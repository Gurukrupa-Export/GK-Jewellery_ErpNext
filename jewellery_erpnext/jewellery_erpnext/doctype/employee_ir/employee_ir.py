# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
import json
from datetime import datetime
from frappe import _
from frappe.utils import flt, cint, today
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from jewellery_erpnext.jewellery_erpnext.doctype.main_slip.main_slip import get_main_slip_item
from jewellery_erpnext.jewellery_erpnext.doctype.department_ir.department_ir import update_stock_entry_dimensions, get_material_wt
from jewellery_erpnext.utils import update_existing, get_item_from_attribute
from jewellery_erpnext.jewellery_erpnext.doctype.qc.qc import create_qc_record
from jewellery_erpnext.jewellery_erpnext.doctype.manufacturing_operation.manufacturing_operation import get_loss_details, get_previous_operation
from frappe.utils import (
	add_days,
	add_to_date,
	cint,
	flt,
	get_datetime,
	get_link_to_form,
	get_time,
	getdate,
	time_diff,
	time_diff_in_hours,
	time_diff_in_seconds,
)

class EmployeeIR(Document):
	@frappe.whitelist()
	def get_operations(self):
		records = frappe.get_list("Manufacturing Operation",{"department": self.department,
						       "employee": ["is","not set"], "operation": ["is","not set"]},["name","gross_wt"])
		self.employee_ir_operations = []
		if records:
			for row in records:
				self.append("employee_ir_operations",{
					"manufacturing_operation": row.name
				})

	def on_submit(self):
		if self.type == "Issue":
			self.on_submit_issue()
			if self.subcontracting == "Yes":
				self.create_subcontracting_order()
		else:
			self.on_submit_receive()
	
	def validate(self):
		self.validate_gross_wt()
		self.update_main_slip()
		if not self.is_new():
			self.validate_qc("Warn")

	def after_insert(self):
		self.validate_qc("Warn")

	def on_cancel(self):
		if self.type == "Issue":
			self.on_submit_issue(cancel=True)
		else:
			self.on_submit_receive(cancel=True)

	def validate_gross_wt(self):
		precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
		for row in self.employee_ir_operations:
			row.gross_wt = frappe.db.get_value("Manufacturing Operation", row.manufacturing_operation, 'gross_wt')
			if not self.main_slip:
				if flt(row.gross_wt, precision) < flt(row.received_gross_wt, precision):
					frappe.throw(f"Row #{row.idx}: Received gross wt cannot be greater than gross wt")

	#for issue
	def on_submit_issue(self, cancel=False):
		now = datetime.now()
		dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
		employee = None if cancel else self.employee
		operation = None if cancel else self.operation
		status = "Not Started" if cancel else "WIP"
		values = {"operation": operation, "status": status}

		if self.subcontracting == "Yes":
			values["for_subcontracting"] = 1 
			values["subcontractor"] = None if cancel else self.subcontractor
		else:
			values["employee"] = employee

		for row in self.employee_ir_operations:
			if not cancel:
				update_stock_entry_dimensions(self, row, row.manufacturing_operation, True)
				create_stock_entry(self,row)
				res = get_material_wt(self, row.manufacturing_operation)
				row.gross_wt = res.get('gross_wt')
				values.update(res)
			# values["gross_wt"] = get_value("Stock Entry Detail", {'manufacturing_operation': row.manufacturing_operation, "to_employee":self.employee}, 'sum(if(uom="cts",qty*0.2,qty))', 0)
			frappe.db.set_value("Manufacturing Operation", row.manufacturing_operation, values)
			values["start_time"] = dt_string
			doc = frappe.get_doc("Manufacturing Operation", row.manufacturing_operation)
			add_time_log(doc,values)
			# frappe.throw('HOLD')

	#for receive
	def on_submit_receive(self, cancel=False):
		self.validate_qc("Stop")
		now = datetime.now()
		dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
		precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
		for row in self.employee_ir_operations:

			res = {"received_gross_wt": row.received_gross_wt}
			res["employee"] = self.employee
			status = "WIP"
			if not cancel:
				status = "Finished"
				create_operation_for_next_op(row.manufacturing_operation, employee_ir=self.name)
				res["complete_time"] = dt_string
				doc = frappe.get_doc("Manufacturing Operation", row.manufacturing_operation)

				add_time_log(doc,res)
				difference_wt = flt(row.received_gross_wt, precision) - flt(row.gross_wt, precision)
				create_stock_entry(self, row, flt(difference_wt, 3))
				# res = get_material_wt(self, row.manufacturing_operation)
			else:
				op = frappe.db.get_value("Manufacturing Operation", {"employee_ir": self.name})
				if op:
					frappe.delete_doc("Manufacturing Operation", op, ignore_permissions=1)
					if self.is_qc_reqd:
						status = "QC Pending"
				# need to handle cancellation
				# mfg_operation = frappe.db.exists("Manufacturing Operation", {"employee_ir": self.name})
			res["status"] = status
			# gross_wt = get_value("Stock Entry Detail", {'manufacturing_operation': row.manufacturing_operation, "employee":self.employee}, 'sum(if(uom="cts",qty*0.2,qty))', 0)
			frappe.set_value("Manufacturing Operation", row.manufacturing_operation, res)

	def validate_qc(self, action = 'Warn'):
		if not self.is_qc_reqd or self.type == "Issue":
			return
	
		qc_list = []
		for row in self.employee_ir_operations:
			operation = frappe.db.get_value("Manufacturing Operation",row.manufacturing_operation, ["status"], as_dict=1)
			if operation.get("status") in ['QC Pending',"WIP"]:
				if action == "Warn":
					create_qc_record(row, self.operation, self.name)
				qc_list.append(row.manufacturing_operation)
		if qc_list:
			msg = f"Please complete QC for the following: {', '.join(qc_list)}"
			if action == "Warn":
				frappe.msgprint(_(msg))
			elif action == 'Stop':
				frappe.throw(_(msg))		

	def update_main_slip(self):
		if not self.main_slip or not self.is_main_slip_required:
			return
		
		main_slip = frappe.get_doc("Main Slip",self.main_slip)
		for row in self.employee_ir_operations:
			if not main_slip.get("main_slip_operation",{"manufacturing_operation":row.manufacturing_operation}):
				main_slip.append("main_slip_operation",{"manufacturing_operation":row.manufacturing_operation})
		main_slip.save()

	@frappe.whitelist()
	def create_subcontracting_order(self):
		service_item = frappe.db.get_value("Department Operation", self.operation, "service_item")
		if not service_item:
			frappe.throw(_(f"Please set service item for {self.operation}"))
		skip_operations = []
		po = frappe.new_doc("Purchase Order")
		po.supplier = self.subcontractor
		po.company = self.company
		po.employee_ir = self.name
		for row in self.employee_ir_operations:
			if not row.gross_wt:
				skip_operations.append(row.manufacturing_operation)
				continue
			po.append("items", {
				"item_code": service_item,
				"qty": row.gross_wt,
				"schedule_date": today(),
				"manufacturing_operation": row.manufacturing_operation
			})
		if skip_operations:
			frappe.throw(f"PO creation skipped for following Manufacturing Operations due to zero gross weight: {', '.join(skip_operations)}")
		if not po.items:
			return
		po.flags.ignore_mandatory = True
		po.save()
		po.db_set("schedule_date", None)
		for row in po.items:
			row.db_set("schedule_date", None)

