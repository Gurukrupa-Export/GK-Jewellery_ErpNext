# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _, scrub
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from jewellery_erpnext.utils import set_values_in_bulk, get_value
from jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry import update_manufacturing_operation
from jewellery_erpnext.jewellery_erpnext.doctype.manufacturing_operation.manufacturing_operation import get_previous_operation

class DepartmentIR(Document):
	@frappe.whitelist()
	def get_operations(self):
		dir_status = "In-Transit" if self.type == "Receive" else ["not in", ["In-Transit", "Received"]]
		filters = {
					"department_ir_status": dir_status
				}
		if self.type == "Issue":
			filters["status"] = ["in",["Finished","Revert"]]
			filters["department"]= self.current_department
		records = frappe.get_list("Manufacturing Operation",filters,["name","gross_wt"])
		self.department_ir_operation = []
		if records:
			for row in records:
				self.append("department_ir_operation",{
					"manufacturing_operation": row.name
				})

	def on_submit(self):
		if self.type == "Issue":
			self.on_submit_issue()
		else:
			self.on_submit_receive()

	def validate(self):
		if (self.current_department or self.next_department) and self.current_department == self.next_department:
			frappe.throw(_("Current and Next department cannot be same"))
		if self.type == 'Receive' and self.receive_against:
			if existing:=frappe.db.exists("Department IR",{"receive_against": self.receive_against, "name": ['!=',self.name], 'docstatus':["!=",2]}):
				frappe.throw(_(f"Department IR: {existing} already exist for Issue: {self.receive_against}"))
		for row in self.department_ir_operation:
			existing = frappe.db.sql(f"""select di.name from `tabDepartment IR Operation` dip left join `tabDepartment IR` di on dip.parent = di.name
			    					where di.docstatus != 2 and di.type = '{self.type}' and dip.name != '{row.name}' and dip.manufacturing_operation = '{row.manufacturing_operation}'""")
			if existing:
				frappe.throw(_(f"Row #{row.idx}: Found duplicate entry in Department IR: {existing[0][0]}"))

	def on_cancel(self):
		self.on_submit_receive(cancel=True)

	#for Receive
	def on_submit_receive(self, cancel=False):
		values = {}
		values["department_receive_id"] = self.name
		values["department_ir_status"] = "Received"
		for row in self.department_ir_operation:
			create_stock_entry(self, row)
			in_transit_wh = frappe.db.get_value("Manufacturing Setting", {"company": self.company},"in_transit")
			values["gross_wt"] = get_value("Stock Entry Detail", {'manufacturing_operation': row.manufacturing_operation,
								   "s_warehouse": in_transit_wh, "docstatus":1}, 'sum(if(uom="cts",qty*0.2,qty))', 0)
			res = get_material_wt(self, row.manufacturing_operation)
			values.update(res)
			frappe.db.set_value("Manufacturing Operation", row.manufacturing_operation, values)
			frappe.db.set_value("Manufacturing Work Order", row.manufacturing_work_order, 'department', self.current_department)

	#for Issue
	def on_submit_issue(self, cancel=False):
		for row in self.department_ir_operation:
			if cancel:
				new_operation = frappe.db.get_value("Manufacturing Operation", {"department_issue_id": self.name})
				if new_operation:
					frappe.delete_doc("Manufacturing Operation", new_operation, ignore_permissions=1)
				frappe.db.set_value("Manufacturing Operation", row.manufacturing_operation, "status", "Not Started")
			else:
				new_operation = create_operation_for_next_dept(self.name,row.manufacturing_operation, self.next_department)
				update_stock_entry_dimensions(self, row, new_operation)
				create_stock_entry_for_issue(self, row, new_operation)
				frappe.db.set_value("Manufacturing Operation", row.manufacturing_operation, "status", "Finished")

