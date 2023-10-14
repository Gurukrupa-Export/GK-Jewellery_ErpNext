# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt


import frappe
import json
from frappe import _
from frappe.utils import flt, cint, today
from frappe.model.document import Document
from jewellery_erpnext.utils import get_item_from_attribute

class Refining(Document):
	def validate(self):
		self.check_overlap()
		self.set_fine_weight()
		self.set_gross_pure_weight()

		self.refining_loss = self.gross_pure_weight - self.refined_fine_weight
		
		if not self.refining_department:
			frappe.throw('Please Select Refining Department')

		if self.refining_type == 'Recovery Material':
			if not self.dustname:
				frappe.throw('Please Select Dust type First')

			if self.multiple_department and self.multiple_operation:
				frappe.throw('Chose any one For Multiple Operations or For Multiple Department')

			if self.multiple_department:
				check_allocation(self,self.refining_department_detail)
			elif self.multiple_operation:
				check_allocation(self,self.refining_operation_detail)

	def on_submit(self):
		create_refining_entry(self)

	def check_overlap(self):
		if not self.multiple_operation:
			condition = f"""docstatus != 2 and dustname = '{self.dustname}' and multiple_operation = {self.multiple_operation} 
					and operation = '{self.operation}' and employee = '{self.employee}' and (
					(('{self.date_from}' > date_from) and ('{self.date_from}' < date_to))
					or (('{self.date_to}' > date_from) and ('{self.date_to}' < date_to))
					or (('{self.date_from}' <= date_from) and ('{self.date_to}' >= date_to))
				)"""
			name = frappe.db.sql(
				f"select name from `tabRefining` where name != '{self.name}' and {condition}"
			)
			if name:
				frappe.throw(
					f"Document is overlapping with <b><a href='/app/refining/{name[0][0]}'>{name[0][0]}</a></b>"
				)
		else:
			if not self.refining_operation_detail:
				return
			operation = [
				frappe.db.escape(row.operation)
				for row in self.refining_operation_detail
			]
			condition = f"""r.docstatus != 2 and dustname = '{self.dustname}' and r.multiple_operation = {self.multiple_operation} and 
					ro.operation in ({', '.join(operation)}) and ((('{self.date_from}' >= r.date_from) and ('{self.date_from}' <= r.date_to))
					or (('{self.date_to}' >= r.date_from) and ('{self.date_to}' <= r.date_to))
					or (('{self.date_from}' <= r.date_from) and ('{self.date_to}' >= r.date_to))
				)"""
			name = frappe.db.sql(
				f"""select r.name from `tabRefining` r, `tabRefining Operation Detail` ro where 
									r.name = ro.parent and r.name != '{self.name}' and {condition}"""
			)
			if name:
				frappe.throw(
					f"Document is overlapping with <b><a href='/app/refining/{name[0][0]}'>{name[0][0]}</b>"
				)

	def set_fine_weight(self):
		self.fine_weight = flt(self.refining_gold_weight) * flt(self.metal_purity) / 100

	def set_gross_pure_weight(self):
		gross_pure_weight = 0
		for row in self.refined_gold:
			gross_pure_weight += row.pure_weight

		self.gross_pure_weight = gross_pure_weight

	@frappe.whitelist()
	def create_dust_receive_entry(self):
		if self.dust_weight <= 0:
			frappe.throw("Dust Weight Cannot Be Zero")
		se = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Transfer to Department",
			"custom_refining":self.name,
			# "manufacturing_work_order": row.manufacturing_work_order,
			"inventory_type": "Regular Stock",
			"auto_created":1
		})

		if not self.multiple_operation and not self.multiple_department:
			if self.department:
				append_se_items(self,se,"single")
			elif self.employee:
				append_se_items(self,se,"single")
			else:
				frappe.throw("Please Select Department or Employee")
		elif not self.multiple_operation and self.multiple_department:
			append_se_items(self,se,"refining_department_detail")

		elif self.multiple_operation and not self.multiple_department:
			append_se_items(self,se,"refining_operation_detail")
		
		se.save()
		# se.submit()

		return 1
	
	@frappe.whitelist()
	def get_linked_stock_entries(self):
		target_wh = self.refining_warehouse
		all_stock_entry = []
		for row in self.manufacturing_work_order:
			mwo = row.manufacturing_work_order
			mop = row.manufacturing_operation
			data = frappe.db.sql(f"""
				SELECT se.manufacturing_work_order, se.manufacturing_operation, sed.parent,
				sed.item_code,sed.item_name, sed.qty, sed.uom 
				FROM `tabStock Entry Detail` sed LEFT JOIN `tabStock Entry` se ON sed.parent = se.name
				WHERE se.docstatus = 1
				AND sed.t_warehouse = '{target_wh}'
				AND se.manufacturing_operation = '{mop}'
				AND se.manufacturing_work_order = '{mwo}'
				""", as_dict=1)
			
			all_stock_entry += data

		return frappe.render_template("jewellery_erpnext/jewellery_erpnext/doctype/refining/refining.html", {"data":all_stock_entry})

