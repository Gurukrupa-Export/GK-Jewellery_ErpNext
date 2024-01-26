import json
import frappe
import itertools
from six import itervalues
from frappe import _
from frappe.utils import flt,cint
from jewellery_erpnext.utils import get_variant_of_item, update_existing, get_item_from_attribute
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.batch.batch import get_batch_qty
from datetime import datetime

def validate(self, method):
	"""
		-> This function is iterating over all the items in the "self.items" list and assigns values to their properties
		-> Then it checks the item code, if it starts with "M" or "F" it gets the metal_purity from the Job Card 
		 		and assigns it to the row.metal_purity 
		 		and also calculates the fine_weight by multiplying gross_weight with metal_purity
		-> If the item code does not start with "M" or "F", it assigns an empty string to the row.metal_purity
		-> Then it checks if the stock_entry_type is "Manufacture" and work_order and bom_no are present, 
				then it gets the tag_no from the BOM and assigns it to the first item in the items list that is a finished_item.
	"""
	allow_zero_valuation(self)
	if self.stock_entry_type == "Manufacture" and self.work_order and self.bom_no:
		if serial_no:=frappe.db.get_value("BOM",self.get("bom_no"),"tag_no"):
			for item in self.items:
				if item.is_finished_item:
					# if not item.serial_no:
					item.serial_no = serial_no
					break

	if self.purpose == 'Material Transfer for Manufacture':
		for row in self.items:
			# Set Purity For Items
			if not row.metal_purity:
				if row.item_code.startswith("M") or row.item_code.startswith("F"):
					row.metal_purity = frappe.db.get_value('Operation Card', self.operation_card, 'purity')

		# Set BOM Via Production Order 			
		if not self.from_bom:
			if self.production_order:
				bom = frappe.db.sql(f"""
							SELECT soi.bom
							FROM `tabSales Order Item` soi
							JOIN `tabProduction Order` po ON po.sales_order_item = soi.name
							WHERE po.name = '{self.production_order}' 
						""", as_dict=True)[0].get('bom')
				self.from_bom=1
				self.bom_no = bom
	
	if self.stock_entry_type in ['Material Transfer for Manufacture', 'Broken / Loss']:
		for row in self.items:
			# Set Operation Card In Child Table
			row.operation_card = self.operation_card

	if self.purpose == "Material Transfer":
		validate_metal_properties(self)
# main slip have validation error for repack and transfer so it was commented
	# validate_main_slip_warehouse(self)

def validate_main_slip_warehouse(doc):
	for row in doc.items:
		main_slip = row.main_slip or row.to_main_slip
		if not main_slip:
			return
		warehouse = frappe.db.get_value("Main Slip", main_slip, "warehouse")
		if (row.main_slip and row.s_warehouse != warehouse) or (row.to_main_slip and row.t_warehouse != warehouse):
			frappe.throw(_(f"Selected warehouse does not belongs to main slip({main_slip})"))

