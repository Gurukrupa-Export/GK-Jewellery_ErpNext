// Copyright (c) 2023, Nirali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sketch Order Rating', {
	design_image_rating: function(frm) {
		console.log((cur_frm.doc.design_image_rating*10)/2)
		frm.set_value('design_image_rating_count',(cur_frm.doc.design_image_rating*10)/2)
	},
	sketch_image_rating: function(frm) {
		console.log((cur_frm.doc.design_image_rating*10)/2)
		frm.set_value('sketch_image_rating_count',(cur_frm.doc.sketch_image_rating*10)/2)
	},
	design_image1_rating: function(frm) {
		console.log((cur_frm.doc.design_image_rating*10)/2)
		frm.set_value('design_image1_rating_count',(cur_frm.doc.design_image1_rating*10)/2)
	},
	design_image2_rating: function(frm) {
		console.log((cur_frm.doc.design_image_rating*10)/2)
		frm.set_value('design_image2_rating_count',(cur_frm.doc.design_image2_rating*10)/2)
	},
	design_image3_rating: function(frm) {
		console.log((cur_frm.doc.design_image_rating*10)/2)
		frm.set_value('design_image3_rating_count',(cur_frm.doc.design_image3_rating*10)/2)
	},
	design_image4_rating: function(frm) {
		console.log((cur_frm.doc.design_image_rating*10)/2)
		frm.set_value('design_image4_rating_count',(cur_frm.doc.design_image4_rating*10)/2)
	},
});
