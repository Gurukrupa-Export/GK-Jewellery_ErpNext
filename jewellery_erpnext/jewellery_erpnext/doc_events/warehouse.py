import frappe
from frappe import _

def validate(doc, method=None):
    if doc.department and doc.employee:
        frappe.throw(_("You can fill in either the department or employee field, but not both."))
    check_unique(doc.name, "department", doc.department)
    check_unique(doc.name, "employee", doc.employee)
    check_unique(doc.name, "subcontractor", doc.subcontractor)
    

def check_unique(name, fieldname, value):
    if not value:
        return
    if existing:=frappe.db.exists('Warehouse', {fieldname: value, "name": ["!=", name]}):
        frappe.throw(_(f"Warehouse: {existing} already have {fieldname} = {value}"))