def create_operation_for_next_op(docname, target_doc=None, employee_ir = None):
	def set_missing_value(source, target):
		target.previous_operation = source.operation
		target.prev_gross_wt = source.received_gross_wt or source.gross_wt or source.prev_gross_wt

	target_doc = get_mapped_doc("Manufacturing Operation", docname,
			{
			"Manufacturing Operation" : {
				"doctype":	"Manufacturing Operation",
				"field_no_map": ['status','employee',"start_time", "subcontractor", "for_subcontracting"
		     					"finish_time", "time_taken", "department_issue_id",
								"department_receive_id", "department_ir_status", "operation", "previous_operation"]
			}
			}, target_doc, set_missing_value)
	target_doc.employee_ir = employee_ir
	target_doc.time_taken = None
	target_doc.save()
	target_doc.db_set("employee", None)

	target_doc.start_time = ""
	target_doc.finish_time = ""
	target_doc.time_taken = ""
	target_doc.started_time = ""
	target_doc.current_time= ""
	target_doc.time_logs = []
	target_doc.total_time_in_mins = ""
	target_doc.save()

@frappe.whitelist()
def get_manufacturing_operations(source_name, target_doc=None):
	if not target_doc:
		target_doc = frappe.new_doc("Employee IR")
	elif isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))
	if not target_doc.get("employee_ir_operations",{"manufacturing_operation":source_name}):
		operation = frappe.db.get_value("Manufacturing Operation", source_name, ["gross_wt","manufacturing_work_order"],as_dict=1)
		target_doc.append("employee_ir_operations",{"manufacturing_operation":source_name, 
					      "gross_wt": operation["gross_wt"], "manufacturing_work_order": operation["manufacturing_work_order"]})
	return target_doc

