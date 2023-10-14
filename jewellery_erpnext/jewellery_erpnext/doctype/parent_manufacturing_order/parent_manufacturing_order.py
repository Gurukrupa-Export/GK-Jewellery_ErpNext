# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
from frappe.model.mapper import get_mapped_doc
from jewellery_erpnext.utils import update_existing

class ParentManufacturingOrder(Document):
	def onload(self):
		self.weight_details=[]
		# self.save()
		master_bom = self.master_bom
		if master_bom == '':
			frappe.throw('Master BOM is Missing')
		if master_bom and len(self.weight_details) == 0:
			all_submited_mwo = frappe.db.get_list('Manufacturing Work Order',filters={'docstatus':1,'manufacturing_order':self.name},pluck='name')
			
			total_gross_wt = []
			total_diamon_wt = []
			total_gemstone_wt = []
			total_other_wt = []

			for j in all_submited_mwo:
				all_wt = frappe.db.get_value('Manufacturing Operation',{'manufacturing_work_order':j},['gross_wt','diamond_wt','gemstone_wt','other_wt'],as_dict=1,order_by='creation DESC')
				total_gross_wt.append(all_wt['gross_wt'])
				total_diamon_wt.append(all_wt['diamond_wt'])
				total_gemstone_wt.append(all_wt['gemstone_wt'])
				total_other_wt.append(all_wt['other_wt'])

			weight_dict = {
				"gross_weight":sum(total_gross_wt),
				"diamond_weight":sum(total_diamon_wt),
				"gemstone_weight":sum(total_gemstone_wt),
				"other_weight":sum(total_other_wt),
			}
	
			db_data = frappe.db.sql(
				f"""select gross_weight ,diamond_weight,gemstone_weight,other_weight from tabBOM tb where name = '{master_bom}'"""
			,as_dict=1)
			for i in db_data[0].keys():
				filed_lable = i.split('_')[0].capitalize() + ' ' + i.split('_')[1].capitalize()
				row = self.append('weight_details', {})
				row.weight_label = filed_lable
				row.from_tolerance_weight = db_data[0][i] - db_data[0][i] * 0.025
				row.to_tolerance_weight = db_data[0][i] + db_data[0][i] * 0.025
				row.product_weight = weight_dict[i]
			# self.save()
	

			
			
			# for j in all_submited_mwo:
				
			# 	gross_wt = frappe.db.get_value('Manufacturing Operation',{'manufacturing_work_order':j},['gross_wt'],as_dict=1,order_by='creation DESC')['gross_wt']
			# 	if gross_wt == 0:
			# 		gross_wt = frappe.db.get_value('Manufacturing Operation',{'manufacturing_work_order':j},['prev_gross_wt'],as_dict=1,order_by='creation DESC')['prev_gross_wt']
			# 	print(j)
				# frappe.db.get_value('Manufacturing Operation',{'manufacturing_work_order':self.name},['name','gross_wt'],as_dict=1,order_by='creation DESC')
				# if i == 'gross_weight':
				# 	total_weight = frappe.db.get_list('Manufacturing Work Order',filters={'docstatus':1,'manufacturing_order':self.name},pluck='gross_wt')
				# if i == 'diamond_weight':
				# 	total_weight = frappe.db.get_list('Manufacturing Work Order',filters={'docstatus':1,'manufacturing_order':self.name},pluck='diamond_wt')
				# if i == 'gemstone_weight':
				# 	total_weight = frappe.db.get_list('Manufacturing Work Order',filters={'docstatus':1,'manufacturing_order':self.name},pluck='gemstone_wt')
				# if i == 'other_weight':
				# 	total_weight = frappe.db.get_list('Manufacturing Work Order',filters={'docstatus':1,'manufacturing_order':self.name},pluck='other_wt')
				# print(f'total_weight=-------------------{total_weight}')
				# row.product_weight = frappe.db.get_list('Manufacturing Work Order',filters={'docstatus':1,'manufacturing_order':self.name},pluck=db_data[0][i])
				# row.product_weight = total_weight

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
		target_warehouse = frappe.db.get_value("Manufacturing Setting", {"company": self.company},"in_transit")
		for row in bom_doc:
			item_type = get_item_type(row.item_code)
			if item_type not in items:
				items[item_type] = []
			items[item_type].append({'item_code': row.item_code, 'qty': row.qty, 'warehouse': target_warehouse})
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
		doc.seq = (self.name.split("-")[-1])
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
	fg_doc.department = frappe.db.get_value("Manufacturing Setting", {"company": doc.company},"default_department")
	fg_doc.for_fg = 1
	fg_doc.auto_created = 1
	fg_doc.save()

# @frappe.whitelist()
# def get_weight(master_bom):
# 	if master_bom == '':
# 		frappe.throw('Master BOM is Missing')
# 	db_data = frappe.db.sql(
# 		f"""select gross_weight ,diamond_weight,gemstone_weight,other_weight from tabBOM tb where name = '{master_bom}'"""
# 	,as_dict=1)
	
# 	all_data = []
# 	for i in db_data[0].keys():
# 		filed_lable = i.split('_')[0].capitalize() + ' ' + i.split('_')[1].capitalize()
# 		from_gross_weight = db_data[0][i] - db_data[0][i] * 0.025
# 		to_gross_weight = db_data[0][i] + db_data[0][i] * 0.025
# 		all_data.append([filed_lable,from_gross_weight,to_gross_weight])
	
# 	return all_data