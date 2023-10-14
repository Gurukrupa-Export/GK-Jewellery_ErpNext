# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe,json
from frappe import _ ,bold
from frappe.utils import now, time_diff
from frappe.query_builder import Criterion
from frappe.model.document import Document
from jewellery_erpnext.utils import set_values_in_bulk
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
class OperationSequenceError(frappe.ValidationError):
	pass

class OverlapError(frappe.ValidationError):
	pass

class ManufacturingOperation(Document):
	

	def reset_timer_value(self, args):
		self.started_time = None

		if args.get("status") in ["WIP", "Finished"]:
			self.current_time = 0.0

			if args.get("status") == "WIP":
				self.started_time = get_datetime(args.get("start_time"))

		if args.get("status") == "QC Pending":
			self.started_time = get_datetime(args.get("start_time"))

		if args.get("status") == "Resume Job":
			args["status"] = "WIP"

		if args.get("status"):
			self.status = args.get("status")

	def add_start_time_log(self, args):
		self.append("time_logs", args)

	def add_time_log(self, args):
		last_row = []
		employees = args.employees
		# if isinstance(employees, str):
		# 	employees = json.loads(employees)
		if self.time_logs and len(self.time_logs) > 0:
			last_row = self.time_logs[-1]

		self.reset_timer_value(args)
		if last_row and args.get("complete_time"):
			for row in self.time_logs:
				if not row.to_time:
					row.update(
						{
							"to_time": get_datetime(args.get("complete_time")),
							# "operation": args.get("sub_operation")
							# "completed_qty": args.get("completed_qty") or 0.0,
						}
					)
		elif args.get("start_time"):
			new_args = frappe._dict(
				{
					"from_time": get_datetime(args.get("start_time")),
					# "operation": args.get("sub_operation"),
					# "completed_qty": 0.0,
				}
			)

			if employees:
				# for name in employees:
				new_args.employee = employees
				self.add_start_time_log(new_args)
			else:
				self.add_start_time_log(new_args)

		if not self.employee and employees:
			self.set_employees(employees)

		# if self.status == "On Hold":
		# 	self.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)

		if self.status == "QC Pending" :
		# and self.status == "On Hold":
			self.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)
			 
		elif self.status == "On Hold":
			self.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)
			
		else: 
			# a = self
			print(self)

		self.save()

	def set_employees(self, employees):
		# for name in employees:
		# self.append("employee", {"employee": employees})
		self.employee = employees
		
		
							# , "completed_qty": 0.0
	# def validate_sequence_id(self):
	# 	# if self.is_corrective_job_card:
	# 	# 	return

	# 	# if not (self.work_order and self.sequence_id):
	# 	# 	return

	# 	# current_operation_qty = 0.0
	# 	# data = self.get_current_operation_data()
	# 	# if data and len(data) > 0:
	# 	# 	current_operation_qty = flt(data[0].completed_qty)

	# 	# current_operation_qty += flt(self.total_completed_qty)

	# 	data = frappe.get_all(
	# 		"Work Order Operation",
	# 		fields=["operation", "status", "completed_qty", "sequence_id"],
	# 		filters={"docstatus": 1, "parent": self.work_order, "sequence_id": ("<", self.sequence_id)},
	# 		order_by="sequence_id, idx",
	# 	)

	# 	message = "Job Card {0}: As per the sequence of the operations in the work order {1}".format(
	# 		bold(self.name), bold(get_link_to_form("Work Order", self.work_order))
	# 	)

	# 	for row in data:
	# 		if row.status != "Completed" and row.completed_qty < current_operation_qty:
	# 			frappe.throw(
	# 				_("{0}, complete the operation {1} before the operation {2}.").format(
	# 					message, bold(row.operation), bold(self.operation)
	# 				),
	# 				OperationSequenceError,
	# 			)

	# 		if row.completed_qty < current_operation_qty:
	# 			msg = f"""The completed quantity {bold(current_operation_qty)}
	# 				of an operation {bold(self.operation)} cannot be greater
	# 				than the completed quantity {bold(row.completed_qty)}
	# 				of a previous operation
	# 				{bold(row.operation)}.
	# 			"""

	# 			frappe.throw(_(msg))
	def validate(self):
		self.set_start_finish_time()
		self.validate_time_logs()
		# self.update_weights()
		self.validate_loss()
		# self.validate_time_logs()

	def validate_time_logs(self):
		self.total_time_in_mins = 0.0
		# self.total_completed_qty = 0.0

		if self.get("time_logs"):
			for d in self.get("time_logs"):
				if d.to_time and get_datetime(d.from_time) > get_datetime(d.to_time):
					frappe.throw(_("Row {0}: From time must be less than to time").format(d.idx))

				data = self.get_overlap_for(d)
				if data:
					frappe.throw(
						_("Row {0}: From Time and To Time of {1} is overlapping with {2}").format(
							d.idx, self.name, data.name
						),
						OverlapError,
					)

				if d.from_time and d.to_time:
					d.time_in_mins = time_diff_in_hours(d.to_time, d.from_time) * 60
					in_hours = time_diff(d.to_time, d.from_time)
					d.time_in_hour = str(in_hours)[:-3]
					self.total_time_in_mins += d.time_in_mins

					default_shift = frappe.db.get_value('Employee',d.employee,'default_shift')
					shift_hours = frappe.db.get_value('Shift Type',default_shift,['start_time','end_time'])
					total_shift_hours = time_diff(shift_hours[1], shift_hours[0])
					
					if in_hours >= total_shift_hours:
						d.time_in_days = in_hours/total_shift_hours
						

			# frappe.throw('HOLD')

				# if d.completed_qty and not self.sub_operations:
				# 	self.total_completed_qty += d.completed_qty

			# self.total_completed_qty = flt(self.total_completed_qty, self.precision("total_completed_qty"))

		# for row in self.sub_operations:
		# 	self.total_completed_qty += row.completed_qty

	def update_corrective_in_work_order(self, wo):
		wo.corrective_operation_cost = 0.0
		for row in frappe.get_all(
			"Job Card",
			fields=["total_time_in_mins", "hour_rate"],
			filters={"is_corrective_job_card": 1, "docstatus": 1, "work_order": self.work_order},
		):
			wo.corrective_operation_cost += flt(row.total_time_in_mins) * flt(row.hour_rate)

		wo.calculate_operating_cost()
		wo.flags.ignore_validate_update_after_submit = True
		wo.save()

	def get_current_operation_data(self):
		return frappe.get_all(
			"Job Card",
			fields=[
				"sum(total_time_in_mins) as time_in_mins",
				"sum(total_completed_qty) as completed_qty",
				"sum(process_loss_qty) as process_loss_qty",
			],
			filters={
				"docstatus": 1,
				"work_order": self.work_order,
				"operation_id": self.operation_id,
				"is_corrective_job_card": 0,
			},
		)

	def get_overlap_for(self, args, check_next_available_slot=False):
		production_capacity = 1

		jc = frappe.qb.DocType("Manufacturing Operation")
		# jctl = frappe.qb.DocType("Job Card Time Log")
		jctl = frappe.qb.DocType("Manufacturing Operation  Time Log")

		time_conditions = [
			((jctl.from_time < args.from_time) & (jctl.to_time > args.from_time)),
			((jctl.from_time < args.to_time) & (jctl.to_time > args.to_time)),
			((jctl.from_time >= args.from_time) & (jctl.to_time <= args.to_time)),
		]

		if check_next_available_slot:
			time_conditions.append(((jctl.from_time >= args.from_time) & (jctl.to_time >= args.to_time)))

		query = (
			frappe.qb.from_(jctl)
			.from_(jc)
			.select(jc.name.as_("name"), jctl.to_time)
		#    , jc.workstation, jc.workstation_type
			.where(
				(jctl.parent == jc.name)
				& (Criterion.any(time_conditions))
				& (jctl.name != f"{args.name or 'No Name'}")
				& (jc.name != f"{args.parent or 'No Name'}")
				& (jc.docstatus < 2)
			)
			.orderby(jctl.to_time, order=frappe.qb.desc)
		)

		# if self.workstation_type:
		# 	query = query.where(jc.workstation_type == self.workstation_type)

		# if self.workstation:
		# 	production_capacity = (
		# 		frappe.get_cached_value("Workstation", self.workstation, "production_capacity") or 1
		# 	)
		# 	query = query.where(jc.workstation == self.workstation)

		if args.get("employee"):
			# override capacity for employee
			production_capacity = 1
			query = query.where(jctl.employee == args.get("employee"))

		existing = query.run(as_dict=True)

		if existing and production_capacity > len(existing):
			return

		# if self.workstation_type:
		# 	if workstation := self.get_workstation_based_on_available_slot(existing):
		# 		self.workstation = workstation
		# 		return None

		return existing[0] if existing else None


	def update_weights(self):
		res = get_material_wt(self)
		self.update(res)

	def validate_loss(self):
		if self.is_new() or not self.loss_details:
			return
		items = get_stock_entries_against_mfg_operation(self)
		for row in self.loss_details:
			if row.item_code not in items.keys():
				frappe.throw(_(f"Row #{row.idx}: Invalid item for loss"), title="Loss Details")
			if row.stock_uom != items[row.item_code].get("uom"):
				frappe.throw(_(f"Row #{row.idx}: UOM should be {items[row.item_code].get('uom')}"), title="Loss Details") 
			if row.stock_qty > items[row.item_code].get("qty",0):
				frappe.throw(_(f"Row #{row.idx}: qty cannot be greater than {items[row.item_code].get('qty',0)}"), title="Loss Details")

	def set_start_finish_time(self):
		if self.has_value_changed("status"):
			if self.status == "WIP" and not self.start_time:
				self.start_time = now()
				self.finish_time = None
			elif self.status == "Finished":
				if not self.start_time:
					self.start_time = now()
				self.finish_time = now()
		if self.start_time and self.finish_time:
			self.time_taken = time_diff(self.finish_time, self.start_time)
	
	@frappe.whitelist()
	def create_fg(self):
		create_manufacturing_entry(self)
		pmo = frappe.db.get_value("Manufacturing Work Order", self.manufacturing_work_order, "manufacturing_order")
		wo = frappe.get_all("Manufacturing Work Order", {"manufacturing_order": pmo}, pluck="name")
		set_values_in_bulk("Manufacturing Work Order", wo, {"status": "Completed"})

	@frappe.whitelist()
	def get_linked_stock_entries(self):
		target_wh = frappe.db.get_value("Warehouse",{"department": self.department})
		pmo = frappe.db.get_value("Manufacturing Work Order", self.manufacturing_work_order, "manufacturing_order")
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Manufacture"
		mwo = frappe.get_all("Manufacturing Work Order",
					{"name": ["!=",self.manufacturing_work_order],"manufacturing_order": pmo, "docstatus":["!=",2], "department":["=",self.department]},
					pluck="name")
		data = frappe.db.sql(f"""select se.manufacturing_work_order, se.manufacturing_operation, sed.parent, sed.item_code,sed.item_name, sed.qty, sed.uom 
		       				from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name where
							se.docstatus = 1 and se.manufacturing_work_order in ('{"', '".join(mwo)}') and sed.t_warehouse = '{target_wh}' 
							group by sed.manufacturing_operation,  sed.item_code, sed.qty, sed.uom """, as_dict=1)

		return frappe.render_template("jewellery_erpnext/jewellery_erpnext/doctype/manufacturing_operation/stock_entry_details.html", {"data":data})

