# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
from frappe.model.mapper import get_mapped_doc
from erpnext.controllers.item_variant import get_variant,create_variant
from jewellery_erpnext.utils import update_existing

class ParentManufacturingOrder(Document):
	def after_insert(self):
		if self.serial_no:
			serial_bom = frappe.db.exists("BOM",{"tag_no":self.serial_no})
			self.db_set("serial_id_bom", serial_bom)

	def validate(self):
		get_gemstone_details(self)

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
		bom_doc = frappe.get_all("BOM Item",{"parent": bom}, ["parent","item_code", "qty"])
		items = {}
		target_warehouse = frappe.db.get_value("Manufacturing Setting", {"company": self.company},"in_transit")
		for row in bom_doc:
			item_type = get_item_type(row.item_code)			
			
			if item_type == "diamond_item":
				continue
				diamond_item_code = get_diamond_item_code_by_variant(self,bom,row,target_warehouse,item_type)
				items[item_type].append({'item_code': diamond_item_code, 'qty': row.qty, 'warehouse': target_warehouse})
				
			elif item_type == "gemstone_item":
				continue
				items[item_type].append({'item_code': gemstone_item_code, 'qty': row.qty, 'warehouse': target_warehouse})
			else:
				if item_type not in items:
					items[item_type] = []
					items[item_type].append({'item_code': row.item_code, 'qty': row.qty, 'warehouse': target_warehouse})

		diamond_list = get_diamond_item_code_by_variant(self,bom,target_warehouse) 

		if diamond_list:
			items["diamond_item"] = diamond_list

		gemstone_list = get_gemstone_item_code_by_variant(self,bom,target_warehouse)
		if gemstone_list:
			items["gemstone_item"] = items["gemstone_item"]

		for item_type, val in items.items():
			if item_type == "metal_item":
				continue
			mr_doc = frappe.new_doc('Material Request')
			mr_doc.company = self.company
			mr_doc.material_request_type = 'Material Transfer'
			mr_doc.schedule_date = frappe.utils.nowdate()
			mr_doc.manufacturing_order = self.name
			for i in val:
				mr_doc.append('items', i)
			mr_doc.save()
		frappe.msgprint("Material Request Created !!")

	def set_missing_value(self):
		if not self.is_new():
			pass


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
	doc = frappe.new_doc("Parent Manufacturing Order")
	so_det = frappe.get_value("Sales Order Item", row.docname, ["metal_type","metal_touch","metal_colour"], as_dict=1) or {}
	doc.company = source_doc.company
	doc.department = frappe.db.get_value("Manufacturing Setting", {"company": source_doc.company},"default_department")
	doc.sales_order = row.sales_order
	doc.sales_order_item = row.docname
	doc.item_code = row.item_code
	doc.metal_type = so_det.get("metal_type")
	doc.metal_touch = so_det.get("metal_touch")
	doc.metal_colour = so_det.get("metal_colour")
	# doc.sales_order_bom = row.bom
	doc.service_type = [frappe.get_doc(row) for row in frappe.get_all("Service Type 2", {"parent": row.sales_order}, ["service_type1", "'Service Type 2' as doctype"])]
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
		doc.metal_touch = row.metal_touch
		doc.metal_type = row.metal_type
		doc.metal_purity = row.metal_purity
		doc.metal_colour = row.metal_colour
		doc.seq = int(self.name.split("-")[-1])
		doc.department = frappe.db.get_value("Manufacturing Setting", {"company": doc.company},"default_department")
		doc.auto_created = 1
		doc.save()
	
	#for FG item
	fg_doc = get_mapped_doc("Parent Manufacturing Order", self.name,
				{
				"Parent Manufacturing Order" : {
					"doctype":	"Manufacturing Work Order",
					"field_map": {
						"name": "manufacturing_order"
					}
				}
			   })
	fg_doc.metal_touch = row.metal_touch
	fg_doc.metal_type = row.metal_type
	fg_doc.metal_purity = row.metal_purity
	fg_doc.metal_colour = row.metal_colour
	fg_doc.seq = int(self.name.split("-")[-1])
	fg_doc.department = frappe.db.get_value("Manufacturing Setting", {"company": doc.company},"default_fg_department")
	fg_doc.for_fg = 1
	fg_doc.auto_created = 1
	fg_doc.save()

def get_diamond_item_code_by_variant(self,bom,target_warehouse):
	attributes = {}
	diamond_list = []
	diamond_bom = frappe.get_doc('BOM',bom)
	if diamond_bom.diamond_detail:	
		# Loop through the rows of the bom table
		for row in diamond_bom.diamond_detail:
			# Get the template document for the current item
			template = frappe.get_doc("Item",row.item)
			if template.name not in attributes: # If the attributes for the current item have not been fetched yet
				attributes[template.name] = [attr.attribute for attr in template.attributes] # Store the attributes in the dictionary
			# Create a dictionary of the attribute values from the row
			args = {attr: row.get(attr.replace(" ", "_").lower()) for attr in attributes[template.name] if row.get(attr.replace(" ", "_").lower())}
			args["Diamond Grade"] = self.diamond_grade
			# frappe.throw(f"""{args}""")
			variant = get_variant(row.item, args) # Get the variant for the current item and attribute values

			if variant:
				diamond_list.append({'item_code': variant, 'qty': self.qty, 'warehouse': target_warehouse})
				
			else:
				# Create a new variant
				variant = create_variant(row.item,args)
				variant.save()
				diamond_list.append({'item_code': variant.item_code, 'qty': self.qty, 'warehouse': target_warehouse})

		return diamond_list
		
def get_gemstone_item_code_by_variant(self,bom,target_warehouse):
	attributes = {}
	gemstone_list = []
	if len(self.gemstone_table) > 0:
		for row in self.gemstone_table:
			template = frappe.get_doc("Item","G")
			if template.name not in attributes: 
				attributes[template.name] = [attr.attribute for attr in template.attributes]
			args = {attr: row.get(attr.replace(" ", "_").lower()) for attr in attributes[template.name] if row.get(attr.replace(" ", "_").lower())}
			variant = get_variant(row.item, args)
			
			if variant:
				gemstone_list.append({'item_code': variant, 'qty': row.quantity, 'warehouse': target_warehouse})
			else:
				# Create a new variant
				variant = create_variant(row.item,args)
				variant.save()
				gemstone_list.append({'item_code': variant.item_code, 'qty': row.quantity, 'warehouse': target_warehouse})
			
		return gemstone_list

def get_gemstone_details(self):
	bom = self.serial_id_bom or self.master_bom
	if not bom:
		frappe.throw("BOM is missing")
	bom_doc = frappe.get_doc('BOM',bom)
	if len(bom_doc.gemstone_detail) > 0:
		for gem_row in bom_doc.gemstone_detail:
			self.append('gemstone_table',gem_row)