def update_stock_entry_dimensions(doc, row, manufacturing_operation, for_employee = False):
	filters = {}
	if for_employee:
		filters['employee' if doc.type == "Receive" else "to_employee"] = doc.employee
		current_dep = doc.department
		next_dep = doc.department
	else:
		current_dep = doc.current_department
		next_dep = doc.next_department
	filters.update({"manufacturing_work_order": row.manufacturing_work_order, "docstatus": 1,
					"manufacturing_operation": ["is", "not set"], "department": current_dep, "to_department": next_dep})
	stock_entries = frappe.get_all("Stock Entry", filters = filters, pluck="name")
	values = {
		"manufacturing_operation": manufacturing_operation
	}
	for stock_entry in stock_entries:
		rows = frappe.get_all("Stock Entry Detail", {"parent": stock_entry}, pluck = "name")
		set_values_in_bulk("Stock Entry Detail", rows, values)
		frappe.db.set_value("Stock Entry", stock_entry, values)
		update_manufacturing_operation(stock_entry)

def create_stock_entry(doc, row):
	in_transit_wh = frappe.db.get_value("Manufacturing Setting", {"company": doc.company},"in_transit")
	department_wh = frappe.get_value("Warehouse", {"department": doc.current_department})
	if not department_wh:
		frappe.throw(_(f"Please set warhouse for department {doc.current_department}"))
	stock_entries = frappe.get_all("Stock Entry Detail", {
						"manufacturing_operation": row.manufacturing_operation, "t_warehouse": in_transit_wh,
						"department": doc.previous_department, "to_department": doc.current_department, "docstatus": 1
					}, pluck="parent", group_by = "parent")
	for stock_entry in stock_entries:
		existing_doc = frappe.get_doc("Stock Entry", stock_entry)
		se_doc = frappe.copy_doc(existing_doc)
		for child in se_doc.items:
			child.s_warehouse = in_transit_wh
			child.t_warehouse = department_wh
			child.material_request = None
			child.material_request_item = None
			child.department = doc.previous_department
			child.to_department = doc.current_department
		se_doc.department = doc.previous_department
		se_doc.to_department = doc.current_department
		se_doc.auto_created = True
		se_doc.department_ir = doc.name
		se_doc.save()
		se_doc.submit()

def create_stock_entry_for_issue(doc, row, manufacturing_operation):
	in_transit_wh = frappe.db.get_value("Manufacturing Setting", {"company": doc.company},"in_transit")
	department_wh = frappe.get_value("Warehouse", {"department": doc.current_department})
	if not department_wh:
		frappe.throw(_(f"Please set warhouse for department {doc.current_department}"))
	stock_entries = frappe.get_all("Stock Entry Detail", {
						"manufacturing_operation": row.manufacturing_operation, "t_warehouse": department_wh,
						"to_department": doc.current_department, "docstatus": 1
					}, pluck="parent", group_by = "parent")
	if not stock_entries:
		prev_mfg_operation = get_previous_operation(row.manufacturing_operation)
		in_transit_wh = frappe.db.get_value("Manufacturing Setting", {"company": doc.company},"in_transit")

		stock_entries = frappe.get_all("Stock Entry Detail", filters={
							"manufacturing_operation": prev_mfg_operation, "t_warehouse": department_wh, 
							"to_department": doc.current_department, "docstatus": 1
						}, or_filters={"employee" : ["is", "set"], "subcontractor" : ["is", "set"] }, pluck="parent", group_by = "parent")
	for stock_entry in stock_entries:
		existing_doc = frappe.get_doc("Stock Entry", stock_entry)
		se_doc = frappe.copy_doc(existing_doc)
		for child in se_doc.items:
			child.t_warehouse = in_transit_wh
			child.s_warehouse = department_wh
			child.material_request = None
			child.material_request_item = None
			child.manufacturing_operation = manufacturing_operation
			child.department = doc.current_department
			child.to_department = doc.next_department
			child.to_main_slip = None
			child.main_slip = None
			child.employee = None
			child.to_employee = None
			child.subcontractor = None
			child.to_subcontractor = None
		
		se_doc.to_main_slip = None
		se_doc.main_slip = None
		se_doc.employee = None
		se_doc.to_employee = None
		se_doc.subcontractor = None
		se_doc.to_subcontractor = None
		se_doc.department = doc.current_department
		se_doc.to_department = doc.next_department
		se_doc.department_ir = doc.name
		se_doc.manufacturing_operation = manufacturing_operation
		se_doc.auto_created = True
		se_doc.save()
		se_doc.submit()


