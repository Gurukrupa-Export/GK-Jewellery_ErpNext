from frappe.model.document import Document
import frappe
class TestTS(Document):
    def validate(self):
        if self.docstatus == 1:
            # company = self.company
            customer = self.customer
            employee_name = self.employee_name
            employee = self.employee
            department = self.department
            parent_project = self.parent_project  # Use correct field name
            start_date = self.start_date
            end_date = self.end_date
            
            timesheet = frappe.new_doc("Timesheet")
            # timesheet.company = company
            timesheet.customer = customer
            timesheet.employee_name = employee_name
            timesheet.employee = employee
            timesheet.department = department
            timesheet.parent_project = parent_project
            timesheet.start_date = start_date
            timesheet.end_date = end_date
            
            # Save the "Timesheet" document
            timesheet.insert()

            # Print a success message or perform additional actions
            print("Automation successful: TestTS data copied to Timesheet.")

