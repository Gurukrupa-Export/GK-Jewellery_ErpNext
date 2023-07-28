frappe.ui.form.on('Demo', {
	refresh: function(frm) {
	  frm.fields_dict['start'].$input.on('change', function() {
		if (frm.doc.start) {
		  frm.set_value('timer', 60); // Set the initial time in seconds (e.g., 60 seconds)
		  frm.timer_interval = setInterval(function() {
			var remaining_time = frm.doc.timer - 1;
			frm.set_value('timer', remaining_time);
			if (remaining_time <= 0) {
			  clearInterval(frm.timer_interval);
			}
		  }, 1000); // Update timer every 1000 milliseconds (1 second)
		} else {
		  clearInterval(frm.timer_interval); // Stop the timer when 'Start' is unchecked
		}
	  });
	}
  });
  