def create_stock_entry(doc, row, difference_wt=0):
	department_wh = frappe.get_value("Warehouse", {"department": doc.department})
	if doc.subcontracting == "Yes":
		employee_wh = frappe.get_value("Warehouse", {"subcontractor": doc.subcontractor})
	else:
		employee_wh = frappe.get_value("Warehouse", {"employee": doc.employee})
	if not department_wh:
		frappe.throw(_(f"Please set warhouse for department {doc.department}"))
	if not employee_wh:
		frappe.throw(_(f"Please set warhouse for {'subcontractor' if doc.subcontracting == 'Yes' else 'employee'} {doc.subcontractor if doc.subcontracting == 'Yes' else doc.employee}"))
	stock_entries = frappe.db.sql(f"""select se.name from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name 
			       where se.docstatus=1 and sed.manufacturing_operation = '{row.manufacturing_operation}' and 
				   {"sed.t_warehouse" if doc.type == "Issue" else "sed.s_warehouse"} = '{department_wh}' 
				   and sed.to_department = '{doc.department}' group by se.name order by se.creation""", as_dict=1, pluck=1)
	if doc.type == "Issue" and not stock_entries:
		prev_mfg_operation = get_previous_operation(row.manufacturing_operation)
		stock_entries = frappe.db.sql(f"""select se.name from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name 
			       where se.docstatus=1 and sed.manufacturing_operation = '{prev_mfg_operation}' and 
				   sed.t_warehouse = '{department_wh}' and (sed.employee is not NULL or sed.subcontractor is not NULL)
				   and sed.to_department = '{doc.department}' group by se.name order by se.creation""", as_dict=1, pluck=1)
	item = None
	metal_item = None
	if doc.main_slip:
		item = get_main_slip_item(doc.main_slip)

	existing_items = frappe.get_all("Stock Entry Detail",{"parent": ['in',stock_entries]}, pluck='item_code')
	if difference_wt != 0:
		mwo = frappe.db.get_value("Manufacturing Work Order", row.manufacturing_work_order, ["metal_type", "metal_touch", "metal_purity", "metal_colour"], as_dict=1)
		metal_item = get_item_from_attribute(mwo.metal_type, mwo.metal_touch, mwo.metal_purity, mwo.metal_colour)
		if (metal_item not in existing_items) and difference_wt < 0:
			frappe.throw(_(f"Stock Entry for metal not found. Unable to subtract weight difference({difference_wt})"))
	loss = {}
	if doc.type == "Receive":
		loss = get_loss_details(row.manufacturing_operation)
	if loss.get("total_loss"):
		difference_wt = flt(difference_wt + loss.get("total_loss",0), 3)
	row.db_set("gold_loss", difference_wt)
	for stock_entry in stock_entries:
		existing_doc = frappe.get_doc("Stock Entry", stock_entry)
		se_doc = frappe.copy_doc(existing_doc)
		for child in se_doc.items:
			if child.item_code in loss.keys():
				loss_qty = loss[child.item_code].get("qty",0)
				if child.qty == loss_qty or child.qty < loss_qty:
					loss[child.item_code]["qty"] = loss_qty - child.qty
					se_doc.remove(child)
					continue
				else:
					child.qty = child.qty - loss_qty
					loss[child.item_code]["qty"] = child.qty

			if doc.type == "Issue":
				se_doc.stock_entry_type = 'Material Transfer to Subcontractor' if doc.subcontracting == "Yes" else "Material Transfer to Employee"
				child.s_warehouse = department_wh
				child.t_warehouse = employee_wh
				if doc.subcontracting == "Yes":
					child.to_subcontractor = doc.subcontractor
					child.subcontractor = None	
				else:
					child.to_employee = doc.employee
					child.employee = None
				child.department_operation = doc.operation
				child.main_slip = None
				child.to_main_slip = doc.main_slip if item == child.item_code else None
			else:
				se_doc.stock_entry_type = 'Material Transfer to Department'
				child.s_warehouse = employee_wh
				child.t_warehouse = department_wh
				if doc.subcontracting == "Yes":
					child.to_subcontractor = None
					child.subcontractor = doc.subcontractor
				else:
					child.to_employee = None
					child.employee = doc.employee
				child.to_main_slip = None
				child.main_slip = doc.main_slip if item == child.item_code else None
			child.qty = child.qty + (difference_wt if (metal_item == child.item_code) and difference_wt < 0 else 0)
			if child.qty < 0:
				frappe.throw(_("Qty cannot be negative"))
			child.manufacturing_operation = row.manufacturing_operation
			child.department = doc.department
			child.to_department = doc.department
			child.manufacturer =  doc.manufacturer
			child.material_request = None
			child.material_request_item = None
			if (metal_item == child.item_code) and difference_wt < 0:
				update_existing("Manufacturing Operation", row.manufacturing_operation, {"gross_wt": f"gross_wt + {difference_wt}", "net_wt": f"net_wt + {difference_wt}"})
		se_doc.department = doc.department
		se_doc.to_department = doc.department
		se_doc.to_employee = doc.employee if doc.type == "Issue" else None
		se_doc.employee = doc.employee if doc.type == "Receive" else None
		se_doc.to_subcontractor = doc.subcontractor if doc.type == "Issue" else None
		se_doc.subcontractor = doc.subcontractor if doc.type == "Receive" else None
		se_doc.auto_created = True
		se_doc.employee_ir = doc.name
		se_doc.manufacturing_operation = row.manufacturing_operation
		if not se_doc.items:
			continue
		se_doc.save()
		se_doc.submit()

	if difference_wt != 0:
		if not doc.main_slip:
			frappe.throw(_("Cannot add weight without Main Slip"))
		if doc.subcontracting == "Yes":
			convert_pure_metal(row.manufacturing_work_order, doc.main_slip, abs(difference_wt), employee_wh, employee_wh, reverse=(difference_wt < 0))

		se_doc = frappe.new_doc("Stock Entry")
		se_doc.stock_entry_type = "Material Transfer to Department"
		se_doc.purpose = "Material Transfer"
		se_doc.manufacturing_order = frappe.db.get_value("Manufacturing Work Order",row.manufacturing_work_order, "manufacturing_order")
		se_doc.manufacturing_work_order = row.manufacturing_work_order
		se_doc.manufacturing_operation = row.manufacturing_operation
		se_doc.department = doc.department
		se_doc.to_department = doc.department
		se_doc.main_slip = doc.main_slip
		se_doc.employee = doc.employee
		se_doc.subcontractor = doc.subcontractor
		se_doc.inventory_type = "Regular Stock"
		se_doc.auto_created = False
		se_doc.employee_ir = doc.name
		se_doc.append("items", {
			"item_code": metal_item,
			"s_warehouse": employee_wh,
			"t_warehouse": department_wh,
			"to_employee": None,
			"employee": doc.employee,
			"to_subcontractor": None,
			"subcontractor": doc.subcontractor,
			"to_main_slip": None,
			"main_slip": doc.main_slip,
			"qty": abs(difference_wt),
			"manufacturing_operation": row.manufacturing_operation,
			"department": doc.department,
			"to_department": doc.department,
			"manufacturer":  doc.manufacturer,
			"material_request": None,
			"material_request_item": None,
			"inventory_type": "Regular Stock"
		})
		se_doc.save()
		se_doc.submit()

