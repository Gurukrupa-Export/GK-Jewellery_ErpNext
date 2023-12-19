# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint
from frappe.model.mapper import get_mapped_doc

class ProductCertification(Document):
	def validate(self):
		if self.department and not frappe.db.exists("Warehouse",{"department": self.department}):
			frappe.throw("Please set warehouse for selected Department")
			
		if self.supplier and not frappe.db.exists("Warehouse",{"subcontractor": self.supplier}):
			frappe.throw("Please set warehouse for selected supplier")

		self.validate_items()
		self.update_bom()
		self.get_exploded_table()
		self.distribute_amount()

	def validate_items(self):
		if self.type == "Issue":
			return
		for row in self.product_details:
			if not frappe.db.get_value("Product Details", {"parent": self.receive_against, "serial_no": row.serial_no, "item_code": row.item_code, "manufacturing_work_order": row.manufacturing_work_order}):
				frappe.throw(_(f"Row #{row.idx}: item not found in {self.receive_against}"))

	def update_bom(self):
		for row in self.product_details:
			if not (row.serial_no or row.manufacturing_work_order):
				frappe.throw(_(f"Row #{row.idx}: Either select serial no or manufacturing work order"))
			if row.bom:
				continue
			if row.serial_no:
				row.bom = frappe.db.get_value("BOM", {"tag_no": row.serial_no}, "name")
			if not row.bom:
				row.bom = frappe.db.get_value("Item", row.item_code, "master_bom")
			if not row.bom:
				frappe.throw(_(f"Row #{row.idx}: BOM not found for item or serial no"))

	def distribute_amount(self):
		if not self.product_details:
			return
		length = len(self.product_details)
		if self.type == "Issue":
			self.total_amount = 0
		amt = self.total_amount/length
		for row in self.product_details:
			row.amount = amt

	def on_submit(self):
		create_stock_entry(self)
		self.update_huid()
	
	def update_huid(self):
		for row in self.exploded_product_details:
			if row.serial_no:
				add_to_serial_no(row.serial_no, self, row)
			elif row.manufacturing_work_order:
				frappe.set_value("Manufacturing Work Order", row.manufacturing_work_order, "huid", row.huid)

	def get_exploded_table(self):
		cat_det = frappe.get_all("Certification Settings", {"parent": "Jewellery Settings"}, ["category", "count"])
		custom_cat = {row.category:row.count for row in cat_det}
		# self.exploded_product_details = []
		metal_det = None
		for row in self.product_details:
			metal_touch = ""
			metal_colour = frappe.db.get_value("BOM", row.bom, "metal_colour")
			count = 1
			if row.manufacturing_work_order:
				mwo = frappe.db.get_value("Manufacturing Work Order", row.manufacturing_work_order, ["department","qty", "metal_touch", "metal_colour"], as_dict=1)
				if self.department != mwo.department:
					frappe.throw(_(f"Manufacturing Work Order should be in '{self.department}' department"))
				count *= cint(mwo.get("qty"))
				metal_touch = mwo.get("metal_touch")
				metal_colour = mwo.get("metal_colour")
			else:
				metal_det = frappe.db.sql(f"""SELECT DISTINCT metal_touch FROM `tabBOM Metal Detail`
									 where parent = '{row.bom}'""", as_dict=1)
				count *= cint(len(metal_det))

			if row.category in custom_cat:
				count *= custom_cat.get(row.category, 1)
			
			existing = self.get("exploded_product_details", {"item_code": row.item_code, "serial_no": row.serial_no, "manufacturing_work_order": row.manufacturing_work_order})
			if existing and len(existing) == count:
				continue
			for i in range(0, count):
				if metal_det:
					metal_touch = metal_det[i].get("metal_touch")
				if existing and metal_touch in [a.get('metal_touch') for a in existing]:
					continue
				self.append("exploded_product_details", {
					'item_code': row.item_code,
					"serial_no": row.serial_no,
					"bom": row.bom,
					"manufacturing_work_order": row.manufacturing_work_order,
					"supply_raw_material": bool(row.manufacturing_work_order),
					"metal_touch": metal_touch,
					"metal_colour": metal_colour,
					"category": row.category,
					"sub_category": row.sub_category
				})