def create_manufacturing_entry(doc):
	target_wh = frappe.db.get_value("Warehouse",{"department": doc.department})
	pmo = frappe.db.get_value("Manufacturing Work Order", doc.manufacturing_work_order, "manufacturing_order")
	pmo_det = frappe.db.get_value("Parent Manufacturing Order", pmo, ["item_code", "qty"], as_dict=1)
	se = frappe.get_doc({
		"doctype": "Stock Entry",
		"purpose": "Manufacture",
		"manufacturing_order": pmo,
		"stock_entry_type": "Manufacture",
		"department": doc.department,
		"to_department": doc.department,
		"manufacturing_work_order": doc.manufacturing_work_order,
		"manufacturing_operation": doc.name,
		"inventory_type": "Regular Stock",
		"auto_created":1
		})
	mwo = frappe.get_all("Manufacturing Work Order",
			      {"name": ["!=",doc.manufacturing_work_order],"manufacturing_order": pmo, "docstatus":["!=",2], "department":["=",doc.department]},
				  pluck="name")
	data = frappe.db.sql(f"""select se.manufacturing_work_order, se.manufacturing_operation, sed.parent, sed.item_code,sed.item_name, sed.qty, sed.uom 
		      				from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name where
							se.docstatus = 1 and se.manufacturing_work_order in ('{"', '".join(mwo)}') and sed.t_warehouse = '{target_wh}' 
							group by sed.manufacturing_operation,  sed.item_code, sed.qty, sed.uom """, as_dict=1)
	for entry in data:
		se.append("items",{
			"item_code": entry.item_code,
			"qty": entry.qty,
			"uom": entry.uom,
			"manufacturing_operation": doc.name,
			"department": doc.department,
			"to_department": doc.department,
			"s_warehouse": target_wh
		})
	se.append("items",{
		"item_code": pmo_det.item_code,
		"qty": pmo_det.qty,
		"t_warehouse": target_wh,
		"department": doc.department,
		"to_department": doc.department,
		"manufacturing_operation": doc.name,
		"is_finished_item":1
	})
	se.save()
	se.submit()
	frappe.msgprint('Finished Good created successfully')