def validate_metal_properties(doc):
	mwo = frappe._dict()
	if doc.manufacturing_work_order:
		mwo = frappe.db.get_value("Manufacturing Work Order", doc.manufacturing_work_order, ["metal_type", "metal_touch", "metal_purity", "metal_colour","multicolour","allowed_colours"], as_dict=1)
	for row in doc.items:
		item_template = frappe.db.get_value("Item",row.item_code, "variant_of")
		main_slip = row.main_slip or row.to_main_slip
		ms = frappe.db.get_value("Main Slip", main_slip, ["metal_type", "metal_touch", "metal_purity", "metal_colour", "check_color", "for_subcontracting","multicolour","allowed_colours"], as_dict=1)
		if main_slip and item_template != 'M':
			frappe.throw(_("Only metals are allowed in Main Slip."))
		if item_template != "M" or not (main_slip or mwo):
			continue
		attribute_det = frappe.db.get_values("Item Variant Attribute",{"parent": row.item_code, "attribute":["in",["Metal Type", "Metal Touch", "Metal Purity", "Metal Colour"]]}, ['attribute', 'attribute_value'], as_dict=1)
		item_det = { row.attribute: row.attribute_value for row in attribute_det}
		if mwo.multicolour == 0:
			if main_slip:
				if ms.get("for_subcontracting"):
					continue
				if ms.metal_touch != item_det.get("Metal Touch") or ms.metal_purity != item_det.get("Metal Purity") or (ms.metal_colour != item_det.get("Metal Colour") and ms.check_color):
					frappe.throw(f"Row #{row.idx}: Metal properties do not match with the selected main slip")
			if mwo:
				# frappe.throw(str([mwo.metal_touch != item_det.get("Metal Touch"), mwo.metal_purity != item_det.get("Metal Purity"), (mwo.metal_colour != item_det.get("Metal Colour"))]))
				if mwo.metal_touch != item_det.get("Metal Touch") or mwo.metal_purity != item_det.get("Metal Purity"):
						frappe.throw(f"Row #{row.idx}: Metal properties do not match with the selected Manufacturing Work Order")
		
		if mwo.multicolour == 1:
			if not main_slip:
				frappe.throw(f"Select Main Slip")
			if ms.multicolour == 0:
				frappe.throw(f"Select Multicolour Main Slip </br><b>Metal Properties are: (MT:{mwo.metal_type}, MTC:{mwo.metal_touch}, MP:{mwo.metal_purity}, MC:{mwo.allowed_colours})</b>")
			allowed_colors = ''.join(sorted(map(str.upper, mwo.allowed_colours)))
			colour_code = {"P": "Pink", "Y": "Yellow", "W": "White"}
			color_matched = False	 # Flag to check if at least one color matches
			for char in allowed_colors:
				if char not in colour_code:
					frappe.throw(f"Invalid color code <b>{char}</b> in MWO: <b>{row.manufacturing_work_order}</b>")
				if ms.check_color and colour_code[char] == item_det.get("Metal Colour"):
					color_matched = True	# Set the flag to True if color matches and exit loop
					break 
			# Throw an error only if no color matches
			if ms.check_color and not color_matched:
				frappe.throw(f"<b>Row #{row.idx}</b></br>Metal properties in MWO: <b>{doc.manufacturing_work_order}</b> do not match the main slip. </br><b>Metal Properties are: (MT:{mwo.metal_type}, MTC:{mwo.metal_touch}, MP:{mwo.metal_purity}, MC:{allowed_colors})</b>")


def on_cancel(self, method=None):
	update_manufacturing_operation(self, True)
	update_main_slip(self, True)

def onsubmit(self, method):
	validate_items(self)
	update_manufacturing_operation(self)
	update_main_slip(self)
	
	# update_material_request_status(self)
	# create_finished_bom(self)

def update_main_slip(doc, is_cancelled=False):
	if doc.purpose != "Material Transfer":
		return
	main_slip_map = frappe._dict()
	for entry in doc.items:
		if entry.main_slip and entry.to_main_slip:
			frappe.throw(_("Select either source or target main slip."))
		if entry.main_slip:
			metal_type = frappe.db.get_value("Main Slip", entry.main_slip, "metal_type")
			excluded_metal = frappe.db.get_value("Item Variant Attribute",{'parent': entry.item_code, "attribute": "Metal Type", "attribute_value": metal_type})
			if (not excluded_metal):
				continue
			temp = main_slip_map.get(entry.main_slip, frappe._dict())
			if entry.manufacturing_operation:
				temp["operation_receive"] = flt(temp.get("operation_receive")) + (entry.qty if not is_cancelled else -entry.qty)
			else:
				temp["receive_metal"] = flt(temp.get('receive_metal')) + (entry.qty if not is_cancelled else -entry.qty)
			main_slip_map[entry.main_slip] = temp

		elif entry.to_main_slip:
			metal_type = frappe.db.get_value("Main Slip", entry.to_main_slip, "metal_type")
			excluded_metal = frappe.db.get_value("Item Variant Attribute",{'parent': entry.item_code, "attribute": "Metal Type", "attribute_value": metal_type})
			if (not excluded_metal):
				continue
			temp = main_slip_map.get(entry.to_main_slip, frappe._dict())
			if entry.manufacturing_operation:
				temp["operation_issue"] = flt(temp.get("operation_issue")) + (entry.qty if not is_cancelled else -entry.qty)
			else:
				temp["issue_metal"] = flt(temp.get('issue_metal')) + (entry.qty if not is_cancelled else -entry.qty)
			main_slip_map[entry.to_main_slip] = temp

	for main_slip, values in main_slip_map.items():
		_values = { key: f'{key} + {value}' for key,value in values.items()}
		_values["pending_metal"] = "(issue_metal + operation_issue) - (receive_metal + operation_receive)"
		update_existing("Main Slip", main_slip, _values)