@frappe.whitelist()
def get_manufacturing_operations(source_name, target_doc=None):
	if not target_doc:
		target_doc = frappe.new_doc("Refining")
	elif isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))
	
	operation = frappe.db.get_value("Manufacturing Operation", source_name,
								["metal_type","manufacturing_order","gross_wt",
		   						"manufacturing_work_order"],as_dict=1)

	target_doc.append("manufacturing_work_order",
				   {"manufacturing_operation":source_name,
					"manufacturing_work_order":operation['manufacturing_work_order'],
					"metal_type":operation["metal_type"],
					# "metal_weight":operation["metal_weight"],
					"parent_manufacturing_work_order":operation["manufacturing_order"]})
	return target_doc

def get_stock_entries_against_mfg_operation(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("Manufacturing Operation", doc)
	wh = frappe.db.get_value("Warehouse", {"department": doc.department}, "name")
	if doc.employee:
		wh = frappe.db.get_value("Warehouse", {"employee": doc.employee}, "name")

	stock_entry_details = frappe.db.get_all("Stock Entry Detail", 
						filters={"t_warehouse": wh, "manufacturing_operation": doc.name, "docstatus": 1},
						fields=["item_code", "qty", "uom","batch_no","serial_no"])
	return stock_entry_details

def create_refining_entry(self):
	target_wh = frappe.db.get_value("Warehouse",{"department": self.refining_department})

	se = frappe.get_doc({
		"doctype": "Stock Entry",
		"stock_entry_type": "Repack",
		"custom_refining":self.name,
		# "manufacturing_work_order": row.manufacturing_work_order,
		"inventory_type": "Regular Stock",
		"auto_created":1
		})
	
	if self.refining_type == "Parent Manufacturing Order":
		all_items = []
		for row in self.manufacturing_work_order:
			# get items from operations
			data = get_stock_entries_against_mfg_operation(row.manufacturing_operation)
			if data:
				all_items += data
				
		if all_items:
			for entry in all_items:
				se.append("items",{
					"item_code": entry.item_code,
					"qty": entry.qty,
					"uom": entry.uom,
					"batch_no":entry.batch_no,
					"serial_no" :entry.serial_no,
					"manufacturing_operation": row.manufacturing_operation,
					"department": self.department,
					# "to_department": doc.department,
					"s_warehouse": target_wh
				})

	if self.refining_type == "Serial Number":
		for row in self.refining_serial_no_detail:
			# get items from serial no
			se.append("items",{
				"item_code": row.item_code,
				"qty": row.metal_weight,
				# "uom": row.uom,
				# "batch_no":row.batch_no,
				"serial_no" :row.serial_number,
				# "manufacturing_operation": row.manufacturing_operation,
				"department": self.department,
				# "to_department": doc.department,
				"s_warehouse": target_wh
			})

	if self.refining_type == 'Recovery Material':
		frappe.throw("Dust Not Received in Refining Department") if not self.dust_received else 0
		recovered_item = get_item_based_on_purity(self)

		if not self.multiple_operation and not self.multiple_department:
			enter_stock_row(self,se,recovered_item)
		elif not self.multiple_operation and self.multiple_department:
			enter_stock_row(self,se,recovered_item)
		elif self.multiple_operation and not self.multiple_department:
			enter_stock_row(self,se,recovered_item)

	elif self.refining_type == 'Re-Refining Material':
		recovered_item = get_item_based_on_purity(self)
		enter_stock_row(self,se,recovered_item)
		

	elif self.refining_type in ["Parent Manufacturing Order","Serial Number"]:
		if not (len(self.recovered_diamond) > 0 and len(self.recovered_gemstone) > 0 and len(self.refined_gold) > 0):
			frappe.throw(f"Please Select at Least 1 item in <strong> Recovered Diamond </strong> or <strong> Recovered Metal</strong> or <strong> Recovered Gemstone</strong>")
		if len(self.recovered_diamond) > 0:

			for diamond_row in self.recovered_diamond:
				se.append("items",{
					"item_code": diamond_row.item,
					"qty": diamond_row.weight,
					"pcs":diamond_row.pcs,
					# "batch_no":entry.batch_no,
					# "serial_no" :entry.serial_no,
					"t_warehouse": target_wh,
					# "department": doc.department,
					# "to_department": doc.department,
					# "manufacturing_operation": doc.name,
					# "is_finished_item":1
				})
		
		if len(self.recovered_gemstone) > 0:
			for gen_row in self.recovered_gemstone:
				se.append("items",{
					"item_code": gen_row.item,
					"qty": gen_row.weight,
					"pcs":gen_row.pcs,
					# "batch_no":entry.batch_no,
					# "serial_no" :entry.serial_no,
					"t_warehouse": target_wh,
					# "department": doc.department,
					# "to_department": doc.department,
					# "manufacturing_operation": doc.name,
					# "is_finished_item":1
				})
		if len(self.refined_gold) > 0:
			for metal_row in self.refined_gold:
				se.append("items",{
					"item_code": metal_row.item_code,
					"qty": metal_row.pure_weight,
					# "pcs":metal_row.pcs,s
					# "batch_no":entry.batch_no,
					# "serial_no" :entry.serial_no,
					"t_warehouse": target_wh,
					# "department": doc.department,
					# "to_department": doc.department,
					# "manufacturing_operation": doc.name,
					# "is_finished_item":1
				})
	
	se.save()
	# se.submit()
	frappe.msgprint('Refining Entry Passed successfully')

def check_allocation(self,allocation_table):
	allocation = 0
	for row in allocation_table:
		allocation += row.ratio or 0

	if allocation != 100:
		frappe.throw("Ratio Should be 100%")

def append_se_items(self,se,type):
	try:
		if type == 'single':
			se.append("items",{
					"item_code": self.item_code,
					"qty": self.dust_weight,
					"s_warehouse": self.source_warehouse,
					"t_warehouse": self.refining_warehouse,
					"to_department": self.refining_department,
				})
		elif type == 'refining_department_detail':
			for row in self.refining_department_detail:
				source_warehouse = frappe.db.get_value('Warehouse',{"department":row.department},'name')
				se.append("items",{
					"item_code": self.item_code,
					"qty": flt((self.dust_weight*row.ratio)/100),
					"s_warehouse": source_warehouse,
					"t_warehouse": self.refining_warehouse,
					"to_department": self.refining_department,
				})
		elif type == 'refining_operation_detail':
			for row in self.refining_operation_detail:
				allocate_dust_employee_wise_operations(self,row,se)
			
	except Exception as e:
		frappe.throw(f"Error while Receiving Dust from : {e}")


def get_item_based_on_purity(self):
	if not self.metal_purity:
		frappe.throw(f"Please Select Metal Purity")
	elif self.fine_weight <= 0:
		frappe.throw(f"Fine Weight Should be Greater Than 0")

	metal_touch = frappe.db.get_value('Attribute Value',{'name':self.metal_purity},'metal_touch')

	recovered_item = get_item_from_attribute('Gold', metal_touch, self.metal_purity, "Yellow")
	
	recovered_item = recovered_item if recovered_item else 'Refined Gold'

	frappe.db.set_value('Refining', self.name, 'recovered_item', recovered_item)
	return recovered_item

def allocate_dust_employee_wise_operations(self,row,se):
	list_of_operation = frappe.db.get_list('Manufacturing Operation', filters=[
		['start_time', '>=', self.date_from],
		['finish_time', '<=',self.date_to],
		['operation','=',row.operation]],
		fields=['name','operation','employee','SUM(net_wt) as net_wt'],
		group_by='employee'
		)

	dust_weight = flt((self.dust_weight*row.ratio)/100)
	total_net_wt = sum([operation.get('net_wt') for operation in list_of_operation])

	for operation in list_of_operation:
		source_warehouse = frappe.db.get_value('Warehouse',{"employee":operation.employee},'name')
		
		se.append("items",{
			"item_code": self.item_code,
			"qty": dust_weight*operation.net_wt/total_net_wt,
			"s_warehouse": source_warehouse,
			"t_warehouse": self.refining_warehouse,
			"to_department": self.refining_department,
		})
		
def enter_stock_row(self,se,recovered_item):
	se.append("items",{
		"item_code": self.item_code,
		"qty": self.dust_weight,
		"s_warehouse": self.refining_warehouse,
		"to_department": self.refining_department,
	})
			
	se.append("items",{
		"item_code": recovered_item,
		"qty": self.fine_weight,
		"t_warehouse": self.refining_warehouse,
		"to_department": self.refining_department,
	})