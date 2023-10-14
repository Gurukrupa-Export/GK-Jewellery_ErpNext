frappe.ui.form.on('Stock Entry', {
    refresh(frm) {
        frm.trigger("get_items_from_customer_goods")
    },
    validate(frm) {
        $.each(frm.doc.items || [], function(i, row) {
            row.inventory_type = frm.doc.inventory_type;
            row.customer = frm.doc._customer;
            row.branch = frm.doc.branch;
            row.department = frm.doc.department;
            row.to_department = frm.doc.to_department;
            row.main_slip = frm.doc.main_slip;
            row.to_main_slip = frm.doc.to_main_slip;
            row.employee = frm.doc.employee;
            row.to_employee = frm.doc.to_employee;
            row.subcontractor = frm.doc.subcontractor
            row.to_subcontractor = frm.doc.to_subcontractor
            row.project = frm.doc.project;
            row.manufacturing_operation = frm.doc.manufacturing_operation
        })
        refresh_field("items");
    },
    get_items_from_customer_goods(frm) {
        if (frm.doc.docstatus===0 && frm.doc.stock_entry_type == "Customer Goods Issue") {
            frm.add_custom_button(__('Customer Goods Received'), function() {
                erpnext.utils.map_current_doc({
                    method: "jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry.make_stock_in_entry",
                    source_doctype: "Stock Entry",
                    target: frm,
                    date_field: "posting_date",
                    setters: {
                        stock_entry_type: "Customer Goods Received",
                        purpose: "Material Receipt",
                        _customer: frm.doc._customer,
                        inventory_type: frm.doc.inventory_type
                    },
                    get_query_filters: {
                        docstatus: 1,
                        purpose: "Material Receipt",
                    },
    		    	size: "extra-large"

                })
            }, __("Get Items From"));
        }
        else {
            frm.remove_custom_button(__('Customer Goods Received'),__("Get Items From"))
        }
    },
    setup: function (frm) {
        frm.set_query('item_template', function (doc) {
            return { filters: { 'has_variants': 1 } }
        });
        frm.set_query('manufacturing_work_order', function(doc) {
		    return {
		        filters: {
		            "manufacturing_order": frm.doc.manufacturing_order
		        }
		    }
		});
		frm.set_query("manufacturing_operation", function(doc) {
		    return {
		        filters: {
		            "manufacturing_work_order": frm.doc.manufacturing_work_order,
                    "status": ['not in', ["Finished", "Revert"]]
		        }
		    }
		})
        frm.set_query("department", function(doc) {
		    return {
		        filters: {
		            "company": frm.doc.company
		        }
		    }
		})
        frm.set_query("to_department", function(doc) {
		    return {
		        filters: {
		            "company": frm.doc.company
		        }
		    }
		})
        frm.set_query("employee", function(doc) {
		    return {
		        filters: {
		            "department": frm.doc.department
		        }
		    }
		})
        frm.set_query("to_employee", function(doc) {
		    return {
		        filters: {
		            "department": frm.doc.to_department
		        }
		    }
		})
        frm.set_query("main_slip", function(doc) {
		    return {
		        filters: {
		            "docstatus": 0
		        }
		    }
		})
        frm.set_query("to_main_slip", function(doc) {
		    return {
		        filters: {
		            "docstatus": 0
		        }
		    }
		})
        frm.fields_dict['item_template_attribute'].grid.get_field('attribute_value').get_query = function (frm, cdt, cdn) {
            var child = locals[cdt][cdn];
            return {
                query: 'jewellery_erpnext.query.item_attribute_query',
                filters: { 'item_attribute': child.item_attribute }
            }
        }
    },
    onload_post_render: function (frm) {
        frm.fields_dict['item_template_attribute'].grid.wrapper.find('.grid-remove-rows').remove();
        frm.fields_dict['item_template_attribute'].grid.wrapper.find('.grid-add-multiple-rows').remove();
        frm.fields_dict['item_template_attribute'].grid.wrapper.find('.grid-add-row').remove();
        frm.trigger("stock_entry_type")
    },
    from_job_card: function (frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.from_job_card = frm.doc.from_job_card;
        });
    },
    to_job_card: function (frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.to_job_card = frm.doc.to_job_card;
        });
    },
    item_template: function (frm) {
        if (frm.doc.item_template) {
            frm.doc.item_template_attribute = []
            frappe.model.with_doc("Item", frm.doc.item_template, function () {
                var item_template = frappe.model.get_doc("Item", frm.doc.item_template);
                $.each(item_template.attributes, function (index, d) {
                    let row = frm.add_child('item_template_attribute')
                    row.item_attribute = d.attribute
                })
                frm.refresh_field('item_template_attribute')
            })
        }
    },
    add_item: function (frm) {
        if (!frm.doc.item_template_attribute || !frm.doc.item_template) {
            frappe.throw("Please select Item Template.")
        }
        frappe.call({
            method: "jewellery_erpnext.utils.set_items_from_attribute",
            args: {
                item_template: frm.doc.item_template,
                item_template_attribute: frm.doc.item_template_attribute
            },
            callback: function (r) {
                if (r.message) {
                    let item = frm.add_child('items')
                    item.item_code = r.message.name
                    item.qty = 1
                    item.transfer_qty = 1
                    item.uom = r.message.stock_uom
                    item.stock_uom = r.message.stock_uom
                    item.conversion_factor = 1
                    frm.refresh_field('items')
                    frm.set_value('item_template', '')
                    frm.doc.item_template_attribute = []
                    frm.refresh_field('item_template_attribute')
                }
            }
        })
    },
    stock_entry_type(frm) {
        if (in_list(["Customer Goods Issue","Customer Goods Received"],frm.doc.stock_entry_type)){
            frm.set_value('inventory_type', 'Customer Goods')
        }
        else {
            frm.set_value('inventory_type', 'Regular Stock')
        }
        frm.trigger("get_items_from_customer_goods")
    },
    inventory_type(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.inventory_type = frm.doc.inventory_type;
        });
    },
    _customer(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.customer = frm.doc._customer;
        });
    },
    branch(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.branch = frm.doc.branch;
        });
    },
    department(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.department = frm.doc.department;
        });
    },
    to_department(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.to_department = frm.doc.to_department;
        });
    },
    main_slip(frm) {
        if (frm.doc.main_slip) {
            frappe.db.get_value("Main Slip", frm.doc.main_slip, "employee", (r)=> {
                frm.set_value("employee",r.employee)
            })
        }
        $.each(frm.doc.items || [], function (i, d) {
            d.main_slip = frm.doc.main_slip;
        });
    },
    to_main_slip(frm) {
        if (frm.doc.to_main_slip) {
            frappe.db.get_value("Main Slip", frm.doc.to_main_slip, "employee", (r)=> {
                frm.set_value("to_employee",r.employee)
            })
        }
        $.each(frm.doc.items || [], function (i, d) {
            d.to_main_slip = frm.doc.to_main_slip;
        });
    },
    employee(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.employee = frm.doc.employee;
        });
    },
    to_employee(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.to_employee = frm.doc.to_employee;
        });
    },
    subcontractor(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.subcontractor = frm.doc.subcontractor;
        });
    },
    to_subcontractor(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.to_subcontractor = frm.doc.to_subcontractor;
        });
    },
    project(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.project = frm.doc.project;
        });
    },
    manufacturing_operation(frm) {
        $.each(frm.doc.items || [], function (i, d) {
            d.manufacturing_operation = frm.doc.manufacturing_operation;
        });
    }
})

