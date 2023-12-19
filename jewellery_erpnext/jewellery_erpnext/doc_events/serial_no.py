import frappe
from frappe.model.naming import make_autoname
def before_submit(self, method=None):
    apply_custom_serial_number = 0 #frappe.db.get_value("Manufacturing Setting", self.company, 'apply_custom_serial_number')
    if apply_custom_serial_number == 1:
        for item in self.items:
            serial_no = ""
            date_to_letter = {0:'A', 1:'B', 2:'C', 3:'D', 4:'E', 5:'F', 6:'G', 7:'H', 8:'I', 9:'J'}
            series_start, abbr = frappe.db.get_value("Manufacturing Setting", self.company, ['series_start', 'abbr'])
            if not series_start or not abbr:
                frappe.throw(f"Please Add Series Start and Abbr in Jewellery Setting of <strong>{self.company}</strong>")

            attritube = frappe.db.sql(f"""select attribute_value from `tabItem Variant Attribute`
                                where parent = '{item.item_code}' and attribute = "Naming Series Abb" """,as_dict=True)
            if not attritube:
                frappe.throw(f"Varient Not Found with attribute <strong>Naming Series Abb</strong> in Item: <strong>{item.item_code}</strong>")
                
            date = self.posting_date[2:4]
            for i in range(item.qty):
                sr_no = make_autoname(series_start+"-"+abbr+"-"+attritube[0].attribute_value+"-"+date[0]+"-"+date_to_letter[int(date[1])]+"-.####")
                serial_no += sr_no + "\n" 
            item.serial_no = serial_no