def create_stock_entry(doc):
	se_doc = frappe.new_doc("Stock Entry")
	se_doc.stock_entry_type = get_stock_entry_type(doc.service_type, doc.type)
	se_doc.company = doc.company
	se_doc.product_certification = doc.name
	s_warehouse = frappe.db.exists("Warehouse",{"department": doc.department})
	t_warehouse = frappe.db.exists("Warehouse",{"subcontractor": doc.supplier})
	added_mwo = []
	added_serial = []
	for row in doc.exploded_product_details:
		if row.supply_raw_material and row.manufacturing_work_order not in added_mwo:
			get_stock_item_against_mwo(se_doc, doc, row, s_warehouse, t_warehouse)
			added_mwo.append(row.manufacturing_work_order)
		else:
			if row.serial_no in added_serial:
				continue
			added_serial.append(row.serial_no)
			se_doc.append("items", {
				"item_code": row.item_code,
				"serial_no": row.serial_no,
				"qty": 1,
				"s_warehouse": s_warehouse if doc.type == "Issue" else t_warehouse,
				"t_warehouse": t_warehouse if doc.type == "Issue" else s_warehouse,
				"Inventory_type": "Regular Stock",
				"reference_doctype": "Serial No",
				"reference_docname": row.serial_no
			})
	se_doc.inventory_type = "Regular Stock"
	se_doc.save()
	se_doc.submit()
	frappe.msgprint("Stock Entry created")

def get_stock_entry_type(txn_type, purpose):
	if purpose == "Issue":
		if txn_type == "Hall Marking Service":
			return "Material Issue for Hallmarking"
		else:
			return "Material Issue for Certification"
	else:
		if txn_type == "Hall Marking Service":
			return "Material Receipt for Hallmarking"
		else:
			return "Material Receipt for Certification"

def get_stock_item_against_mwo(se_doc, doc, row, s_warehouse, t_warehouse):
	if doc.type == "Issue":	
		target_wh = frappe.get_value("Warehouse", {"department": doc.department}, "name")
		filters = [
			["Stock Entry", "manufacturing_work_order", "=", row.manufacturing_work_order],
			["Stock Entry", "manufacturing_operation", "is", "set"],
			["Stock Entry Detail", "t_warehouse", "=", target_wh],
			["Stock Entry Detail", "employee", "is", "not set"],
		]
	else:
		filters = [
			["Stock Entry", "product_certification", "=", doc.receive_against],
			["Stock Entry Detail", "reference_docname", "=", row.manufacturing_work_order],
			["Stock Entry Detail", "reference_doctype", "=", "Manufacturing Work Order"],
		]
	stock_entries = frappe.get_all("Stock Entry", filters=filters, fields=["`tabStock Entry Detail`.item_code", "`tabStock Entry Detail`.qty"], join="right join")
	if len(stock_entries) < 1:		
		frappe.msgprint(f'No Stock entry Found against the Manufacturing Work Order: <strong> {row.manufacturing_work_order}</strong>')
	
	for item in stock_entries:
		se_doc.append("items", {
			"item_code": item.item_code,
			"qty": item.qty,
			"s_warehouse": s_warehouse if doc.type == "Issue" else t_warehouse,
			"t_warehouse": t_warehouse if doc.type == "Issue" else s_warehouse,
			"Inventory_type": "Regular Stock",
			"reference_doctype": "Manufacturing Work Order",
			"reference_docname": row.manufacturing_work_order
		})

@frappe.whitelist()
def create_product_certification_receive(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.type = "Receive"

	doc = get_mapped_doc(
		"Product Certification",
		source_name,
		{
			"Product Certification": {
				"doctype": "Product Certification",
				"field_map": {"name": "receive_against"},
				"field_no_map": ["date"]
			},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=True,
	)

	return doc

def add_to_serial_no(serial_no, doc, row):
	serial_doc = frappe.get_doc("Serial No", serial_no)
	serial_doc.append("huid", {
		"huid": row.huid,
		"date": doc.date
	})
	serial_doc.save()