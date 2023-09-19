# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import get_link_to_form
from erpnext.setup.utils import get_exchange_rate
import json

class CADOrder(Document):
	def on_submit(self):
		create_line_items(self)

    
def create_line_items(self):
	# if self.workflow_state == 'Approved' and not self.item:
	item = create_item_from_cad_order(self.name)
	frappe.db.set_value(self.doctype, self.name, "item", item)
	frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item))))

def create_item_from_cad_order(source_name, target_doc=None):
	def post_process(source, target):
		target.disabled = 1
		target.is_design_code = 1
		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer

	doc = get_mapped_doc(
		"CAD Order",
		source_name,
		{
			"CAD Order": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"subcategory": "item_subcategory",
					"setting_type": "setting_type",
					"stepping":"stepping",
					"fusion":"fusion",
					"drops":"drops",
					"coin":"coin",
					"gold_wire":"gold_wire",
					"gold_ball":"gold_ball",
					"flows":"flows",
					"nagas":"nagas",
					"design_attributes":"design_attribute",
					"india":"india",
					"india_states":"india_states",
					"usa":"usa",
					"usa_states":"usa_states"
				} 
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name

@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges
		quotation = frappe.get_doc(target)
		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")
		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)
		quotation.conversion_rate = exchange_rate
		# get default taxes
		taxes = get_default_taxes_and_charges(
			"Sales Taxes and Charges Template", company=quotation.company
		)
		if taxes.get("taxes"):
			quotation.update(taxes)
		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")

		quotation.quotation_to = "Customer"
		field_map = {
 			# target : source
			"company": "company",
			"party_name": "customer_code",
			"order_type": "order_type",
			"diamond_quality": "diamond_quality"
		}
		for target_field, source_field in field_map.items():
			quotation.set(target_field,source.get(source_field))
		service_types = frappe.db.get_values("Service Type 2", {"parent": source.name},"service_type1")
		for service_type in service_types:
			quotation.append("service_type",{"service_type1": service_type})

	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("Quotation")
	else:
		target_doc = frappe.get_doc(target_doc)

	cad_order = frappe.db.get_value("CAD Order", source_name, "*")

	target_doc.append("items", {
		"branch": cad_order.get("branch"),
		"project": cad_order.get("project"),
		"item_code": cad_order.get("item"),
		"serial_no": cad_order.get("tag_no"),
		"metal_colour": cad_order.get("metal_colour"),
		"metal_purity": cad_order.get("metal_purity"),
		"metal_touch": cad_order.get("metal_touch"),
		"gemstone_quality": cad_order.get("gemstone_quality"),
		"item_category" : cad_order.get("category"),
		"diamond_quality": cad_order.get("diamond_quality"),
		"item_subcategory": cad_order.get("subcategory"),
		"setting_type": cad_order.get("setting_type"),
		"delivery_date": cad_order.get("delivery_date"),
		"order_form_type": "CAD Order",
		"order_form_id": cad_order.get("name"),
		"salesman_name": cad_order.get("salesman_name"),
		"order_form_date": cad_order.get("order_date"),
		"po_no": cad_order.get("po_no")
	})
	set_missing_values(cad_order, target_doc)

	return target_doc