def validate_items(self):
	if self.stock_entry_type != 'Broken / Loss': return
	for i in self.items:
		if not frappe.db.exists('BOM Item', {'parent': self.bom_no, 'item_code': i.get('item_code')}):
			return frappe.throw(f"Item {i.get('item_code')} Not Present In BOM {self.bom_no}")

def allow_zero_valuation(self):
	for row in self.items:
		if row.inventory_type == "Customer Goods":
			row.allow_zero_valuation_rate = 1

def update_material_request_status(self):
	try:
		if self.purpose != "Material Transfer for Manufacture": return
		mr_doc = frappe.db.get_value('Material Request', {'docstatus':0, 'job_card': self.job_card}, 'name')
		frappe.msgprint(mr_doc)
		if mr_doc:
			mr_doc = frappe.get_doc('Material Request', {'docstatus':0, 'job_card': self.job_card}, 'name')
			mr_doc.per_ordered = 100
			mr_doc.status = "Transferred"
			mr_doc.save()
			mr_doc.submit()
	except Exception as e:
		frappe.logger('utils').exception(e)


def create_finished_bom(self):
	"""
	-> This function creates a Finieshed Goods BOM based on the items in a stock entry
	-> It separates the items into manufactured items, raw materials and scrap items
	-> Subtracts the scrap quantity from the raw materials quantity
	-> Sets the properties of the BOM document before saving it, 
			and retrieves properties from the Work Order BOM and assigns them to the newly created BOM
	"""
	if self.stock_entry_type != 'Manufacture': return
	bom_doc = frappe.new_doc('BOM')
	items_to_manufacture = []
	raw_materials = []
	scrap_item = []
	# Seperate Items Into Items To Manufacture, Raw Materials and Scrap Items
	for item in self.items:
		if not item.s_warehouse and item.t_warehouse:
			variant_of = frappe.db.get_value('Item', item.item_code, 'variant_of')
			if not variant_of and item.item_code not in ['METAL LOSS' , 'FINDING LOSS']:
				items_to_manufacture.append(item.item_code)
			else:
				scrap_item.append({'item_code':item.item_code, 'qty': item.qty}) 
		else:
			raw_materials.append({'item_code':item.item_code, 'qty': item.qty})

	# Subtract Scrap Quantity from actual quantity
	for scrap, rm in itertools.product(scrap_item, raw_materials):
		variant_of = get_variant_of_item(rm.get('item_code'))
		if scrap.get('item_code') == rm.get('item_code'):
			rm['qty'] = rm['qty'] - scrap['qty']

	bom_doc.item = items_to_manufacture[0]
	for raw_item in raw_materials:
		qty = raw_item.get('qty') or 1
		diamond_quality =frappe.db.get_value('BOM Diamond Detail', {'parent': self.bom_no}, 'quality')
		# Set all the items into respective Child Tables For BOM rate Calculation
		updated_bom = set_item_details(raw_item.get('item_code'), bom_doc,qty, diamond_quality)
	updated_bom.customer = frappe.db.get_value('BOM', self.bom_no, 'customer')
	updated_bom.gold_rate_with_gst = frappe.db.get_value('BOM', self.bom_no, 'gold_rate_with_gst')
	updated_bom.is_default = 0
	updated_bom.tag_no = frappe.db.get_value('BOM', self.bom_no, 'tag_no')
	updated_bom.bom_type = 'Finished Goods'
	updated_bom.reference_doctype = 'Work Order'
	updated_bom.save(ignore_permissions = True)


