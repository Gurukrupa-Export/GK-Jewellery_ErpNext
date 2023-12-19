// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Timesheet", {
    refresh: function(frm) {
		if (frm.doc.docstatus < 1) {

			let button = 'Start Timer';
			$.each(frm.doc.time_logs || [], function(_i, row) {
				if ((row.from_time <= frappe.datetime.now_datetime()) && !row.completed) {
					button = 'Resume Timer';
                    if (row.to_time){
                        button = 'Start Timer';
                    }
				}
			});

			frm.add_custom_button(__(button), function() {
				var flag = true;
				$.each(frm.doc.time_logs || [], function(i, row) {
					// Fetch the row for which from_time is not present
					if (flag && row.activity_type && !row.from_time){
						erpnext.timesheet.timer(frm, row);
						row.from_time = frappe.datetime.now_datetime();
						frm.refresh_fields("time_logs");
						frm.save();
						flag = false;
					}
					// Fetch the row for timer where activity is not completed and from_time is before now_time
					if (flag && row.from_time <= frappe.datetime.now_datetime() && !row.completed) {
						let timestamp = moment(frappe.datetime.now_datetime()).diff(moment(row.from_time),"seconds");
						erpnext.timesheet.timer(frm, row, timestamp);
						flag = false;
					}
				});
				// If no activities found to start a timer, create new
				if (flag) {
					erpnext.timesheet.timer(frm);
				}
			}).addClass("btn-primary");
		}
	},
});

frappe.ui.form.on("Timesheet Detail", {
	time_logs_remove: function(frm) {
		calculate_time_and_amount(frm);
	},

	from_time: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn);
	},

	to_time: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if(frm._setting_hours) return;

		var hours = moment(child.to_time).diff(moment(child.from_time), "seconds") / 3600;
		frappe.model.set_value(cdt, cdn, "hours", hours);
	},

	time_logs_add: function(frm, cdt, cdn) {
		if(frm.doc.parent_project) {
			frappe.model.set_value(cdt, cdn, 'project', frm.doc.parent_project);
		}
	},

	hours: function(frm, cdt, cdn) {
		calculate_end_time(frm, cdt, cdn);
		// calculate_billing_costing_amount(frm, cdt, cdn);
		// calculate_time_and_amount(frm);
	},

	// billing_hours: function(frm, cdt, cdn) {
	// 	calculate_billing_costing_amount(frm, cdt, cdn);
	// 	calculate_time_and_amount(frm);
	// },

	// billing_rate: function(frm, cdt, cdn) {
	// 	calculate_billing_costing_amount(frm, cdt, cdn);
	// 	calculate_time_and_amount(frm);
	// },

	// costing_rate: function(frm, cdt, cdn) {
	// 	calculate_billing_costing_amount(frm, cdt, cdn);
	// 	calculate_time_and_amount(frm);
	// },

	// is_billable: function(frm, cdt, cdn) {
	// 	update_billing_hours(frm, cdt, cdn);
	// 	update_time_rates(frm, cdt, cdn);
	// 	calculate_billing_costing_amount(frm, cdt, cdn);
	// 	calculate_time_and_amount(frm);
	// },

	// activity_type: function (frm, cdt, cdn) {
	// 	if (!frappe.get_doc(cdt, cdn).activity_type) return;

	// 	frappe.call({
	// 		method: "erpnext.projects.doctype.timesheet.timesheet.get_activity_cost",
	// 		args: {
	// 			employee: frm.doc.employee,
	// 			activity_type: frm.selected_doc.activity_type,
	// 			currency: frm.doc.currency
	// 		},
	// 		callback: function (r) {
	// 			if (r.message) {
	// 				frappe.model.set_value(cdt, cdn, "billing_rate", r.message["billing_rate"]);
	// 				frappe.model.set_value(cdt, cdn, "costing_rate", r.message["costing_rate"]);
	// 				calculate_billing_costing_amount(frm, cdt, cdn);
	// 			}
	// 		}
	// 	});
	// }
});

// var calculate_end_time = function(frm, cdt, cdn) {
// 	let child = locals[cdt][cdn];

