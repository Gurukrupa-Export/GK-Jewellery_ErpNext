import frappe,json
from frappe.model.document import Document

@frappe.whitelist()
def get_dispatch_slip(source_name, target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Dispatch Slip")
	else:
		target_doc = frappe.get_doc(target_doc)

	sales_invoice_items = frappe.db.get_list("Sales Invoice Item",filters={"parent":source_name},fields=["*"])
	
	# print(sales_invoice_items)
	for i in sales_invoice_items:
		target_doc.append("delivery_challan_detail", {
			"item_code": i.get("item_code"),
			"gst_hsn_code": i.get("gst_hsn_code"),
			"description": i.get("description"),
			"qty": i.get("qty"),
			"amount": i.get("net_amount"),
			# "item_code": sales_invoice.get("description"),
	})

	return target_doc