def set_item_details(item_code, bom_doc, qty, diamond_quality):
	"""
		-> This function takes in an item_code, a bom_doc, a quantity and diamond_quality as its inputs,
		-> It then adds the item attributes and details in the corresponding child table of BOM document.
		-> It returns the updated BOM document.
	"""
	variant_of = get_variant_of_item(item_code)
	item_doc = frappe.get_doc('Item', item_code)
	attr_dict = {'item_variant': item_code, 'quantity':qty}
	for attr in item_doc.attributes:
		attr_doc = frappe.as_json(attr)
		attr_doc = json.loads(attr_doc)
		for key, val in attr_doc.items():
			if key == 'attribute':
				attr_dict[attr_doc[key].replace(" ","_").lower()] = attr_doc["attribute_value"]
	# Determine child table name based on variant
	child_table_name = ''
	if variant_of == 'M': child_table_name = 'metal_detail'
	elif variant_of == 'D': 
		child_table_name = 'diamond_detail'
		weight_per_pcs = frappe.db.get_value('Attribute Value', attr_dict.get('diamond_sieve_size'), 'weight_in_cts')
		attr_dict['weight_per_pcs'] = weight_per_pcs
		attr_dict["quality"] = diamond_quality
		attr_dict['pcs'] = qty / weight_per_pcs
	elif variant_of == 'G': child_table_name = 'gemstone_detail'
	elif variant_of == 'F': child_table_name = 'finding_detail'
	else: return
	bom_doc.append(child_table_name,attr_dict)
	return bom_doc


def get_scrap_items_from_job_card(self):
	if not self.pro_doc:
		self.set_work_order_details()

	scrap_items = frappe.db.sql('''
		SELECT
			JCSI.item_code, JCSI.item_name, SUM(JCSI.stock_qty) as stock_qty, JCSI.stock_uom, JCSI.description, JC.wip_warehouse 
		FROM
			`tabJob Card` JC, `tabJob Card Scrap Item` JCSI
		WHERE
			JCSI.parent = JC.name AND JC.docstatus = 1
			AND JCSI.item_code IS NOT NULL AND JC.work_order = %s
		GROUP BY
			JCSI.item_code
	''', self.work_order, as_dict=1) # custom change in query JC.wip_warehouse 

	pending_qty = flt(self.pro_doc.qty) - flt(self.pro_doc.produced_qty)
	if pending_qty <=0:
		return []

	used_scrap_items = self.get_used_scrap_items()
	for row in scrap_items:
		row.stock_qty -= flt(used_scrap_items.get(row.item_code))
		row.stock_qty = (row.stock_qty) * flt(self.fg_completed_qty) / flt(pending_qty)

		if used_scrap_items.get(row.item_code):
			used_scrap_items[row.item_code] -= row.stock_qty

		if cint(frappe.get_cached_value('UOM', row.stock_uom, 'must_be_whole_number')):
			row.stock_qty = frappe.utils.ceil(row.stock_qty)

	return scrap_items

def get_bom_scrap_material(self, qty):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(self.bom_no, self.company, qty=qty,
			fetch_exploded = 0, fetch_scrap_items = 1) or {}

		for item in itervalues(item_dict):
			item.from_warehouse = ""
			item.is_scrap_item = 1

		for row in self.get_scrap_items_from_job_card():
			if row.stock_qty <= 0:
				continue

			item_row = item_dict.get(row.item_code)
			if not item_row:
				item_row = frappe._dict({})

			item_row.update({
				'uom': row.stock_uom,
				'from_warehouse': '',
				'qty': row.stock_qty + flt(item_row.stock_qty),
				'converison_factor': 1,
				'is_scrap_item': 1,
				'item_name': row.item_name,
				'description': row.description,
				'allow_zero_valuation_rate': 1,
				'to_warehouse': row.wip_warehouse # custom change
			})

			item_dict[row.item_code] = item_row

		return item_dict