// 	if(!child.from_time) {
// 		// if from_time value is not available then set the current datetime
// 		frappe.model.set_value(cdt, cdn, "from_time", frappe.datetime.get_datetime_as_string());
// 	}

// 	let d = moment(child.from_time);
// 	if(child.hours) {
// 		d.add(child.hours, "hours");
// 		frm._setting_hours = true;
// 		frappe.model.set_value(cdt, cdn, "to_time",
// 			d.format(frappe.defaultDatetimeFormat)).then(() => {
// 			frm._setting_hours = false;
// 		});
// 	}
// };

// var update_billing_hours = function(frm, cdt, cdn) {
// 	let child = frappe.get_doc(cdt, cdn);
// 	if (!child.is_billable) {
// 		frappe.model.set_value(cdt, cdn, 'billing_hours', 0.0);
// 	} else {
// 		// bill all hours by default
// 		frappe.model.set_value(cdt, cdn, "billing_hours", child.hours);
// 	}
// };

// var update_time_rates = function(frm, cdt, cdn) {
// 	let child = frappe.get_doc(cdt, cdn);
// 	if (!child.is_billable) {
// 		frappe.model.set_value(cdt, cdn, 'billing_rate', 0.0);
// 	}
// };

// var calculate_billing_costing_amount = function(frm, cdt, cdn) {
// 	let row = frappe.get_doc(cdt, cdn);
// 	let billing_amount = 0.0;
// 	let base_billing_amount = 0.0;
// 	let exchange_rate = flt(frm.doc.exchange_rate);
// 	frappe.model.set_value(cdt, cdn, 'base_billing_rate', flt(row.billing_rate) * exchange_rate);
// 	frappe.model.set_value(cdt, cdn, 'base_costing_rate', flt(row.costing_rate) * exchange_rate);
// 	if (row.billing_hours && row.is_billable) {
// 		base_billing_amount = flt(row.billing_hours) * flt(row.base_billing_rate);
// 		billing_amount = flt(row.billing_hours) * flt(row.billing_rate);
// 	}

// 	frappe.model.set_value(cdt, cdn, 'base_billing_amount', base_billing_amount);
// 	frappe.model.set_value(cdt, cdn, 'base_costing_amount', flt(row.base_costing_rate) * flt(row.hours));
// 	frappe.model.set_value(cdt, cdn, 'billing_amount', billing_amount);
// 	frappe.model.set_value(cdt, cdn, 'costing_amount', flt(row.costing_rate) * flt(row.hours));
// };

// var calculate_time_and_amount = function(frm) {
// 	let tl = frm.doc.time_logs || [];
// 	let total_working_hr = 0;
// 	let total_billing_hr = 0;
// 	let total_billable_amount = 0;
// 	let total_costing_amount = 0;
// 	for(var i=0; i<tl.length; i++) {
// 		if (tl[i].hours) {
// 			total_working_hr += tl[i].hours;
// 			total_billable_amount += tl[i].billing_amount;
// 			total_costing_amount += tl[i].costing_amount;

// 			if (tl[i].is_billable) {
// 				total_billing_hr += tl[i].billing_hours;
// 			}
// 		}
// 	}

// 	frm.set_value("total_billable_hours", total_billing_hr);
// 	frm.set_value("total_hours", total_working_hr);
// 	frm.set_value("total_billable_amount", total_billable_amount);
// 	frm.set_value("total_costing_amount", total_costing_amount);
// };

// // set employee (and company) to the one that's currently logged in
// const set_employee_and_company = function(frm) {
// 	const options = { user_id: frappe.session.user };
// 	const fields = ['name', 'company'];
// 	frappe.db.get_value('Employee', options, fields).then(({ message }) => {
// 		if (message) {
// 			// there is an employee with the currently logged in user_id
// 			frm.set_value("employee", message.name);
// 			frm.set_value("company", message.company);
// 		}

// 	});
// };

// function set_project_in_timelog(frm) {
// 	if(frm.doc.parent_project) {
// 		$.each(frm.doc.time_logs || [], function(i, item) {
// 			frappe.model.set_value(item.doctype, item.name, "project", frm.doc.parent_project);
// 		});
// 	}
// }