def get_stock_entries_against_mfg_operation(doc):
	if isinstance(doc, str):
		doc = frappe.get_doc("Manufacturing Operation", doc)
	wh = frappe.db.get_value("Warehouse", {"department": doc.department}, "name")
	if doc.employee:
		wh = frappe.db.get_value("Warehouse", {"employee": doc.employee}, "name")
	sed = frappe.db.get_all("Stock Entry Detail", filters={"t_warehouse": wh, "manufacturing_operation": doc.name, "docstatus": 1}, fields=["item_code", "qty", "uom"])
	items = {}
	for row in sed:
		existing = items.get(row.item_code)
		if existing:
			qty = existing.get("qty",0) + row.qty
		else:
			qty = row.qty
		items[row.item_code] = {"qty": qty, "uom": row.uom}
	return items

def get_loss_details(docname):
	data = frappe.get_all("Operation Loss Details", {"parent": docname}, ["item_code", "stock_qty as qty", "stock_uom as uom"])
	items = {}
	for row in data:
		existing = items.get(row.item_code)
		if existing:
			qty = existing.get("qty",0) + row.qty
		else:
			qty = row.qty
		items[row.item_code] = {"qty": qty, "uom": row.uom}
	return items

def get_previous_operation(manufacturing_operation):
	mfg_operation = frappe.db.get_value("Manufacturing Operation", manufacturing_operation, ["previous_operation", "manufacturing_work_order"], as_dict=1)
	if not mfg_operation.previous_operation:
		return None
	return frappe.db.get_value("Manufacturing Operation", {"operation": mfg_operation.previous_operation, "manufacturing_work_order": mfg_operation.manufacturing_work_order})