def update_manufacturing_operation(doc, is_cancelled=False):
	if isinstance(doc, str):
		doc = frappe.get_doc("Stock Entry",doc)
	if doc.purpose not in ["Material Transfer", "Material Receipt"] or doc.auto_created:
		return
	item_wt_map = frappe._dict()
	field_map = {
		'F': "finding_wt",
		'G': "gemstone_wt",
		'D': "diamond_wt",
		'M': "net_wt",
		'O': "other_wt"
	}
	for entry in doc.items:
		if not entry.manufacturing_operation:
			continue
		variant_of = frappe.db.get_value("Item",entry.item_code, "variant_of")
		fieldname = field_map.get(variant_of, "other_wt")
		wt = item_wt_map.setdefault(entry.manufacturing_operation, frappe._dict())
		qty = entry.qty if not is_cancelled else -entry.qty
		weight_in_gram = flt(wt.get(fieldname)) + qty*0.2 if entry.uom == "cts" else qty
		weight_in_cts = flt(wt.get(fieldname)) + qty
		wt[fieldname] = weight_in_cts
		if variant_of == 'D':
			wt["diamond_wt_in_gram"] = weight_in_gram
		elif variant_of == 'G':
			wt["gemstone_wt_in_gram"] = weight_in_gram
		wt['gross_wt'] = weight_in_gram
		item_wt_map[entry.manufacturing_operation] = wt

	for manufacturing_operation, values in item_wt_map.items():
		_values = { key: f'{key} + {value}' for key,value in values.items() if key != "finding_wt"}
		update_existing("Manufacturing Operation", manufacturing_operation, _values)


