# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now, time_diff, get_timedelta
from frappe.model.document import Document
from jewellery_erpnext.utils import set_values_in_bulk

class ManufacturingOperation(Document):
	def validate(self):
		self.set_start_finish_time()
		self.update_weights()
		self.validate_loss()

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
			self.time_taken = get_timedelta(time_diff(self.finish_time, self.start_time))
	
	@frappe.whitelist()
	def create_fg(self):
		create_manufacturing_entry(self)
		pmo = frappe.db.get_value("Manufacturing Work Order", self.manufacturing_work_order, "manufacturing_order")
		wo = frappe.get_all("Manufacturing Work Order", {"manufacturing_order": pmo}, pluck="name")
		set_values_in_bulk("Manufacturing Work Order", wo, {"status": "Completed"})
		create_finished_goods_bom(self)

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

		total_qty = sum(item['qty'] for item in data)

		return frappe.render_template("jewellery_erpnext/jewellery_erpnext/doctype/manufacturing_operation/stock_entry_details.html", {"data":data,"total_qty":total_qty})

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
	if doc.for_subcontracting and doc.subcontractor:
		wh = frappe.db.get_value("Warehouse", {"subcontractor": doc.subcontractor}, "name")
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
	total_loss = 0
	for row in data:
		existing = items.get(row.item_code)
		if existing:
			qty = existing.get("qty",0) + row.qty
		else:
			qty = row.qty
		total_loss += (row.qty*0.2 if row.uom == "cts" else row.qty)
		items[row.item_code] = {"qty": qty, "uom": row.uom}
	items["total_loss"] = total_loss
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

def create_finished_goods_bom(self):
		data = get_stock_entry_data(self)

		new_bom = frappe.copy_doc(frappe.get_doc("BOM",self.design_id_bom))
		new_bom.bom_type = "Finished Goods"
		new_bom.metal_detail = []
		new_bom.finding_detail = []
		new_bom.diamond_detail = []
		new_bom.gemstone_detail = []
		new_bom.other_detail = []
		# new_bom.items = []

		for item in data:
			item_row  = frappe.get_doc('Item',item['item_code'])

			if item_row.variant_of == 'M':
				row = {}
				for attribute in item_row.attributes:
					atrribute_name = format_attrbute_name(attribute.attribute)
					row[atrribute_name] = attribute.attribute_value
					row['quantity'] = item['qty']
				new_bom.append('metal_detail',row)

			elif item_row.variant_of == 'F':
				row = {}
				for attribute in item_row.attributes:
					atrribute_name = format_attrbute_name(attribute.attribute)
					row[atrribute_name] = attribute.attribute_value
					row['quantity'] = item['qty']
				new_bom.append('finding_detail',row)

			elif item_row.variant_of == 'D':
				row = {}
				for attribute in item_row.attributes:
					atrribute_name = format_attrbute_name(attribute.attribute)
					row[atrribute_name] = attribute.attribute_value
					row['quantity'] = item['qty']
				new_bom.append('diamond_detail',row)

			elif item_row.variant_of == 'G':
				row = {}
				for attribute in item_row.attributes:
					atrribute_name = format_attrbute_name(attribute.attribute)
					row[atrribute_name] = attribute.attribute_value
					row['quantity'] = item['qty']
				new_bom.append('gemstone_detail',row)

			elif item_row.variant_of == 'O':
				row = {}
				for attribute in item_row.attributes:
					atrribute_name = format_attrbute_name(attribute.attribute)
					row[atrribute_name] = attribute.attribute_value
					row['quantity'] = item['qty']
				new_bom.append('other_detail',row)

		new_bom.insert(ignore_mandatory = True)

def get_stock_entry_data(self):
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
	
	return data

def format_attrbute_name(input_string):
    # Replace spaces with underscores and convert to lowercase
    formatted_string = input_string.replace(" ", "_").lower()
    return formatted_string