def create_operation_for_next_dept(ir_name,docname, next_department, target_doc = None):
	def set_missing_value(source, target):
		target.previous_operation = source.operation
		target.prev_gross_wt = source.received_gross_wt or source.gross_wt or source.prev_gross_wt

	target_doc = get_mapped_doc("Manufacturing Operation", docname,
			{
			"Manufacturing Operation" : {
				"doctype":	"Manufacturing Operation",
				"field_no_map": ['status','employee','department',"start_time","for_subcontracting", "subcontractor"
		     					"finish_time", "time_taken", "department_issue_id",
								"department_receive_id", "department_ir_status", "operation", "previous_operation"]
			}
			}, target_doc, set_missing_value)
	target_doc.department_issue_id = ir_name
	target_doc.department_ir_status = "In-Transit"
	target_doc.department = next_department
	target_doc.time_taken = None
	target_doc.save()
	target_doc.db_set("employee", None)
	return target_doc.name

@frappe.whitelist()
def get_manufacturing_operations(source_name, target_doc=None):
	if not target_doc:
		target_doc = frappe.new_doc("Department IR")
	elif isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))
	
	operation = frappe.db.get_value("Manufacturing Operation", source_name, ["gross_wt","manufacturing_work_order"],as_dict=1)
	if not target_doc.get("department_ir_operation",{"manufacturing_work_order": operation["manufacturing_work_order"]}):
		target_doc.append("department_ir_operation",{"manufacturing_operation":source_name, 
					      "manufacturing_work_order": operation["manufacturing_work_order"]})
	return target_doc

@frappe.whitelist()
def get_manufacturing_operations_from_department_ir(docname):
	return frappe.get_all("Manufacturing Operation",{"department_issue_id":docname, "department_ir_status": "In-Transit"}, ["name as manufacturing_operation", "manufacturing_work_order"])


@frappe.whitelist()
def department_receive_query(doctype, txt, searchfield, start, page_len, filters):
	args = {
		"txt": "%{0}%".format(txt),
	}
	condition = 'and name not in (select dp.receive_against from `tabDepartment IR` dp where dp.docstatus = 1 and dp.type = "Receive" and dp.receive_against is not NULL) '
	if filters.get("current_department"):
		args["current_department"] = filters.get("current_department")
		condition += """and current_department = %(current_department)s """ 

	if filters.get("next_department"):
		args["next_department"] = filters.get("next_department")
		condition += "and next_department = %(next_department)s "

	data = frappe.db.sql(f"""select name
			from `tabDepartment IR`
				where type = "Issue" and docstatus = 1 
				and name like %(txt)s {condition}
			""",args)
	return data if data else []

def get_material_wt(doc, manufacturing_operation):
	res = frappe.db.sql(f"""select ifnull(sum(if(sed.uom='cts',sed.qty*0.2, sed.qty)),0) as gross_wt, ifnull(sum(if(i.variant_of = 'M',sed.qty,0)),0) as net_wt,
        ifnull(sum(if(i.variant_of = 'D',sed.qty,0)),0) as diamond_wt, ifnull(sum(if(i.variant_of = 'D',if(sed.uom='cts',sed.qty*0.2, sed.qty),0)),0) as diamond_wt_in_gram,
        ifnull(sum(if(i.variant_of = 'G',sed.qty,0)),0) as gemstone_wt, ifnull(sum(if(i.variant_of = 'G',if(sed.uom='cts',sed.qty*0.2, sed.qty),0)),0) as gemstone_wt_in_gram,
        ifnull(sum(if(i.variant_of = 'O',sed.qty,0)),0) as other_wt
        from `tabStock Entry Detail` sed left join `tabStock Entry` se on sed.parent = se.name left join `tabItem` i on i.name = sed.item_code 
		    where se.{scrub(doc.doctype)} = "{doc.name}" and sed.manufacturing_operation = "{manufacturing_operation}" and se.docstatus = 1""", as_dict=1)
	if res:
		return res[0]
	return {}