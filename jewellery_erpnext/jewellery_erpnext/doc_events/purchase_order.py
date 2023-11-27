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


@frappe.whitelist()
def get_supplier_details(item_code,supplier):
	if supplier=='None':
		frappe.throw('Select Supplier First')
	item_name = frappe.db.sql(f"""select attribute_value  from `tabItem Variant Attribute` tiva WHERE parent  = '{item_code}' and attribute ='Finding Sub-Category'""",as_dict=1)[0]['attribute_value']
	supplier_price_list = frappe.db.sql(f"""select name from `tabSupplier Price List` tspl WHERE supplier='{supplier}' order BY creation desc""",as_dict=1)[0]['name']
	wastage = frappe.db.sql(f"""select wastage from `tabMaking Charge Price Finding Subcategory` tmcpfs WHERE parent = '{supplier_price_list}' and subcategory = '{item_name}'""",as_dict=1)[0]['wastage']
	return wastage