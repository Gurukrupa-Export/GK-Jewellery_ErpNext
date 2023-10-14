# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import get_link_to_form

class SketchOrder(Document):
	def validate(self):
		populate_child_table(self)

	def on_submit(self):
		self.make_items()
	
	def make_items(self):
		# if self.workflow_state == "Items Updated":
		for row in self.final_sketch_approval_cmo:
			if row.item or not (row.design_status == "Approved" and row.design_status_cpo == "Approved"):
				continue
			item_template = create_item_template_from_sketch_order(self, row.name)
			updatet_item_template(self,item_template)
			# frappe.msgprint("New Item Template Created: {0}".format(get_link_to_form("Item",item_template)))
			item_variant = create_item_from_sketch_order(self,item_template,row.name)
			update_item_variant(self,item_variant,item_template)
			frappe.db.set_value(row.doctype, row.name, "item", item_template)
			frappe.msgprint("New Item Template {0} & Variant Created {1} ".format(get_link_to_form("Item",item_template),get_link_to_form("Item",item_variant)))

# 
def updatet_item_template(self,item_template):
	frappe.db.set_value('Item',item_template,{
		"is_design_code":0,
		"item_code":item_template
	})

def update_item_variant(self,item_variant,item_template):
	frappe.db.set_value('Item',item_variant,{
		"is_design_code":1,
		"variant_of" : item_template
	})
	# target_doc_ = frappe.get_doc('Item',item_variant)
	# for i in target_doc_.attributes:
	# 	i.attribute = 'Gold Target'
	# 	i.attribute_value = '25'
	
	# target_doc_.save()
	

def populate_child_table(self):
	if self.workflow_state == 'Assigned':
		self.rough_sketch_approval = []
		self.final_sketch_approval = []
		self.final_sketch_approval_cmo = []
		for designer in self.designer_assignment:
			self.append("rough_sketch_approval", {
				"designer": designer.designer,
				"designer_name": designer.designer_name
			})

			self.append("final_sketch_approval", {
				"designer": designer.designer,
				"designer_name": designer.designer_name
			})

			self.append("final_sketch_approval_cmo", {
				"designer": designer.designer,
				"designer_name": designer.designer_name
			})
			
			hod_name = frappe.db.get_value('User', {'email': frappe.session.user}, 'full_name')
			subject = "Sketch Design Assigned"
			context = f"Mr. {hod_name} has assigned you a task"
			user_id = frappe.db.get_value('Employee', designer.designer, 'user_id')
			if user_id : create_system_notification(self, subject, context, [user_id])
		# create_system_notification(self, subject, context, recipients)
		
def create_system_notification(self, subject, context, recipients):
	if not recipients:
		return
	notification_doc = {
		"type": "Alert",
		"document_type": self.doctype,
		"document_name": self.name,
		"subject": subject,
		"from_user": frappe.session.user,
		"email_content": context
	}
	for user in recipients:
		notification = frappe.new_doc("Notification Log")
		notification.update(notification_doc)
		
		notification.for_user = user
		if (
			notification.for_user != notification.from_user
			or notification_doc.get('type') == "Energy Point"
			or notification_doc.get('type') == "Alert"
		):
			notification.insert(ignore_permissions=True)

@frappe.whitelist()
def create_item_template_from_sketch_order(self,source_name, target_doc=None):
	def post_process(source, target):
		
		target.is_design_code = 1
		target.has_variants = 1
		target.stepping = self.stepping
		target.fusion = self.fusion
		target.drops = self.drops
		target.coin = self.coin
		target.gold_wire = self.gold_wire
		target.gold_ball = self.gold_ball
		target.flows = self.flows
		target.nagas = self.nagas
		target.india = self.india
		target.india_states = self.india_states
		target.usa = self.usa
		target.usa_states = self.usa_states
		target.design_attribute = self.design_attributes
		target.order_form_type = 'Sketch Order'
		target.order_form_id = self.name
	doc = get_mapped_doc(
		"Final Sketch Approval CMO",
		source_name,
		{
			"Final Sketch Approval CMO": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"sub_category": "item_subcategory",
					"gold_wt_approx": "approx_gold",
					"diamond_wt_approx": "approx_diamond",
					"sub_category":"subcategory",
				}
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name

def create_item_from_sketch_order(self,item,source_name, target_doc=None):
	def post_process(source, target):
		target.item_code = f'{item}-0001'
		target.stepping = self.stepping
		target.fusion = self.fusion
		target.drops = self.drops
		target.coin = self.coin
		target.gold_wire = self.gold_wire
		target.gold_ball = self.gold_ball
		target.flows = self.flows
		target.nagas = self.nagas
		target.india = self.india
		target.india_states = self.india_states
		target.usa = self.usa
		target.usa_states = self.usa_states
		target.design_attribute = self.design_attributes
		target.order_form_type = 'Sketch Order'
		target.order_form_id = self.name
		
	

	doc = get_mapped_doc(
		"Final Sketch Approval CMO",
		source_name,
		{
			"Final Sketch Approval CMO": {
				"doctype": "Item",
				"field_map": {
					"category": "item_category",
					"sub_category": "item_subcategory",
					"gold_wt_approx": "approx_gold",
					"diamond_wt_approx": "approx_diamond",
					
				}
			}
		},target_doc, post_process
	)
	doc.save()
	return doc.name