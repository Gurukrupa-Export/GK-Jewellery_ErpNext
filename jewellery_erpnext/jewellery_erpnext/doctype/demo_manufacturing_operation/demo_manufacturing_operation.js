// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('demo Manufacturing Operation', {
	refresh: function(frm) {
		frm.toggle_display("started_time", false);
		frm.toggle_display("current_time", false);
		// set_html(frm)

		frappe.flags.pause_job = 0;
		frappe.flags.resume_job = 0;

		if(frm.doc.docstatus == 0 && !frm.is_new()){
			frm.trigger("prepare_timer_buttons");
		}
	},

	prepare_timer_buttons: function(frm) {
		frm.trigger("make_dashboard");

		if (!frm.doc.started_time && !frm.doc.current_time) {
			frm.add_custom_button(__("Start Job"), () => {
				if ((frm.doc.employee && !frm.doc.employee.length) || !frm.doc.employee) {
					frappe.prompt({fieldtype: 'Table MultiSelect', label: __('Select Employees'),
						options: "Job Card Time Log", fieldname: 'employees'}, d => {
						frm.events.start_job(frm, "Work In Progress", d.employees);
					}, __("Assign Job to Employee"));
				} else {
					frm.events.start_job(frm, "Work In Progress", frm.doc.employee);
				}
			}).addClass("btn-primary");
		} 
		// else if (frm.doc.status == "QC Pending"){
		// 	frm.add_custom_button(__("Resume Job"), () => {
		// 		frm.events.start_job(frm, "Resume Job", frm.doc.employee);
		// 	}).addClass("btn-primary");
		// }
		// else if(frm.doc.status == "Work In Progress"){
		// 	frm.add_custom_button(__("Pause Job"), () => {
		// 		frm.events.start_job(frm, "On Hold");
		// 	});
		// 	// .addClass("btn-primary");
		// 	frm.add_custom_button(__("Complete Job"), () => {
		// 		var sub_operations = frm.doc.sub_operations;

		// 		let set_qty = true;
		// 		if (sub_operations && sub_operations.length > 1) {
		// 			set_qty = false;
		// 			let last_op_row = sub_operations[sub_operations.length - 2];

		// 			if (last_op_row.status == 'Complete') {
		// 				set_qty = true;
		// 			}
		// 		}

		// 		if (set_qty) {
		// 			frm.events.complete_job(frm, "Complete", 0.0);
		// 		}
		// 	}).addClass("btn-primary");
		// }
		else if (frm.doc.status == "QC Pending" || frm.doc.status == "On Hold") {
			frm.add_custom_button(__("Resume Job"), () => {
				frm.events.start_job(frm, "Resume Job", frm.doc.employee);
			}).addClass("btn-primary");
		} 
		else {
			//it's for complete job which require sub_operations
			frm.add_custom_button(__("Pause Job"), () => {
				frm.events.complete_job(frm, "QC Pending");
				frm.events.complete_job(frm, "On Hold");
			});

			frm.add_custom_button(__("Complete Job"), () => {
				var sub_operations = frm.doc.sub_operations;

				let set_qty = true;
				if (sub_operations && sub_operations.length > 1) {
					set_qty = false;
					let last_op_row = sub_operations[sub_operations.length - 2];

					if (last_op_row.status == 'Complete') {
						set_qty = true;
					}
				}

				if (set_qty) {
					frm.events.complete_job(frm, "Complete", 0.0);
				// 	frappe.prompt({fieldtype: 'Float', label: __('Completed Quantity'),
				// 		fieldname: 'qty', default: frm.doc.for_quantity}, data => {
				// 		frm.events.complete_job(frm, "Complete", data.qty);
				// 	}, __("Enter Value"));
				// } else {
				}
			}).addClass("btn-primary");
		}
	},

	start_job: function(frm, status, employee) {
		const args = {
			job_card_id: frm.doc.name,
			start_time: frappe.datetime.now_datetime(),
			employees: employee,
			status: status
		};
		frm.events.make_time_log(frm, args);
	},

	complete_job: function(frm, status) {
		const args = {
			job_card_id: frm.doc.name,
			complete_time: frappe.datetime.now_datetime(),
			status: status,
			// completed_qty: completed_qty
		};
		frm.events.make_time_log(frm, args);
	},

	make_time_log: function(frm, args) {
		frm.events.update_sub_operation(frm, args);

		frappe.call({
			method: "jewellery_erpnext.jewellery_erpnext.doctype.demo_manufacturing_operation.demo_manufacturing_operation.make_time_log",
			args: {
				args: args
			},
			freeze: true,
			callback: function () {
				frm.reload_doc();
				frm.trigger("make_dashboard");
			}
		});
	},

	update_sub_operation: function(frm, args) {
		if (frm.doc.sub_operations && frm.doc.sub_operations.length) {
			let sub_operations = frm.doc.sub_operations.filter(d => d.status != 'Complete');
			if (sub_operations && sub_operations.length) {
				args["sub_operation"] = sub_operations[0].sub_operation;
			}
		}
	},

	validate: function(frm) {
		if ((!frm.doc.time_logs || !frm.doc.time_logs.length) && frm.doc.started_time) {
			frm.trigger("reset_timer");
		}
	},

	reset_timer: function(frm) {
		frm.set_value('started_time' , '');
	},

	hide_timer: function(frm) {
		frm.toolbar.page.inner_toolbar.find(".stopwatch").remove();
	},

	make_dashboard: function(frm) {
		if(frm.doc.__islocal)
			return;

		frm.dashboard.refresh();
		const timer = `
			<div class="stopwatch" style="font-weight:bold;margin:0px 13px 0px 2px;
				color:#545454;font-size:18px;display:inline-block;vertical-align:text-bottom;>
				<span class="hours">00</span>
				<span class="colon">:</span>
				<span class="minutes">00</span>
				<span class="colon">:</span>
				<span class="seconds">00</span>
			</div>`;

		var section = frm.toolbar.page.add_inner_message(timer);

		let currentIncrement = frm.doc.current_time || 0;
		console.log(frm.doc.current_time)
		if (frm.doc.started_time || frm.doc.current_time) {
			if (frm.doc.status == "QC Pending") {
				updateStopwatch(currentIncrement);
			} 
			else if (frm.doc.status == "On Hold") {
				updateStopwatch(currentIncrement);	
			}
			else {
				currentIncrement += moment(frappe.datetime.now_datetime()).diff(moment(frm.doc.started_time),"seconds");
				initialiseTimer();
			}

			function initialiseTimer() {
				const interval = setInterval(function() {
					var current = setCurrentIncrement();
					updateStopwatch(current);
				}, 1000);
			}

			function updateStopwatch(increment) {
				var hours = Math.floor(increment / 3600);
				var minutes = Math.floor((increment - (hours * 3600)) / 60);
				var seconds = increment - (hours * 3600) - (minutes * 60);

				$(section).find(".hours").text(hours < 10 ? ("0" + hours.toString()) : hours.toString());
				$(section).find(".minutes").text(minutes < 10 ? ("0" + minutes.toString()) : minutes.toString());
				$(section).find(".seconds").text(seconds < 10 ? ("0" + seconds.toString()) : seconds.toString());
			}

			function setCurrentIncrement() {
				currentIncrement += 1;
				return currentIncrement;
			}
		}
	},

	// set_total_completed_qty: function(frm) {
	// 	frm.doc.total_completed_qty = 0;
	// 	frm.doc.time_logs.forEach(d => {
	// 		if (d.completed_qty) {
	// 			frm.doc.total_completed_qty += d.completed_qty;
	// 		}
	// 	});

	// 	if (frm.doc.total_completed_qty && frm.doc.for_quantity > frm.doc.total_completed_qty) {
	// 		let flt_precision = precision('for_quantity', frm.doc);
	// 		let process_loss_qty = (
	// 			flt(frm.doc.for_quantity, flt_precision)
	// 			- flt(frm.doc.total_completed_qty, flt_precision)
	// 		);

	// 		frm.set_value('process_loss_qty', process_loss_qty);
	// 	}

	// 	refresh_field("total_completed_qty");
	// }
});

frappe.ui.form.on('Job Card Time Log', {
	// completed_qty: function(frm) {
	// 	frm.events.set_total_completed_qty(frm);
	// },

	to_time: function(frm) {
		frm.set_value('started_time', '');
	}
})