frappe.ui.form.on("Stock Entry Detail", {
    items_add: function (frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        row.from_job_card = frm.doc.from_job_card;
        row.to_job_card = frm.doc.to_job_card;
        row.inventory_type = frm.doc.inventory_type;
        row.customer = frm.doc._customer;
        row.branch = frm.doc.branch;
        row.department = frm.doc.department;
        row.to_department = frm.doc.to_department;
        row.main_slip = frm.doc.main_slip;
        row.to_main_slip = frm.doc.to_main_slip;
        row.employee = frm.doc.employee;
        row.to_employee = frm.doc.to_employee;
        row.subcontractor = frm.doc.subcontractor
        row.to_subcontractor = frm.doc.to_subcontractor
        row.project = frm.doc.project;
        row.manufacturing_operation = frm.doc.manufacturing_operation
        refresh_field("items");
    }
})

erpnext.stock.select_batch_and_serial_no = (frm, item) => {
	let get_warehouse_type_and_name = (item) => {
		let value = '';
		if(frm.fields_dict.from_warehouse.disp_status === "Write") {
			value = cstr(item.s_warehouse) || '';
			return {
				type: 'Source Warehouse',
				name: value
			};
		} else {
			value = cstr(item.t_warehouse) || '';
			return {
				type: 'Target Warehouse',
				name: value
			};
		}
	}

	if(item && !item.has_serial_no && !item.has_batch_no) return;
	if (frm.doc.purpose === 'Material Receipt') return;

	frappe.require("assets/jewellery_erpnext/js/utils/serial_no_batch_selector.js", function() {
		if (frm.batch_selector?.dialog?.display) return;
		frm.batch_selector = new erpnext.SerialNoBatchSelector({
			frm: frm,
			item: item,
			warehouse_details: get_warehouse_type_and_name(item),
		});
	});
}

erpnext.show_serial_batch_selector = function (frm, d, callback, on_close, show_dialog) {
	let warehouse, receiving_stock, existing_stock;
	if (frm.doc.is_return) {
		if (["Purchase Receipt", "Purchase Invoice"].includes(frm.doc.doctype)) {
			existing_stock = true;
			warehouse = d.warehouse;
		} else if (["Delivery Note", "Sales Invoice"].includes(frm.doc.doctype)) {
			receiving_stock = true;
		}
	} else {
		if (frm.doc.doctype == "Stock Entry") {
			if (frm.doc.purpose == "Material Receipt") {
				receiving_stock = true;
			} else {
				existing_stock = true;
				warehouse = d.s_warehouse;
			}
		} else {
			existing_stock = true;
			warehouse = d.warehouse;
		}
	}

	if (!warehouse) {
		if (receiving_stock) {
			warehouse = ["like", ""];
		} else if (existing_stock) {
			warehouse = ["!=", ""];
		}
	}

	frappe.require("assets/jewellery_erpnext/js/utils/serial_no_batch_selector.js", function() {
		new erpnext.SerialNoBatchSelector({
			frm: frm,
			item: d,
			warehouse_details: {
				type: "Warehouse",
				name: warehouse
			},
			callback: callback,
			on_close: on_close
		}, show_dialog);
	});
}
