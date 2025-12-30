import frappe

@frappe.whitelist()
def get_customer_pricing(customer, item_code):
    try:
        item = frappe.get_doc("Item", item_code)
        description = item.description or item.item_name
    except frappe.DoesNotExistError:
        return {"description": None, "available_qty": 0, "last_price": None}

    bins = frappe.get_all("Bin", filters={"item_code": item_code}, fields=["actual_qty"])
    total_qty = sum(b.actual_qty for b in bins)

    allocated_so_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(sii.qty), 0)
        FROM `tabSales Order Item` sii
        JOIN `tabSales Order` so ON so.name = sii.parent
        WHERE so.docstatus = 0 AND sii.item_code = %s
    """, (item_code,))[0][0]

    allocated_quot_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(qi.qty), 0)
        FROM `tabQuotation Item` qi
        JOIN `tabQuotation` q ON q.name = qi.parent
        WHERE q.docstatus = 0 AND qi.item_code = %s
    """, (item_code,))[0][0]

    available_qty = max(total_qty - allocated_so_qty - allocated_quot_qty, 0)

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

    return {
        "description": description,
        "available_qty": available_qty,
        "last_price": last_price_val
    }