def get_material_wt(doc):
	filters = {}
	if doc.for_subcontracting:
		if doc.subcontractor:
			filters["subcontractor"] = doc.subcontractor
	else:
		if doc.employee:
			filters["employee"] = doc.employee
	if not filters:
		filters["department"] = doc.department
	t_warehouse = frappe.db.get_value("Warehouse", filters, "name")
	res = frappe.db.sql(f"""select ifnull(sum(if(sed.uom='cts',sed.qty*0.2, sed.qty)),0) as gross_wt, ifnull(sum(if(i.variant_of = 'M',sed.qty,0)),0) as net_wt,
        ifnull(sum(if(i.variant_of = 'D',sed.qty,0)),0) as diamond_wt, ifnull(sum(if(i.variant_of = 'D',if(sed.uom='cts',sed.qty*0.2, sed.qty),0)),0) as diamond_wt_in_gram,
        ifnull(sum(if(i.variant_of = 'G',sed.qty,0)),0) as gemstone_wt, ifnull(sum(if(i.variant_of = 'G',if(sed.uom='cts',sed.qty*0.2, sed.qty),0)),0) as gemstone_wt_in_gram,
        ifnull(sum(if(i.variant_of = 'O',sed.qty,0)),0) as other_wt
        from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name left join `tabItem` i on i.name = sed.item_code 
		    where sed.t_warehouse = "{t_warehouse}" and sed.manufacturing_operation = "{doc.name}" and se.docstatus = 1""", as_dict=1)
	if res:
		return res[0]
	return {}

@frappe.whitelist()
def make_time_log(args):
	if isinstance(args, str):
		args = json.loads(args)
	args = frappe._dict(args)
	doc = frappe.get_doc("Manufacturing Operation", args.job_card_id)
	# doc.validate_sequence_id()
	doc.add_time_log(args)