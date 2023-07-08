# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint
import json
from jewellery_erpnext.utils import update_existing
from jewellery_erpnext.jewellery_erpnext.doctype.parent_manufacturing_order.parent_manufacturing_order import make_manufacturing_order

class ManufacturingPlan(Document):
	def on_submit(self):
		for row in self.manufacturing_plan_table:
			update_existing("Sales Order Item",row.docname, "manufacturing_order_qty", f"manufacturing_order_qty + {row.manufacturing_order_qty}")
			create_manufacturing_order(self, row)

	def on_cancel(self):
		for row in self.manufacturing_plan_table:
			update_existing("Sales Order Item", row.docname, "manufacturing_order_qty", f"greatest(manufacturing_order_qty - {row.manufacturing_order_qty},0)")

	def validate(self):
		total = 0
		for row in self.manufacturing_plan_table:
			total += cint(row.manufacturing_order_qty)
			if row.qty_per_manufacturing_order == 0:
				frappe.throw(_("Qty per Manufacturing Order cannot be Zero"))
			if row.manufacturing_order_qty % row.qty_per_manufacturing_order != 0:
				frappe.throw(_(f"Row #{row.idx}: `Manufacturing Order Qty` / `Qty per Manufacturing Order` must be a whole number"))
		self.total_planned_qty = total

	@frappe.whitelist()
	def get_sales_orders(self):
		data = frappe.db.sql("""select so.name
			from `tabSales Order` so left join `tabSales Order Item` soi on (soi.parenttype = 'Sales Order' and soi.parent = so.name)
			where soi.qty > soi.manufacturing_order_qty  and so.docstatus = 1.0 group by so.name
			order by so.modified DESC""", as_dict=1)
		self.sales_order = []
		for row in data:
			self.append("sales_order",{
				"sales_order": row.name
			})

	@frappe.whitelist()
	def get_items_for_production(self):
		sales_orders = [row.sales_order for row in self.sales_order]
		items = frappe.db.sql(f"""select soi.name as docname, soi.parent as sales_order, soi.item_code, itm.mould as mould_no,
		 			(soi.qty - soi.manufacturing_order_qty) as pending_qty
					from `tabSales Order Item` soi left join `tabItem` itm on soi.item_code = itm.name
					where soi.parent in ('{"', '".join(sales_orders)}') and soi.qty > soi.manufacturing_order_qty""", as_dict=1)
		self.manufacturing_plan_table = []
		for item_row in items:
			item_row['manufacturing_order_qty'] = item_row.get("pending_qty")
			item_row['qty_per_manufacturing_order'] = 1
			self.append("manufacturing_plan_table", item_row)

def create_manufacturing_order(doc, row):
	cnt = int(row.manufacturing_order_qty / row.qty_per_manufacturing_order)
	for i in range(0,cnt):
		make_manufacturing_order(doc, row)
	frappe.msgprint("Parent Manufacturing Order Created")

@frappe.whitelist()
def get_sales_order(source_name, target_doc=None):
	if not target_doc:
		target_doc = frappe.new_doc("Manufacturing Plan")
	elif isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))
	if not target_doc.get("sales_order",{"sales_order":source_name}):
		target_doc.append("sales_order",{"sales_order":source_name, "customer": frappe.db.get_value("Sales Order", source_name, "customer")})
	return target_doc

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_pending_ppo_sales_order(doctype, txt, searchfield, start, page_len, filters):
	conditions = " and soi.qty > soi.manufacturing_order_qty"
	if txt:
		conditions += " and so.name like '%%" + txt + "%%' "
	if customer:=filters.get("customer"):
		conditions += f" and so.customer = '{customer}'"
	if company:=filters.get("company"):
		conditions += f" and so.company = '{company}'"
	if branch:=filters.get("branch"):
		conditions += f" and so.branch = '{branch}'"
	if txn_date:=filters.get("transaction_date"):
		conditions += f" and so.transaction_date = '{txn_date}'"
	so_data = frappe.db.sql(
		f"""
		select
			distinct so.name, so.transaction_date,
			so.company, so.customer
		from
			`tabSales Order` so, `tabSales Order Item` soi
		where
			so.name = soi.parent
			and so.docstatus = 1
			{conditions}
		order by so.transaction_date Desc
		limit %(page_len)s offset %(start)s """,
		{
			"page_len": page_len,
			"start": start,
		},
		as_dict=1
	)

	return so_data