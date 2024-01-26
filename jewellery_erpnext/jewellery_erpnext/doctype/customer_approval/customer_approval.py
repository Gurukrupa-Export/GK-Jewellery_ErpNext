# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CustomerApproval(Document):
    def before_save(self):
        stock_entry_reference = self.stock_entry_reference
        quantity = quantity_calculation(stock_entry_reference)
        for item in self.items:
            for qty in quantity:
                if qty[0] == item.item_code:
                    if qty[1] < item.quantity:
                        frappe.throw('Error: Quantity cannot be greater than the remaining quantity.')
        
            serial_item = []
            if item.serial_no:
                serial_item.extend(item.serial_no.split('\n'))

            if len(serial_item) > item.quantity:
                frappe.throw("Error: Please remove serial no")

            elif len(serial_item) < item.quantity:
                frappe.throw("Error: There are less serial no. Please add")

@frappe.whitelist()
def get_stock_entry_data(stock_entry_reference):
    doc = frappe.get_doc("Stock Entry", stock_entry_reference)
    
    quantities = dict(quantity_calculation(stock_entry_reference))
    serial_numbers = serial_no_filter(stock_entry_reference)

    for item in doc.items:
        item_code = item.item_code
        if item_code in quantities:
            item.qty = quantities[item_code]
            for serial_no in serial_numbers:
                if item_code == serial_no['item_code']:
                    item.serial_no = serial_no['serial_no']
                    break
        else:
            item.qty = 0
    return {"items":doc.items, "supporting_staff":doc.custom_supporting_staff}

@frappe.whitelist()
def get_items_filter(doctype, txt, searchfield, start, page_len, filters):
    stock_entry_reference = filters['stock_entry_reference']
    result = quantity_calculation(stock_entry_reference)
    return result

@frappe.whitelist()
def quantity_calculation(stock_entry_reference):
    issue_item = frappe.db.sql(f"""SELECT sed.item_code, sed.qty
                                FROM `tabStock Entry Detail` as sed
                                LEFT JOIN `tabStock Entry` as se
                                ON sed.parent = se.name
                                WHERE se.name LIKE '{stock_entry_reference}'
    """, as_dict=True)
    
    issue_item = [{'item_code': entry['item_code'], 
                      'quantity': entry.get('quantity', entry.get('qty'))} for entry in issue_item]
   
    returned_item = frappe.db.sql(f"""SELECT sed.item_code, sed.qty
                                    FROM `tabStock Entry Detail` as sed
                                    LEFT JOIN `tabStock Entry` as se
                                    ON sed.parent = se.name
                                    WHERE se.custom_material_return_receipt_number LIKE '{stock_entry_reference}'
                                        AND se.custom_customer_approval_reference IS NULL
    """, as_dict=True)
    
    returned_item = [{'item_code': entry['item_code'], 
                      'quantity': entry.get('quantity', entry.get('qty'))} for entry in returned_item]
    
    customer_approved_item = frappe.db.sql(f"""SELECT soic.item_code, soic.quantity
                                    FROM `tabSales Order Item Child` as soic
                                    LEFT JOIN `tabCustomer Approval` as ca
                                    ON soic.parent = ca.name
                                    WHERE ca.stock_entry_reference LIKE '{stock_entry_reference}'
    """, as_dict=True)
    
    total_item_occupied = returned_item + customer_approved_item
    
    summed_quantities = {}
    for entry in total_item_occupied:
        item_code = entry['item_code']
        quantity = entry['quantity']
        summed_quantities.setdefault(item_code, 0)
        summed_quantities[item_code] += quantity
    
    total_quantity_dict = {item['item_code']: item['quantity'] for item in issue_item}
    
    for item in total_item_occupied:
        item_code = item['item_code']
        if item_code in total_quantity_dict:
            total_quantity_dict[item_code] -= item['quantity']
        
    result = [[item_code, quantity] for item_code, quantity in total_quantity_dict.items() if quantity > 0]
 
    return result       

@frappe.whitelist()
def serial_no_filter(stock_entry_reference):
    issue_item_serial_no = frappe.db.sql(f"""SELECT sed.item_code, sed.serial_no
                                FROM `tabStock Entry Detail` as sed
                                LEFT JOIN `tabStock Entry` as se
                                ON sed.parent = se.name
                                WHERE se.name LIKE '{stock_entry_reference}' 
                                    AND sed.serial_no IS NOT null
    """, as_dict=True)

    customer_approval_item_serial_no = frappe.db.sql(f"""SELECT soic.item_code, soic.serial_no
                                FROM `tabSales Order Item Child` AS soic
                                LEFT JOIN `tabCustomer Approval` AS ca
                                ON soic.parent = ca.name
                                WHERE ca.stock_entry_reference LIKE '{stock_entry_reference}' 
                                    AND soic.serial_no IS NOT null
    """, as_dict=True)
    
    combined_data_ca_serial_no = {}
    
    for entry in customer_approval_item_serial_no:
        item_code = entry['item_code']
        serial_no = entry['serial_no']
        if item_code in combined_data_ca_serial_no:
            combined_data_ca_serial_no[item_code]['serial_no'] += '\n' + serial_no
        else:
            combined_data_ca_serial_no[item_code] = {'item_code': item_code, 'serial_no': serial_no}
    customer_approval_item_serial_no = list(combined_data_ca_serial_no.values())
    
    return_reciept_serial_no = frappe.db.sql(f"""SELECT sed.item_code, sed.serial_no
                                FROM `tabStock Entry Detail` AS sed
                                LEFT JOIN `tabStock Entry` AS se
                                ON sed.parent = se.name
                                WHERE se.custom_material_return_receipt_number LIKE '{stock_entry_reference}'
                                    AND sed.serial_no IS NOT null
    """, as_dict=True)
    
    combined_data_rr_serial_no = {}
    
    for entry in return_reciept_serial_no:
        item_code = entry['item_code']
        serial_no = entry['serial_no']
        if item_code in combined_data_rr_serial_no:
            combined_data_rr_serial_no[item_code]['serial_no'] += '\n' + serial_no
        else:
            combined_data_rr_serial_no[item_code] = {'item_code': item_code, 'serial_no': serial_no}

    return_reciept_serial_no = list(combined_data_rr_serial_no.values())
    
    result = []
    
    for dict_a in issue_item_serial_no:
        item_code = dict_a['item_code']
        serial_a = set(dict_a['serial_no'].split('\n')) if dict_a['serial_no'] else set()

        dict_b = next((d for d in customer_approval_item_serial_no if d['item_code'] == item_code), None)
        serial_b = set(dict_b['serial_no'].split('\n')) if dict_b and dict_b['serial_no'] else set()

        dict_c = next((d for d in return_reciept_serial_no if d['item_code'] == item_code), None)
        serial_c = set(dict_c['serial_no'].split('\n')) if dict_c and dict_c['serial_no'] else set()

        remaining_serials = serial_a - serial_b - serial_c

        result_dict = {'item_code': item_code, 'serial_no': '\n'.join(sorted(remaining_serials))}
        result.append(result_dict)
    return result       

@frappe.whitelist()
def get_bom_no(serial_no):
    result = frappe.get_value('BOM', {'tag_no': serial_no}, ['name', 'gross_weight'])
    if result:
        name, gross_weight = result
    else:
        name, gross_weight = '', ''
    return {"name":name,"gross_weight":gross_weight}