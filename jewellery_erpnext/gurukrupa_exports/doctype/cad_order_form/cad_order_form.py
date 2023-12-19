# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe,json
from frappe import _
from frappe.utils import get_link_to_form
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class CADOrderForm(Document):
	def on_submit(self):
		create_cad_orders(self)

	def on_cancel(self):
		delete_auto_created_cad_order(self)

	def validate(self):
		self.validate_category_subcaegory()

	def validate_category_subcaegory(self):
		for row in self.get("order_details"):
			if row.subcategory:
				parent = frappe.db.get_value("Attribute Value", row.subcategory, "parent_attribute_value")
				if row.category != parent:
					frappe.throw(_(f"Category & Sub Category mismatched in row #{row.idx}"))


def create_cad_orders(self):
	doclist = []
	for row in self.order_details:
		docname = make_cad_order(row.name, parent_doc = self)
		frappe.db.set_value('CAD Order Form Detail',row.name,'cad_order_id',docname)
		doclist.append(get_link_to_form("CAD Order", docname))

	if doclist:
		msg = _("The following {0} were created: {1}").format(
				frappe.bold(_("CAD Orders")), "<br>" + ", ".join(doclist)
			)
		frappe.msgprint(msg)

def delete_auto_created_cad_order(self):
	for row in frappe.get_all("CAD Order", filters={"cad_order_form": self.name}):
		frappe.delete_doc("CAD Order", row.name)

def make_cad_order(source_name, target_doc=None, parent_doc = None):
	def set_missing_values(source, target):
		target.cad_order_form_detail = source.name
		target.cad_order_form = source.parent
		target.index = source.idx
	
	
	design_type = frappe.get_doc('CAD Order Form Detail',source_name).design_type
	
	if design_type == 'Mod':
		item_type = set_item_type(source_name)
		bom_or_cad = workflow_state_maker(source_name)		
	else:
		item_type = 'Template and Variant'
		bom_or_cad = 'CAD'
	# print(item_type)
	# frappe.throw(f"{item_type}-{bom_or_cad}")
		
	doc = get_mapped_doc(
		"CAD Order Form Detail",
		source_name,
		{
			"CAD Order Form Detail": {
				"doctype": "CAD Order" 
			}
		},target_doc, set_missing_values
	)

	for entity in parent_doc.get("service_type",[]):
		doc.append("service_type", {"service_type1": entity.service_type1})
	doc.parcel_place = parent_doc.parcel_place
	doc.company = parent_doc.company
	doc.form_remarks = parent_doc.remarks
	doc.india = parent_doc.india
	doc.usa = parent_doc.usa
	doc.india_states = parent_doc.india_states
	doc.design_attributes = parent_doc.design_attributes
	doc.item_type = item_type
	doc.bom_or_cad = bom_or_cad
	doc.save()
	
	return doc.name

def set_item_type(source_name):
	doc = frappe.get_doc('CAD Order Form Detail',source_name)
	
	# all_variant_attribute = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'in_item_variant':1},fields=['item_attribute'])
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_item_variant=1""",as_dict=1
	)
	# suffix_attribute = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'suffix':1},fields=['item_attribute'])
	suffix_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and suffix=1""",as_dict=1
	)
	# print(suffix_attribute)

	all_attribute_list = []
	for variant_attribut in all_variant_attribute:
		item_attribute = variant_attribut['item_attribute'].lower().replace(' ','_')
		all_attribute_list.append(item_attribute)
	
	bom_detail = frappe.db.get_value('BOM',{'is_active':1,'item':doc.design_id},all_attribute_list,as_dict=1)
	if bom_detail==None:
		frappe.throw(f'BOM is not available for {doc.design_id}')
	
	all_item_type = []
	for attribute in suffix_attribute:
		item_attribute = attribute['item_attribute'].lower().replace(' ','_')
		if bom_detail[item_attribute] != frappe.db.get_value('CAD Order Form Detail',source_name,item_attribute):
			item_type = 'Suffix Of Variant'
		else:
			item_type = 'Only Variant'
		all_item_type.append(item_type)
	
	if 'Suffix Of Variant' in all_item_type:
		item_type = 'Suffix Of Variant'
	else:
		item_type = 'Only Variant'

	return item_type


def workflow_state_maker(source_name):

	doc = frappe.get_doc('CAD Order Form Detail',source_name)

	# all_variant_attribute = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'in_item_variant':1},fields=['item_attribute'])
	all_variant_attribute = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_item_variant=1""",as_dict=1
	)

	all_attribute_list = []
	for variant_attribut in all_variant_attribute:
		item_attribute = variant_attribut['item_attribute'].lower().replace(' ','_')
		all_attribute_list.append(item_attribute)
	
	bom_detail = frappe.db.get_value('BOM',{'is_active':1,'is_default':1,'item':doc.design_id},all_attribute_list,as_dict=1)

	# cad_attribute_list = frappe.db.get_list('Attribute Value Item Attribute Detail',filters={'parent':doc.subcategory,'in_cad_flow':1},fields=['item_attribute'])
	cad_attribute_list = frappe.db.sql(
		f"""select item_attribute from `tabAttribute Value Item Attribute Detail` where parent = '{doc.subcategory}' and in_cad_flow=1""",as_dict=1
	)

	all_bom_or_cad = []
	for i in cad_attribute_list:
		item_attribute = i['item_attribute'].lower().replace(' ','_')
		if bom_detail[item_attribute] != frappe.db.get_value('CAD Order Form Detail',source_name,item_attribute):
			bom_or_cad = 'CAD'
		else:
			bom_or_cad = 'BOM'
		all_bom_or_cad.append(bom_or_cad)
	
	if 'CAD' in all_bom_or_cad:
		bom_or_cad = 'CAD'
	else:
		bom_or_cad = 'CAD'

	return bom_or_cad


# @frappe.whitelist()
# def set_titan_code(customer_code,titan_code):
# 	metal_touch = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[:2],'customer':customer_code},'parent')
# 	# category = frappe.db.get_value('Customer Attributes Table',{'code':titan_code[6],'customer':customer_code},'parent')
	
# 	data_json = {"metal_touch":metal_touch,}
# 	return data_json

@frappe.whitelist()
def make_order_form(source_name,target_doc=None):
	if isinstance(target_doc, str):
		target_doc = json.loads(target_doc)
	if not target_doc:
		target_doc = frappe.new_doc("CAD Order Form")
	else:
		target_doc = frappe.get_doc(target_doc)

	titan_order_form = frappe.db.get_value("Titan Order Form", source_name, "*")

	target_doc.append("order_details", {
		"category": titan_order_form.get("item_category"),
		"design_by": "Our  Design",
		"design_type": "Mod",
		"design_id": titan_order_form.get("design_code"),
		"titan_code": titan_order_form.get("titan_code"),
		"subcategory": titan_order_form.get("item_subcategory"),
		"bom": titan_order_form.get("bom"),
		"serial_no_bom": titan_order_form.get("serial_no_bom"),
		"tag_no": titan_order_form.get("serial_no"),
		"metal_type": titan_order_form.get("metal_type"),
		"metal_touch": titan_order_form.get("metal_touch"),
		"metal_purity": titan_order_form.get("metal_purity"),
		"metal_colour": titan_order_form.get("metal_colour"),
		"product_size": titan_order_form.get("product_size"),
		"setting_type": titan_order_form.get("setting_type"),
		"delivery_date": titan_order_form.get("delivery_date"),
		"enamal": titan_order_form.get("enamal"),
		"rhodium": titan_order_form.get("rhodium"),
	})


	return target_doc