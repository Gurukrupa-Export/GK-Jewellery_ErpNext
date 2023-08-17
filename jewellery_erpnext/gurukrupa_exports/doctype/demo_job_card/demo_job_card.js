// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Demo Job Card', {
	refresh:function(frm){
		frappe.flags.pause_job = 0;
		frappe.flags.resume_job = 0;
		if (frm.doc.docstatus == 0 && !frm.is_new() &&
			(frm.doc.for_quantity > frm.doc.total_completed_qty || !frm.doc.for_quantity)
			&& (frm.doc.items || !frm.doc.items.length || frm.doc.for_quantity == frm.doc.transferred_qty)) {
			
			// if Job Card is link to Work Order, the job card must not be able to start if Work Order not "Started"
			// and if stock mvt for WIP is required
			if (frm.doc.work_order) {
				console.log(frm.doc.work_order)
				frappe.db.get_value('Work Order', frm.doc.work_order, ['skip_transfer', 'status'], (result) => {
					console.log(result.skip_transfer)
					console.log(result)
					if (result.skip_transfer === 1 || result.status == 'In Process' || frm.doc.transferred_qty > 0 || !frm.doc.items.length) {
						frm.trigger("prepare_timer_buttons");
					}
				});
			} else {
				frm.trigger("prepare_timer_buttons");
			}
		}
	},
	prepare_timer_buttons: function(frm) {
		frm.trigger("make_dashboard");
		console.log('here2')
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
		} else if (frm.doc.status == "On Hold") {
			frm.add_custom_button(__("Resume Job"), () => {
				frm.events.start_job(frm, "Resume Job", frm.doc.employee);
			}).addClass("btn-primary");
		} else {
			frm.add_custom_button(__("Pause Job"), () => {
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
					frappe.prompt({fieldtype: 'Float', label: __('Completed Quantity'),
						fieldname: 'qty', default: frm.doc.for_quantity}, data => {
						frm.events.complete_job(frm, "Complete", data.qty);
					}, __("Enter Value"));
				} else {
					frm.events.complete_job(frm, "Complete", 0.0);
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

	complete_job: function(frm, status, completed_qty) {
		const args = {
			job_card_id: frm.doc.name,
			complete_time: frappe.datetime.now_datetime(),
			status: status,
			completed_qty: completed_qty
		};
		frm.events.make_time_log(frm, args);
	},
	make_time_log: function(frm, args) {
		frm.events.update_sub_operation(frm, args);

		frappe.call({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_time_log",
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
	timer: function(frm) {
		return `<button> Start </button>`
	},

	set_total_completed_qty: function(frm) {
		frm.doc.total_completed_qty = 0;
		frm.doc.time_logs.forEach(d => {
			if (d.completed_qty) {
				frm.doc.total_completed_qty += d.completed_qty;
			}
		});

		if (frm.doc.total_completed_qty && frm.doc.for_quantity > frm.doc.total_completed_qty) {
			let flt_precision = precision('for_quantity', frm.doc);
			let process_loss_qty = (
				flt(frm.doc.for_quantity, flt_precision)
				- flt(frm.doc.total_completed_qty, flt_precision)
			);

			frm.set_value('process_loss_qty', process_loss_qty);
		}

		refresh_field("total_completed_qty");
	},
	make_dashboard: function(frm) {
		console.log('here')
		if(frm.doc.__islocal)
			return;

		frm.dashboard.refresh();
		const timer = `
			<div class="stopwatch" style="font-weight:bold;margin:0px 13px 0px 2px;
				color:#FF0000;font-size:18px;display:inline-block;vertical-align:text-bottom;>
				<span class="hours">00</span>
				<span class="colon">:</span>
				<span class="minutes">00</span>
				<span class="colon">:</span>
				<span class="seconds">00</span>
			</div>`;

		var section = frm.toolbar.page.add_inner_message(timer);

		let currentIncrement = frm.doc.current_time || 0;
		if (frm.doc.started_time || frm.doc.current_time) {
			if (frm.doc.status == "On Hold") {
				
				updateStopwatch(currentIncrement);
			} else {
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
});
