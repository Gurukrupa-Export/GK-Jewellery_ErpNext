# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
from frappe.model.mapper import get_mapped_doc
from jewellery_erpnext.utils import update_existing

class ParentManufacturingOrder(Document):
	def after_insert(self):
		if self.serial_no:
			serial_bom = frappe.db.exists("BOM",{"tag_no":self.serial_no})
			self.db_set("serial_id_bom", serial_bom)

	def on_submit(self):
		create_manufacturing_work_order(self)
		for idx in range(0, int(self.qty)):
			self.create_material_requests()

	def on_cancel(self):
		update_existing("Manufacturing Plan Table", self.rowname, "manufacturing_order_qty", f"manufacturing_order_qty - {self.qty}")
		update_existing("Sales Order Item", self.sales_order_item, "manufacturing_order_qty", f"manufacturing_order_qty - {self.qty}")
	
	def update_estimated_delivery_date_in_prev_docs(self):
		frappe.db.set_value("Manufacturing Plan", self.manufacturing_plan, "estimated_delivery_date", self.estimated_delivery_date)

	def create_material_requests(self):
		bom = self.serial_id_bom or self.master_bom
		if not bom:
			frappe.throw("BOM is missing")
		bom_doc = frappe.get_all("BOM Item",{"parent": bom}, ["item_code", "qty"])
		items = {}
		target_warehouse = frappe.db.get_single_value("Jewellery Settings","in_transit")
		for row in bom_doc:
			item_type = get_item_type(row.item_code)
			if item_type not in items:
				items[item_type] = []
			items[item_type].append({'item_code': row.item_code, 'qty': row.qty, 'warehouse': target_warehouse})
		for item_type, val in items.items():
			if item_type == "metal_item":
				continue
			mr_doc = frappe.new_doc('Material Request')
			mr_doc.material_request_type = 'Material Transfer'
			mr_doc.schedule_date = frappe.utils.nowdate()
			mr_doc.manufacturing_order = self.name
			for i in val:
				mr_doc.append('items', i)
			mr_doc.save()
		frappe.msgprint("Material Request Created !!")

	def create_operation_card(self):
		oc_doc = frappe.new_doc('Operation Card')
		oc_doc.manufacturing_order = self.name
		oc_doc.purity = self.purity
		oc_doc.item_code = self.item_code
		oc_doc.operation = self.first_operation
		oc_doc.save()
		frappe.msgprint('First Operation Card Created !!')


def get_item_type(item_code):
	item_type = frappe.db.get_value("Item",item_code, "variant_of")
	if item_type == 'M':
		return 'metal_item'
	elif item_type == 'D':
		return 'diamond_item'
	elif item_type == 'G':
		return 'gemstone_item'
	elif item_type == 'F':
		return 'finding_item'
	else:
		return 'other_item'

@frappe.whitelist()
def get_item_code(sales_order_item):
	return frappe.db.get_value('Sales Order Item', sales_order_item, 'item_code')

@frappe.whitelist()
def make_manufacturing_order(source_doc, row):
	# print(type(frappe.db.get_value("Parcel Place MultiSelect",{"parent":row.sales_order,},"parcel_place")))
	print([frappe.db.get_value("Service Type 2",{"parent":row.sales_order},"service_type1")])
	doc = frappe.new_doc("Parent Manufacturing Order")
	doc.company = source_doc.company
	doc.sales_order = row.sales_order
	doc.sales_order_item = row.docname
	doc.item_code = row.item_code
	doc.branch = frappe.db.get_value("Sales Order Item",{"parent":row.sales_order,"item_code":row.item_code},"branch")
	doc.order_form_id = frappe.db.get_value("Sales Order Item",{"parent":row.sales_order,"item_code":row.item_code},"order_form_id")
	doc.order_form_date = frappe.db.get_value("Sales Order Item",{"parent":row.sales_order,"item_code":row.item_code},"order_form_date")
	# recheck this
	doc.service_type = frappe.db.get_value("Service Type 2",{"parent":row.sales_order},"service_type1")
	doc.parcel_place = frappe.db.get_value("Parcel Place MultiSelect",{"parent":row.sales_order,},"parcel_place")
	# 
	doc.manufacturing_plan = source_doc.name
	doc.manufacturer = frappe.db.get_value("Manufacturer",{"company":source_doc.company}, "name", order_by="creation asc")
	doc.qty = row.qty_per_manufacturing_order
	doc.rowname = row.name
	
	doc.save()
	diamond_grade = frappe.db.get_value("Customer Diamond Grade",{"diamond_quality": doc.diamond_quality, "parent": doc.customer},"diamond_grade_1")
	doc.db_set("diamond_grade",diamond_grade)

def create_manufacturing_work_order(self):
	if not self.master_bom:
		return
	# metal_details = frappe.get_all("BOM Metal Detail", {"parent": self.master_bom}, ["metal_type","metal_touch","metal_purity","metal_colour"], group_by='metal_type, metal_purity, metal_colour')
	metal_details = frappe.db.sql(f"""SELECT DISTINCT metal_touch, metal_type, metal_purity, metal_colour
									FROM (
									SELECT metal_touch, metal_type, metal_purity, metal_colour, parent FROM `tabBOM Metal Detail`
									UNION
									SELECT metal_touch, metal_type, metal_purity, metal_colour, parent FROM `tabBOM Finding Detail`
									) AS combined_details where parent = '{self.master_bom}'""", as_dict=1)
	for row in metal_details:
		doc = get_mapped_doc("Parent Manufacturing Order", self.name,
				{
				"Parent Manufacturing Order" : {
					"doctype":	"Manufacturing Work Order",
					"field_map": {
						"name": "manufacturing_order"
					}
				}
			   })
		doc.branch = row.branch
		doc.order_form_id = doc.order_form_id
		doc.order_form_date = doc.order_form_date
		doc.order_form_id = doc.order_form_id
		doc.metal_touch = row.metal_touch
		doc.metal_type = row.metal_type
		doc.metal_purity = row.metal_purity
		doc.metal_color = row.metal_colour
		doc.seq = int(self.name.split("-")[-1])
		doc.department = frappe.db.get_single_value("Jewellery Settings", "default_department")
		doc.auto_created = 1
		doc.save()