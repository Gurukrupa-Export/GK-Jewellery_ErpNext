import frappe
from jewellery_erpnext.utils import update_existing


def make_subcontracting_order(doc, row):
    po = frappe.new_doc("Purchase Order")
    po.supplier = row.supplier
    po.company = doc.company
    po.is_subcontracted = 1
    po.schedule_date = row.estimated_delivery_date
    po.append("items", {
        "item_code": frappe.db.get_single_value("Jewellery Settings", "service_item"),
        "qty": 1,
        "fg_item": row.item_code,
        "fg_item_qty": row.subcontracting_qty,
        "schedule_date": row.estimated_delivery_date
    })
    po.manufacturing_plan = doc.name
    po.rowname = row.name
    po.save()

def validate(doc, method=None):
    pass

def on_cancel(doc, method=None):
    pass
    # update_existing("Manufacturing Plan Table", doc.rowname, "manufacturing_order_qty", f"manufacturing_order_qty - {doc.qty}")
    # update_existing("Sales Order Item", doc.sales_order_item, "manufacturing_order_qty", f"manufacturing_order_qty - {doc.qty}")