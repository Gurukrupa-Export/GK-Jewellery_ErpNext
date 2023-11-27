// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.views.calendar["Manufacturing Work Order"] = {
	fields:  ["posting_date", "manufacturing_end_date", "docstatus", "name", "name"],
	field_map: {
		"start": "posting_date",
		"end": "manufacturing_end_date",
		"id": "name",
		"title": "name",
		"docstatus": "docstatus",
		// "allDay": "allDay",
		// "progress": function(data) {
		// 	return flt(data.produced_qty) / data.qty * 100;
		// }
	},
	gantt: true,
	get_css_class: function(data) {
		if(data.docstatus===1) {
			return "success";
		} else if(data.docstatus===0) {
			return "warning";
		} else {
			return "danger";
		}
	},
	// filters: [
	// 	{
	// 		"fieldtype": "Link",
	// 		"fieldname": "sales_order",
	// 		"options": "Sales Order",
	// 		"label": __("Sales Order")
	// 	},
		// {
		// 	"fieldtype": "Link",
		// 	"fieldname": "production_item",
		// 	"options": "Item",
		// 	"label": __("Production Item")
		// },
		// {
		// 	"fieldtype": "Link",
		// 	"fieldname": "wip_warehouse",
		// 	"options": "Warehouse",
		// 	"label": __("WIP Warehouse")
		// }
	// ],
	// get_events_method: "frappe.desk.calendar.get_events"
}
