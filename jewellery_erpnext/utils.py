import frappe
from frappe.utils import now
from erpnext.controllers.item_variant import get_variant,create_variant
import json

@frappe.whitelist()
def set_items_from_attribute(item_template, item_template_attribute):
	item_template_attribute = json.loads(item_template_attribute)
	args = {}
	for row in item_template_attribute:
		if not row.get('attribute_value'):
			frappe.throw(f"Row: {row.get('idx')} Please select attribute value for {row.get('item_attribute')}.")
		args.update({
			row.get('item_attribute'): row.get('attribute_value')
		})
	variant = get_variant(item_template, args)
	if variant:
		return frappe.get_doc("Item",variant)
	else:
		variant = create_variant(item_template,args)
		variant.save()
		return variant
	
@frappe.whitelist()
def get_item_from_attribute(metal_type, metal_touch, metal_purity, metal_colour = None):
	# items are created without metal_touch as attribute so not considering it in condition for now
	condition = ''
	if metal_colour:
		condition += f"and metal_colour = '{metal_colour}'"
	data = frappe.db.sql(f"""select mtp.parent as item_code from 
						(select _mtp.parent, _mtp.attribute_value as metal_type from `tabItem Variant Attribute` _mtp where _mtp.attribute = "Metal Type") mtp
						left join 
						(select _mt.parent, _mt.attribute_value as metal_touch from `tabItem Variant Attribute` _mt where _mt.attribute = "Metal Touch") mt
						on mt.parent = mtp.parent left join
						(select _mp.parent, _mp.attribute_value as metal_purity from `tabItem Variant Attribute` _mp where _mp.attribute = "Metal Purity") mp
						on mp.parent = mtp.parent left join
						(select _mc.parent, _mc.attribute_value as metal_colour from `tabItem Variant Attribute` _mc where _mc.attribute = "Metal Colour") mc 
						on mtp.parent = mc.parent right join
		      			(select name from `tabItem` where variant_of = 'M') itm on itm.name = mtp.parent
		       where metal_type = '{metal_type}' and metal_touch = '{metal_touch}' and metal_purity = '{metal_purity}' {condition}""")
	if data:
		return data[0][0]
	return None

def get_variant_of_item(item_code):
	return frappe.db.get_value('Item', item_code, 'variant_of')

def update_existing(doctype, name, field, value=None, debug=0):
	modified = now()
	modified_by = frappe.session.user
	if isinstance(field, dict):
		values = ", ".join([f"{key} = {_value}" for key,_value in field.items()])
	else:
		values = f"{field} = {value}"
	query = f"""UPDATE `tab{doctype}` SET {values},`modified`='{modified}',`modified_by`='{modified_by}' WHERE `name`='{name}'"""
	frappe.db.sql(query, debug=debug)

def set_values_in_bulk(doctype, doclist, values):
	value = []
	for key, val in values.items():
		value.append(f"{key} = '{val}'")
	frappe.db.sql(f"""update `tab{doctype}` set { ', '.join(value) } where name in ('{"', '".join(doclist)}')""")

def get_value(doctype, filters, fields, default=None, debug=0):
	fields = ", ".join(fields) if isinstance(fields, list) else fields
	_filters = " and ".join([f"{key} = {value if not isinstance(value, str) else frappe.db.escape(value)}" for key, value in filters.items()])
	res = frappe.db.sql(f"""select {fields} from `tab{doctype}` where {_filters}""", debug=debug)
	if res:
		return res[0][0] or default
	
	return default