import frappe

@frappe.whitelist()
def get_customer_pricing(customer, item_code):
    """
    Returns:
    - description: Item description
    - available_qty: Bin.actual_qty - open SO - open Quotations
    - last_price: Last Sales Invoice rate for this customer
    - bin_qty, so_qty, quot_qty: raw values for debugging
    """

    # 1️⃣ Fetch item description safely
    try:
        item = frappe.get_doc("Item", item_code)
        description = item.description or item.item_name
    except frappe.DoesNotExistError:
        # If variant doesn't exist, return clean empty result
        frappe.logger().info(f"get_customer_pricing: Item {item_code} not found")
        return {
            "description": None,
            "available_qty": 0,
            "last_price": None,
            "bin_qty": 0,
            "so_qty": 0,
            "quot_qty": 0
        }

# 2️⃣ Total on-shelf qty (excluding Rejected and Blemish warehouses)
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(b.actual_qty), 0)
        FROM `tabBin` b
        JOIN `tabWarehouse` w ON b.warehouse = w.name
        WHERE b.item_code = %s
        AND w.name NOT LIKE '%%Rejected%%'
        AND w.name NOT LIKE '%%Blemish%%'
    """, (item_code,))
    total_qty = result[0][0]

    # 3️⃣ Allocated qty in open Sales Orders (all qty, even partially delivered)
    allocated_so_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(sii.qty), 0)
        FROM `tabSales Order Item` sii
        JOIN `tabSales Order` so ON so.name = sii.parent
        WHERE so.docstatus = 1 
        AND so.status NOT IN ('Completed', 'Closed', 'Cancelled')
        AND sii.item_code = %s
    """, (item_code,))[0][0]
    
    # 4️⃣ Allocated qty in open Quotations (submitted but not lost/cancelled)
    allocated_quot_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(qi.qty), 0)
        FROM `tabQuotation Item` qi
        JOIN `tabQuotation` q ON q.name = qi.parent
        WHERE q.docstatus = 1
        AND q.status NOT IN ('Lost', 'Ordered', 'Cancelled', 'Expired')
        AND qi.item_code = %s
    """, (item_code,))[0][0]

    # 5️⃣ Available qty (Bin − SO − Quotation, clamped at 0)
    available_qty = max(total_qty - allocated_so_qty - allocated_quot_qty, 0)

    # 6️⃣ Last Sales Invoice price for this customer
    last_price = frappe.db.sql("""
        SELECT sii.rate
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.customer = %s
          AND sii.item_code = %s
          AND si.docstatus = 1
        ORDER BY si.posting_date DESC
        LIMIT 1
    """, (customer, item_code))
    last_price_val = last_price[0][0] if last_price else None

    # 7️⃣ Debug logging
    frappe.logger().info(
        f"get_customer_pricing: Item={item_code} "
        f"Bin={total_qty} SO={allocated_so_qty} Quotation={allocated_quot_qty} "
        f"Available={available_qty} LastPrice={last_price_val}"
    )

    # 8️⃣ Return results (with raw debug values included)
    return {
        "description": description,
        "available_qty": available_qty,
        "last_price": last_price_val,
        "bin_qty": total_qty,
        "so_qty": allocated_so_qty,
        "quot_qty": allocated_quot_qty
    }
