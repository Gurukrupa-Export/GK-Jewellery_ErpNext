import frappe
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def make_stock_in_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		if target.stock_entry_type == "Customer Goods Received":
			target.stock_entry_type = "Customer Goods Issue"
			target.purpose = "Material Issue"
		elif target.stoc_entry_type == "Customer Goods Issue":
			target.stock_entry_type = "Customer Goods Received"
			target.purpose = "Material Receipt"
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.t_warehouse = ""

		target_doc.s_warehouse = source_doc.t_warehouse
		target_doc.qty = source_doc.qty

	doclist = get_mapped_doc(
		"Stock Entry",
		source_name,
		{
			"Stock Entry": {
				"doctype": "Material Request",
				# "field_map": {"name": "outgoing_stock_entry"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Stock Entry Detail": {
				"doctype": "Material Request Item",
				"field_map": {
					"name": "ste_detail",
					"parent": "against_stock_entry",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
				},
				"postprocess": update_item,
				# "condition": lambda doc: flt(doc.qty) - flt(doc.transferred_qty) > 0.01,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist

