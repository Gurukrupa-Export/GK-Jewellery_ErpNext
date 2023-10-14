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
	# or self.design_type in ['New Design','Fusion','Similar']
	if (self.design_type == 'Mod' and self.item_type == 'Template and Variant') or  (self.design_type == 'Mod' and self.item_type == 'Suffix Of Varinat'):

		item_template = create_item_template_from_cad_order(self)
		updatet_item_template(self,item_template)
		# item_variant = create_item_variant_from_cad_order(item_template,self.name)
		# update_item_variant(self,item_variant,item_template)
		# frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item_variant))))
	if (self.design_type == 'Mod' and self.item_type == "Only Variant"):
		item_variant = create_item_only_variant_from_cad_order(self,self.name)
		frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item_variant[0]))))
		
		frappe.db.set_value('Item',item_variant[0],{
			"is_design_code":1,
			"variant_of" : item_variant[1]
		})

	# elif (self.design_type == 'Mod' and self.item_type == "Suffix Of Variant"):
	# 	item_variant = create_item_only_sufix_of_variant_from_cad_order(self,self.name)
		# frappe.db.set_value(self.doctype, self.name, "item", item_template)
	# item = create_item_from_cad_order(self.name)
	# frappe.db.set_value(self.doctype, self.name, "item", item)

	# create_reference_doc(self,item)
	

	# frappe.msgprint(_("New Item Created: {0}".format(get_link_to_form("Item",item_template))))

def updatet_item_template(self,item_template):
	frappe.db.set_value('Item',item_template,{
		"is_design_code":0,
		"item_code":item_template
	})

def update_item_variant(self,item_variant,item_template):
	frappe.db.set_value('Item',item_variant,{
		"is_design_code":1,
		"variant_of" : item_template
	})



def create_reference_doc(self,item):
	parent_doc = frappe.db.get_value('Reference Design Code',{'design_code':self.design_id},'parent')
	if parent_doc == None:
		parent_doc = frappe.db.get_value('Reference Design Code',{'reference_design_code':self.design_id},'parent')
	if parent_doc:
		parent_doc_value = frappe.get_doc('Reference Items', parent_doc)
		new_row = parent_doc_value.append("item_table", {})
		new_row.design_code = item
		new_row.reference_design_code = self.design_id
		parent_doc_value.save()

	else:
		new_target_doc = frappe.new_doc("Reference Items")
		new_target_doc.parent_reference_item = self.design_id

		child_table_data = [
			{
				"design_code": item,
				"reference_design_code": self.design_id
			},
		]
		
		for data in child_table_data:
			new_target_doc.append("item_table", data)
			
		
		new_target_doc.insert(ignore_permissions=True)
		new_target_doc.save()



def create_item_template_from_cad_order(source_name, target_doc=None):
	
	if source_name.item_type == 'Template and Variant':
		print('if')
		item_code = frappe.db.get_list('Item',filters={'item_category':source_name.category},fields=['name'],order_by='creation DESC')
		print(item_code)
	elif source_name.item_type == 'Suffix Of Varinat':
		print('elif')
	else:
		print('else')
	frappe.throw('HOLD')
		
	
	def post_process(source, target):
		print(target)
		target.is_design_code = 1
		target.has_variants = 1
		if source.designer_assignment:
			target.designer = source.designer_assignment[0].designer

	doc = get_mapped_doc(
		"CAD Order",
		source_name.name,
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
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name

def create_item_variant_from_cad_order(item_template,source_name, target_doc=None):
	def post_process(source, target):
		target.order_form_type = 'CAD Order'
		target.order_form_id = source_name
		target.item_code = f'{item_template}-001'
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
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name

def create_item_only_variant_from_cad_order(self,source_name, target_doc=None):

	db_data = frappe.db.get_list('Item',filters={'item_category':self.category},fields=['name','variant_of'],order_by='creation desc')[0]
	if db_data !=[]:
		index = int(db_data['name'].split('-')[1]) + 1
		suffix = "%.3i" % index
	else:
		suffix = "001"
	item_code = db_data['variant_of'] + '-' + suffix
	
	def post_process(source, target):
		target.order_form_type = 'CAD Order'
		target.order_form_id = source_name
		target.item_code = item_code
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
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)
	# frappe.throw('HOLD')
	doc.save()
	return doc.name,db_data['variant_of']

def create_item_only_sufix_of_variant_from_cad_order(self,source_name, target_doc=None):

	db_data = frappe.db.get_list('Item',filters={'item_category':self.category},fields=['name','variant_of'],order_by='creation desc')[0]
	if db_data !=[]:
		index = int(db_data['name'].split('-')[1]) + 1
		suffix = "%.3i" % index
	else:
		suffix = "001"
	item_code = db_data['variant_of'] + '-' + suffix
	
	def post_process(source, target):
		target.order_form_type = 'CAD Order'
		target.order_form_id = source_name
		target.item_code = item_code
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
					"usa_states":"usa_states",
				} 
			}
		},target_doc, post_process
	)

	doc.save()
	return doc.name,db_data['variant_of']

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