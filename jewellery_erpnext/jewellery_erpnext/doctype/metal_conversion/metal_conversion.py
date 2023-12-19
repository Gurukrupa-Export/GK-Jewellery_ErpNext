# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MetalConversion(Document):
    def before_save(self):
        self.create_stock_entry()

    def create_stock_entry(self):
        if self.customer_received_voucher:
            crv = frappe.get_doc("Stock Entry",{"name": self.customer_received_voucher})
            company = crv.company
            for itm in crv.items:
                itm_list1 = {
                        "s_warehouse" : itm.t_warehouse,
                        "item_code" : itm.item_code,
                        "qty" : itm.qty,
                        "customer" : itm.customer,
                        "inventory_type" : itm.inventory_type,
                        "batch_no" : itm.batch_no,
                        "basic_rate": itm.basic_rate,
                        "basic_amount": itm.basic_amount
                    }
                
                itm_list2 = {
                    "t_warehouse" : itm.t_warehouse,
                    "item_code" : self.mix_metal,
                    "qty" : self.mix_weight,
                    "customer" : itm.customer,
                    "inventory_type" : itm.inventory_type
                }    
                

                parts = itm.item_code.split('-')
                parts[3] = self.to_purity 

                new_itm = '-'.join(parts)
                new_itm_nme = frappe.db.get_value("Item", new_itm, "name")
   
                if new_itm_nme:
                    itm_name = new_itm_nme
                else:
                    frappe.throw("No Item is Found for the selected 'To Purity'")

                itm_list3 = {
                    "t_warehouse" : itm.t_warehouse,
                    "item_code" : itm_name,
                    "qty" : self.total_received_wt,
                    "customer" : itm.customer,
                    "inventory_type" : itm.inventory_type
                }           

            se = frappe.new_doc("Stock Entry")
            se.stock_entry_type = "Repack"
            se.inventory_type = crv.inventory_type
            se._customer = crv._customer
            se.custom_metal_conversion_reference = self.customer_received_voucher
            se.company = company
            se.append("items", itm_list1)
            se.append("items", itm_list2)
            se.append("items", itm_list3)

            se.save()
            se.submit()

            frappe.msgprint(f"Stock Entry { se.name } is created")

    @frappe.whitelist()
    def get_linked_item_details(self):
        se = frappe.get_doc("Stock Entry", self.customer_received_voucher)

        data = frappe.db.sql(f"""SELECT
                    sed.item_code AS item_code,
                    MAX(CASE
                        WHEN va1.attribute = "Metal Purity" THEN va1.attribute_value
                        ELSE NULL
                    END) AS metal_purity,
                    MAX(CASE
                        WHEN va2.attribute = "Metal Colour" THEN va2.attribute_value
                        ELSE NULL
                    END) AS metal_colour,
                    MAX(CASE
                        WHEN va3.attribute = "Metal Touch" THEN va3.attribute_value
                        ELSE NULL
                    END) AS metal_touch,
                    sed.qty AS qty,
                    b.batch_qty - sed.qty AS remaining_qty
                FROM `tabStock Entry` se 
                JOIN `tabBatch` b on b.name = "{ self.batch_no }"
                JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
                JOIN `tabItem` itm ON itm.name = sed.item_code
                LEFT JOIN `tabItem Variant Attribute` va1 ON va1.parent = itm.name AND va1.attribute = "Metal Purity"
                LEFT JOIN `tabItem Variant Attribute` va2 ON va2.parent = itm.name AND va2.attribute = "Metal Colour"
                LEFT JOIN `tabItem Variant Attribute` va3 ON va3.parent = itm.name AND va3.attribute = "Metal Touch"
                WHERE se.name = "{ se.name }"
                GROUP BY sed.item_code;
                """, as_dict=1)

        return frappe.render_template("gurukrupa_customizations/gurukrupa_customizations/doctype/metal_conversion/item_details.html", {"data":data})


    @frappe.whitelist()
    def get_itm_det(self):
        batch_no = ""
        metal_wt = ""
        metal_type = ""
        metal_purity = ""

        if self.customer_received_voucher:
            se = frappe.get_doc("Stock Entry", self.customer_received_voucher)
            batch_no = se.items[0].get("batch_no")

            if batch_no:
                metal_wt = frappe.db.get_value("Batch", batch_no, "batch_qty")

            itm = frappe.get_doc("Item", se.items[0].get("item_code"))
            for i in itm.attributes:
                if i.attribute == "Metal Type":
                    metal_type = i.attribute_value

                if i.attribute == "Metal Purity":
                    metal_purity = i.attribute_value
                

            return {"batch_no": batch_no, "metal_wt": metal_wt, "metal_type": metal_type, "metal_purity": metal_purity}

    @frappe.whitelist()
    def get_list_of_metal_purity(self):
        attr = frappe.get_doc("Item Attribute", "Metal Purity")

        attr_list = []
        for a in attr.item_attribute_values:
            attr_list.append(a.attribute_value)

        return attr_list