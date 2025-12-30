import frappe

@frappe.whitelist()
def get_customer_pricing(customer, item_code):
    """
    Returns:
    - description: Item description
    - available_qty: On-shelf minus open Sales Orders and Quotations
    - last_price: Last Sales Invoice rate for this customer
    """

    # 1. Item description
    item = frappe.get_doc("Item", item_code)
    description = item.description or item.item_name

    # 2. On-shelf qty (sum across all bins)
    bins = frappe.get_all(
        "Bin",
        filters={"item_code": item_code},
        fields=["actual_qty"]
    )
    total_qty = sum(b.actual_qty for b in bins)

    # 3. Allocated qty in open Sales Orders
    allocated_so = frappe.db.sql("""
        SELECT SUM(sii.qty)
        FROM `tabSales Order Item` sii
        JOIN `tabSales Order` so ON so.name = sii.parent
        WHERE so.docstatus = 0 AND sii.item_code = %s
    """, (item_code,))
    allocated_so_qty = allocated_so[0][0] or 0

    # 4. Allocated qty in open Quotations
    allocated_quot = frappe.db.sql("""
        SELECT SUM(qi.qty)
        FROM `tabQuotation Item` qi
        JOIN `tabQuotation` q ON q.name = qi.parent
        WHERE q.docstatus = 0 AND qi.item_code = %s
    """, (item_code,))
    allocated_quot_qty = allocated_quot[0][0] or 0

    # 5. Available qty
    available_qty = total_qty - allocated_so_qty - allocated_quot_qty

    # 6. Last Sales Invoice price for this customer
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

    # 7. Return all data
    return {
        "description": description,
        "available_qty": available_qty,
        "last_price": last_price_val
    }
