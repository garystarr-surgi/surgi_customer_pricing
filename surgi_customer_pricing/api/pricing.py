import frappe

@frappe.whitelist()
def get_customer_pricing(customer: str, item_code: str):
    """
    Returns:
    - description
    - available_qty (on-shelf minus open SO/Quotation)
    - last_price (last Sales Invoice)
    """

    # 1. Item description
    item = frappe.get_doc("Item", item_code)
    description = item.description or item.item_name

    # 2. Available qty (sum of actual_qty in all Bins)
    bins = frappe.get_all(
        "Bin",
        filters={"item_code": item_code},
        fields=["actual_qty"]
    )
    total_qty = sum(b.actual_qty for b in bins)

    # 3. Allocated qty in open Sales Orders + open Quotations
    allocated_so = frappe.db.sql("""
        SELECT SUM(sii.qty) FROM `tabSales Order Item` sii
        JOIN `tabSales Order` so ON so.name = sii.parent
        WHERE so.customer = %s AND so.docstatus = 0 AND sii.item_code = %s
    """, (customer, item_code))

    allocated_quot = frappe.db.sql("""
        SELECT SUM(qi.qty) FROM `tabQuotation Item` qi
        JOIN `tabQuotation` q ON q.name = qi.parent
        WHERE q.customer = %s AND q.docstatus = 0 AND qi.item_code = %s
    """, (customer, item_code))

    allocated_qty = (allocated_so[0][0] or 0) + (allocated_quot[0][0] or 0)

    available_qty = total_qty - allocated_qty

    # 4. Last price paid by this customer
    last_price = frappe.db.sql("""
        SELECT sii.rate FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.customer = %s AND sii.item_code = %s AND si.docstatus = 1
        ORDER BY si.posting_date DESC
        LIMIT 1
    """, (customer, item_code))

    last_price_val = last_price[0][0] if last_price else None

    return {
        "description": description,
        "available_qty": available_qty,
        "last_price": last_price_val
    }

