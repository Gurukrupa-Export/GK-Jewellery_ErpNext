# Copyright (c) 2023, Nirali and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import (
	add_days,
	add_to_date,
	cint,
	flt,
	get_datetime,
	get_link_to_form,
	get_time,
	getdate,
	time_diff,
	time_diff_in_hours,
	time_diff_in_seconds,
	
	
)
from frappe.model.document import Document

class DemoDharm(Document):
	pass


@frappe.whitelist()
def get_time(from_time,to_time,employee):
	in_hours = time_diff(to_time, from_time)
	time_in_hours = str(in_hours)[:-3]

	default_shift = frappe.db.get_value('Employee',employee,'default_shift')
	shift_hours = frappe.db.get_value('Shift Type',default_shift,['start_time','end_time'])
	total_shift_hours = time_diff(shift_hours[1], shift_hours[0])
	
	if in_hours >= total_shift_hours:
		in_days = in_hours/total_shift_hours
		return in_days
	# else:
	# 	return in_hours