@frappe.whitelist()
def make_stock_in_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		if target.stock_entry_type == "Customer Goods Received":
			target.stock_entry_type = "Customer Goods Issue"
			target.purpose = "Material Issue"
			target.custom_cg_issue_against = source.name
		elif target.stock_entry_type == "Customer Goods Issue":
			target.stock_entry_type = "Customer Goods Received"
			target.purpose = "Material Receipt"
		elif source.stock_entry_type == "Customer Goods Transfer":
			target.stock_entry_type = "Customer Goods Transfer"
			target.purpose = "Material Transfer"
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.t_warehouse = ""
		# getting target warehouse on end transit
		target_wh = ""
		if source_parent.custom_material_request_reference:
			ref_mr = frappe.get_doc("Material Request", source_parent.custom_material_request_reference)
			for wh in ref_mr.items:
				if wh.item_code == source_doc.item_code:
					target_wh = wh.warehouse
			target_doc.t_warehouse = target_wh


		target_doc.s_warehouse = source_doc.t_warehouse
		target_doc.qty = source_doc.qty

	doclist = get_mapped_doc(
		"Stock Entry",
		source_name,
		{
			"Stock Entry": {
				"doctype": "Stock Entry",
				"field_map": {"name": "outgoing_stock_entry"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Stock Entry Detail": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "ste_detail",
					"parent": "against_stock_entry",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
				},
				"postprocess": update_item,
				# "condition": lambda doc: flt(doc.qty) - flt(doc.transferred_qty) > 0.01,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


def convert_metal_purity(from_item: dict, to_item: dict, s_warehouse, t_warehouse):
	f_item = get_item_from_attribute(from_item.metal_type, from_item.metal_touch, from_item.metal_purity, from_item.metal_colour)
	t_item = get_item_from_attribute(to_item.metal_type, to_item.metal_touch, to_item.metal_purity, to_item.metal_colour)
	doc = frappe.new_doc("Stock Entry")
	doc.stock_entry_type = "Repack"
	doc.purpose = "Repack"
	doc.inventory_type = "Regular Stock"
	doc.auto_created = True
	doc.append("items", {
		"item_code": f_item,
		"s_warehouse": s_warehouse,
		"t_warehouse": None,
		"qty": from_item.qty,
		"inventory_type": "Regular Stock"
	})
	doc.append("items", {
		"item_code": t_item,
		"s_warehouse": None,
		"t_warehouse": t_warehouse,
		"qty": to_item.qty,
		"inventory_type": "Regular Stock"
	})
	doc.save()
	doc.submit()


@frappe.whitelist()
def make_mr_on_return(source_name, target_doc=None):
	def set_missing_values(source, target):
		itm_batch = []
		dict = {}
		for i in source.items:
			dict.update({"item": i.item_code, "batch": i.batch_no, "serial": i.serial_no, "idx": i.idx})
			itm_batch.append(dict)

		for itm in target.items:
			for b in itm_batch:
				if itm.item_code == b.get("item") and itm.idx == b.get("idx"):
					itm.custom_batch_no = b.get("batch")
					itm.custom_serial_no = b.get("serial")

		if source.stock_entry_type == "Customer Goods Transfer":
			target.material_request_type = "Material Transfer"
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.from_warehouse = source_doc.t_warehouse
		target_wh = ""
		if source_parent.outgoing_stock_entry:
			ref_se = frappe.get_doc("Stock Entry", source_parent.outgoing_stock_entry)
			for wh in ref_se.items:
				if wh.item_code == source_doc.item_code:
					target_wh = wh.s_warehouse

		timestamp_obj = datetime.strptime(str(source_doc.creation), '%Y-%m-%d %H:%M:%S.%f')

		date = timestamp_obj.strftime('%Y-%m-%d')
		time = timestamp_obj.strftime('%H:%M:%S.%f')

		wh_qty = get_batch_qty(batch_no=source_doc.batch_no, warehouse=source_doc.t_warehouse, item_code=source_doc.item_code, posting_date=date, posting_time=time)
		
		target_doc.warehouse = target_wh
		target_doc.qty = wh_qty
	
	doclist = get_mapped_doc(
		"Stock Entry",
		source_name,
		{
			"Stock Entry": {
				"doctype": "Material Request",
			},
			"Stock Entry Detail": {
				"doctype": "Material Request Item",
				"field_map": {
					"custom_serial_no": "serial_no",
					"custom_batch_no": "batch_no",
				},
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist

""" 
create_material_receipt_for_sales_person function  
creates a return receipt for items issued. i.e. Stock Enty to Stock Entry.
"""

@frappe.whitelist()
def create_material_receipt_for_sales_person(source_name):
	source_doctype = 'Stock Entry'
	target_doctype = 'Stock Entry'
	source_doc = frappe.get_doc("Stock Entry", source_name)
	target_doc = frappe.new_doc(source_doctype)
	target_doc.update(source_doc.as_dict())
	material_receipts_sql = f"""SELECT se.name, si.item_code, sum(si.qty) as quantity
                            FROM `tabStock Entry` as se
                            LEFT JOIN `tabStock Entry Detail` as si
                            ON si.parent = se.name
                            WHERE se.custom_material_return_receipt_number = '{source_doc.name}'
                            GROUP BY se.name, si.item_code
                         """
	material_receipts = frappe.db.sql(material_receipts_sql, as_dict=True)
	item_qty_material_receipt = {}
	for row in material_receipts:
		if row.item_code not in item_qty_material_receipt:
			item_qty_material_receipt[row.item_code] = row.quantity
		else:
			item_qty_material_receipt[row.item_code] += row.quantity
	
	target_doc.stock_entry_type = "Material Receipt - Sales Person"
	target_doc.docstatus = 0
	target_doc.posting_date = frappe.utils.nowdate()
	target_doc.posting_time = frappe.utils.nowtime()
	items_quantity_ca= frappe.db.sql(f"""SELECT soic.item_code, sum(soic.quantity)
                                        FROM `tabCustomer Approval` as ca
                                        LEFT JOIN `tabSales Order Item Child` as soic
                                        ON soic.parent = ca.name
                                        WHERE ca.stock_entry_reference LIKE '{source_name}'
                                        GROUP BY soic.item_code
                                     """, as_dict=True)
	items_quantity_ca = {item['item_code']: flt(item['sum(soic.quantity)']) for item in items_quantity_ca}
	items_quantity = item_qty_material_receipt.copy()
	for item_code in items_quantity_ca:
		if item_code in items_quantity:
			items_quantity[item_code]+=items_quantity_ca[item_code]
		else:
			items_quantity[item_code]=items_quantity_ca[item_code]
	
	filtered_items = []
	for item in target_doc.items:
		if item.item_code not in items_quantity:
			filtered_items.append(item)
		elif item.item_code in items_quantity:
			if item.qty != items_quantity[item.item_code]:
				item.qty -= items_quantity[item.item_code]
				filtered_items.append(item)
	
	serial_and_batch_items = {}
	for item in source_doc.items:
		serial_and_batch_items[item.item_code] = [item.serial_no, item.batch_no]
	target_doc.items = filtered_items
	target_doc.stock_entry_type = "Material Receipt - Sales Person"
	target_doc.custom_material_return_receipt_number = source_doc.name
	for item in target_doc.items:
		if item.item_code in serial_and_batch_items:
			item.serial_no = serial_and_batch_items[item.item_code][0]
			item.batch_no = serial_and_batch_items[item.item_code][1]
		item.s_warehouse, item.t_warehouse = item.t_warehouse, item.s_warehouse
	target_doc.insert()
	total_return_receipt_for_issue={}

	return target_doc

"""
create_material_receipt_for_customer_approval function 
creates a return receipt for items issued. i.e. Customer Approval to Stock Entry.
"""
@frappe.whitelist()
def create_material_receipt_for_customer_approval(source_name, cust_name):
    items_quantity_ca = frappe.db.sql(f"""
        SELECT soic.item_code, sum(soic.quantity) as total_quantity, soic.serial_no
        FROM `tabCustomer Approval` as ca
        LEFT JOIN `tabSales Order Item Child` as soic ON soic.parent = ca.name
        WHERE ca.stock_entry_reference LIKE '{source_name}' AND ca.name='{cust_name}'
        GROUP BY soic.item_code, soic.serial_no
    """, as_dict=True)

    item_qty = {item['item_code']: {'total_quantity': item['total_quantity'], 'serial_no': item['serial_no']} for item in items_quantity_ca}

    target_doc = frappe.new_doc("Stock Entry")
    target_doc.update(frappe.get_doc("Stock Entry", source_name).as_dict())
    target_doc.docstatus = 0

    target_doc.items = []
    for item in frappe.get_all("Stock Entry Detail", filters={'parent': source_name}, fields=['*']):
        se_item = frappe.new_doc("Stock Entry Detail")
        se_item.update(item)
        se_item.qty = item_qty.get(item.item_code, {}).get('total_quantity', 0)
        se_item.serial_no = item_qty.get(item.item_code, {}).get('serial_no', '')
        target_doc.append('items', se_item)

    target_doc.stock_entry_type = "Material Receipt - Sales Person"
    target_doc.custom_material_return_receipt_number = source_name
    target_doc.custom_customer_approval_reference = cust_name

    for item in target_doc.items:
        item.s_warehouse, item.t_warehouse = item.t_warehouse, item.s_warehouse

    target_doc.insert()
    return target_doc.name


"""
create_material_receipt_for_customer_approval 
validates serial items entered are equal to quantity or not if not appropriate errors received

"""

@frappe.whitelist()
def make_stock_in_entry_on_transit_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.stock_entry_type = source.stock_entry_type
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.t_warehouse = ""

		if source_doc.material_request_item and source_doc.material_request:
			add_to_transit = frappe.db.get_value("Stock Entry", source_name, "add_to_transit")
			if add_to_transit:
				warehouse = frappe.get_value(
					"Material Request Item", source_doc.material_request_item, "warehouse"
				)
				target_doc.t_warehouse = warehouse

		target_doc.s_warehouse = source_doc.t_warehouse
		target_doc.qty = source_doc.qty - source_doc.transferred_qty

	doclist = get_mapped_doc(
		"Stock Entry",
		source_name,
		{
			"Stock Entry": {
				"doctype": "Stock Entry",
				"field_map": {"name": "outgoing_stock_entry"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Stock Entry Detail": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "ste_detail",
					"parent": "against_stock_entry",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
				},
				"postprocess": update_item,
				"condition": lambda doc: flt(doc.qty) - flt(doc.transferred_qty) > 0.01,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist

@frappe.whitelist()
def validation_of_serial_item(issue_doc):
    doc=frappe.get_doc("Stock Entry",issue_doc)
    serial_item={}
    for item in doc.items:
        check_serial_no = frappe.db.get_list('Item', filters={'item_code': item.item_code},fields=['has_serial_no'])
        if check_serial_no[0]['has_serial_no']==1:
            serial_item[item.item_code]=item.serial_no.split('\n')
    return serial_item

@frappe.whitelist()
def set_filter_for_main_slip(doctype, txt, searchfield, start, page_len, filters):
	mnf = filters.get('mnf')
	metal_purity = frappe.db.get_value('Manufacturing Work Order', { mnf }, 'metal_purity')
	# frappe.throw(str(metal_purity))
	return metal_purity