def get_previous_operation(manufacturing_operation):
	mfg_operation = frappe.db.get_value("Manufacturing Operation", manufacturing_operation, ["previous_operation", "manufacturing_work_order"], as_dict=1)
	if not mfg_operation.previous_operation:
		return None
	return frappe.db.get_value("Manufacturing Operation", {"operation": mfg_operation.previous_operation, "manufacturing_work_order": mfg_operation.manufacturing_work_order})

def convert_pure_metal(mwo, ms, qty, s_warehouse, t_warehouse, reverse = False):
	from jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry import convert_metal_purity
	#source is ms(main slip) and passed qty is difference qty b/w issue and received gross wt i.e. mwo.qty
	mwo = frappe.db.get_value("Manufacturing Work Order", mwo, ["metal_type", "metal_touch", "metal_purity", "metal_colour"], as_dict=1)
	ms = frappe.db.get_value("Main Slip", ms, ["metal_type", "metal_touch", "metal_purity", "metal_colour"], as_dict=1)
	mwo.qty = qty
	if reverse:
		ms.qty = qty*flt(mwo.get("metal_purity"))/100
		convert_metal_purity(mwo, ms, s_warehouse, t_warehouse)
	else:
		ms.qty = qty*flt(mwo.get("metal_purity"))/100 
		convert_metal_purity(ms, mwo, s_warehouse, t_warehouse)


# @frappe.whitelist()
def add_time_log(doc, args):
		
		last_row = []
		employees = args['employee']
		
		# if isinstance(employees, str):
		# 	employees = json.loads(employees)
		if doc.time_logs and len(doc.time_logs) > 0:
			last_row = doc.time_logs[-1]
			

		doc.reset_timer_value(args)
		if last_row and args.get("complete_time"):
			for row in doc.time_logs:
				if not row.to_time:
					row.update(
						{
							"to_time": get_datetime(args.get("complete_time")),
						}
					)
		elif args.get("start_time"):
			new_args = frappe._dict(
				{
					"from_time": get_datetime(args.get("start_time")),
				}
			)

			if employees:
				new_args.employee = employees
				doc.add_start_time_log(new_args)
			else:
				doc.add_start_time_log(new_args)

		if not doc.employee and employees:
			doc.set_employees(employees)

		# if self.status == "On Hold":
		# 	self.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)

		if doc.status == "QC Pending" :
		# and self.status == "On Hold":
			doc.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)
			 
		elif doc.status == "On Hold":
			doc.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)
			
		# else: 
		# 	# a = self
		# 	print(doc)

		doc.save()