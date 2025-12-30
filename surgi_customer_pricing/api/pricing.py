import frappe

@frappe.whitelist()
def get_customer_pricing(customer, item_code):
    """
    Returns:
    - description: Item description
    - available_qty: Bin.actual_qty - open SO - open Quotations
    - last_price: Last Sales Invoice rate for this customer
    """

    # 1️⃣ Fetch item description safely
    try:
        item = frappe.get_doc("Item", item_code)
        description = item.description or item.item_name
    except frappe.DoesNotExistError:
        return {
            "description": f"Item {item_code} not found",
            "available_qty": 0,
            "last_price": None
        }

    # 2️⃣ Total on-shelf qty
    bins = frappe.get_all(
        "Bin",
        filters={"item_code": item_code},
        fields=["actual_qty"]
    )
    total_qty = sum(b.actual_qty for b in bins)

    # 3️⃣ Allocated qty in open Sales Orders
    allocated_so_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(sii.qty), 0)
        FROM `tabSales Order Item` sii
        JOIN `tabSales Order` so ON so.name = sii.parent
        WHERE so.docstatus = 0 AND sii.item_code = %s
    """, (item_code,))[0][0]

    # 4️⃣ Allocated qty in open Quotations
    allocated_quot_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(qi.qty), 0)
        FROM `tabQuotation Item` qi
        JOIN `tabQuotation` q ON q.name = qi.parent
        WHERE q.docstatus = 0 AND qi.item_code = %s
    """, (item_code,))[0][0]

    # 5️⃣ Available qty
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

    # 7️⃣ Return results
    return {
        "description": description,
        "available_qty": available_qty,
        "last_price": last_price_val
    }
