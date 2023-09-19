# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe,json
from frappe.model.document import Document
from typing import Optional

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull, Max, Min
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

class demoManufacturingOperation(Document):
	pass

class OverlapError(frappe.ValidationError):
	pass

###class
class demoManufacturingOperation(Document):

	def validate(self):
		self.validate_time_logs()
		# self.set_status()
		
	def validate_time_logs(self):
		self.total_time_in_mins = 0.0
		# self.total_completed_qty = 0.0

		if self.get("time_logs"):
			print
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
					self.total_time_in_mins += d.time_in_mins

				# if d.completed_qty and not self.sub_operations:
				# 	self.total_completed_qty += d.completed_qty

			# self.total_completed_qty = flt(self.total_completed_qty, self.precision("total_completed_qty"))

		# for row in self.sub_operations:
		# 	self.total_completed_qty += row.completed_qty

	def get_overlap_for(self, args, check_next_available_slot=False):
		production_capacity = 1

		jc = frappe.qb.DocType("demo Manufacturing Operation")
		jctl = frappe.qb.DocType("Job Card Time Log")

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

	def add_time_log(self, args):
		last_row = []
		employees = args.employees
		if isinstance(employees, str):
			employees = json.loads(employees)

		if self.time_logs and len(self.time_logs) > 0:
			last_row = self.time_logs[-1]

		self.reset_timer_value(args)
		if last_row and args.get("complete_time"):
			for row in self.time_logs:
				if not row.to_time:
					row.update(
						{
							"to_time": get_datetime(args.get("complete_time")),
							"operation": args.get("sub_operation")
							# "completed_qty": args.get("completed_qty") or 0.0,
						}
					)
		elif args.get("start_time"):
			new_args = frappe._dict(
				{
					"from_time": get_datetime(args.get("start_time")),
					"operation": args.get("sub_operation")
					# "completed_qty": 0.0,
				}
			)

			if employees:
				for name in employees:
					new_args.employee = name.get("employee")
					self.add_start_time_log(new_args)
			else:
				self.add_start_time_log(new_args)

		if not self.employee and employees:
			self.set_employees(employees)

		if self.status == "QC Pending" :
		# and self.status == "On Hold":
			self.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)
			 
		elif self.status == "On Hold":
			self.current_time = time_diff_in_seconds(last_row.to_time, last_row.from_time)
			
		else: 
			print(self)
			
		self.save()

	def add_start_time_log(self, args):
		self.append("time_logs", args)

	def set_employees(self, employees):
		for name in employees:
			self.append("employee", {"employee": name.get("employee") })
							# "completed_qty": 0.0

	def reset_timer_value(self, args):
		self.started_time = None

		if args.get("status") in ["Work In Progress","QC Pending", "Complete"]:
			self.current_time = 0.0
			# print(args.get("status"))

			#pause
			if args.get("status") == "Work In Progress":
				self.started_time = get_datetime(args.get("start_time"))
				print("here 1",args.get("status"))
			
		if args.get("status") == "QC Pending":
			self.started_time = get_datetime(args.get("start_time"))
			print(args.get("status"))

		# if args.get("status") == "Resume Job":
		# 	print("here ::",args.get("status"))
		# 	args["status"] = "QC Pending"
		# 	# print(args.get("status"))

		# if args.get("status") == "Pause Job":
		# 	args["status"] = "Work In Progress"
			# print(args.get("status"))

		if args.get("status") == "Resume Job":
			print("here 2",args.get("status"))
			args["status"] = "Work In Progress"

		if args.get("status"):
			self.status = args.get("status")
			# print(args.get("status"))
	
####### function
@frappe.whitelist()
def make_time_log(args):
	if isinstance(args, str):
		args = json.loads(args)

	args = frappe._dict(args)
	doc = frappe.get_doc("demo Manufacturing Operation", args.job_card_id)
	# doc.validate_sequence_id()
	doc.add_time_log(args)
