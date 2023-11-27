from . import __version__ as app_version

app_name = "jewellery_erpnext"
app_title = "Jewellery Erpnext"
app_publisher = "Nirali"
app_description = "jewellery custom app"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "nirali@ascratech.com"
app_license = "MIT"

app_include_css = "/assets/jewellery_erpnext/css/jewellery.css"

doctype_js = {
	"Quotation"                    : "public/js/doctype_js/quotation.js",
  	"Customer"                     : "public/js/doctype_js/customer.js",
	"BOM"                          : "public/js/doctype_js/bom.js",
	"Work Order"                   : "public/js/doctype_js/work_order.js",
	"Item"                         : "public/js/doctype_js/item.js",
	"Stock Entry"                  : "public/js/doctype_js/stock_entry.js",
	"Operation"                    : "public/js/doctype_js/operation.js",
	"Job Card"                     : "public/js/doctype_js/job_card.js",
	"Sales Order"                  : "public/js/doctype_js/sales_order.js",
	"Manufacturer"                 : "public/js/doctype_js/manufacturer.js",
    "Quality Inspection Template"  : "public/js/doctype_js/quality_inspection_template.js",
    "Supplier"                     : "public/js/doctype_js/supplier.js",
    "Material Request"			   : "public/js/doctype_js/material_request.js"
}

from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry import get_scrap_items_from_job_card, get_bom_scrap_material
StockEntry.get_scrap_items_from_job_card = get_scrap_items_from_job_card
StockEntry.get_bom_scrap_material = get_bom_scrap_material
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
from jewellery_erpnext.jewellery_erpnext.doc_events.work_order import get_work_orders
WorkOrder.get_work_orders = get_work_orders

doc_events = {
	"Quotation": {
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.quotation.validate",
		"on_submit": "jewellery_erpnext.jewellery_erpnext.doc_events.quotation.on_submit",
		"on_cancel": "jewellery_erpnext.jewellery_erpnext.doc_events.quotation.on_cancel",
		"onload":  "jewellery_erpnext.jewellery_erpnext.doc_events.quotation.onload"
	},
	"Sales Order": {
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.sales_order.validate",
		"on_submit": "jewellery_erpnext.jewellery_erpnext.doc_events.sales_order.on_submit",
		"on_cancel": "jewellery_erpnext.jewellery_erpnext.doc_events.sales_order.on_cancel"
	},
	"BOM": {
		"before_validate": "jewellery_erpnext.jewellery_erpnext.doc_events.bom.before_validate",
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.bom.validate",
		"on_update": "jewellery_erpnext.jewellery_erpnext.doc_events.bom.on_update",
		"on_cancel": "jewellery_erpnext.jewellery_erpnext.doc_events.bom.on_cancel",
		"on_submit": "jewellery_erpnext.jewellery_erpnext.doc_events.bom.on_submit"
	},
	"Work Order": {
		"before_save": "jewellery_erpnext.jewellery_erpnext.doc_events.work_order.before_save",
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.work_order.validate",
	},
	"Item": {
		"before_validate": "jewellery_erpnext.jewellery_erpnext.doc_events.item.before_validate",
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.item.validate",
		"before_save": "jewellery_erpnext.jewellery_erpnext.doc_events.item.before_save",
		"on_trash": "jewellery_erpnext.jewellery_erpnext.doc_events.item.on_trash"
	},
	"Item Attribute": {
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.item_attribute.validate"
	},
	"Stock Entry": {
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry.validate",
        "before_submit": "jewellery_erpnext.jewellery_erpnext.doc_events.serial_no.before_submit",
		"on_submit": "jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry.onsubmit",
		"on_cancel": "jewellery_erpnext.jewellery_erpnext.doc_events.stock_entry.on_cancel"
	},
	"Job Card": {
		"onload": "jewellery_erpnext.jewellery_erpnext.doc_events.job_card.onload",
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.job_card.validate",
		"on_submit": "jewellery_erpnext.jewellery_erpnext.doc_events.job_card.onsubmit"
	},
	"Diamond Weight": {
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.diamond_weight.validate"
	},
	"Gemstone Weight": {
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.gemstone_weight.validate"
	},
	"Mould":{
		"autoname": "jewellery_erpnext.jewellery_erpnext.doc_events.mould.autoname",
		"validate": "jewellery_erpnext.jewellery_erpnext.doc_events.mould.validate",
	},
    "Warehouse": {
        "validate": "jewellery_erpnext.jewellery_erpnext.doc_events.warehouse.validate"
	},
    "Purchase Order": {
        "on_cancel": "jewellery_erpnext.jewellery_erpnext.doc_events.purchase_order.on_cancel"
	}

}

override_whitelisted_methods = {
	"erpnext.manufacturing.doctype.job_card.job_card.make_stock_entry": "jewellery_erpnext.jewellery_erpnext.doc_events.job_card.make_stock_entry",
    "erpnext.stock.doctype.material_request.material_request.make_stock_entry": "jewellery_erpnext.jewellery_erpnext.doc_events.material_request.make_stock_entry"
}

fixtures = [
	{
		"dt": "Custom Field", 
		"filters": [["dt", "in", [
            "Stock Entry", "Warehouse", "Quotation Item", "Sales Order Item",
            "Sales Order", "Quotation", "Stock Entry Detail", "Quality Inspection Template",
            "Purchase Order", "Purchase Order Item", "Material Request", "Supplier", "Serial No",
            "Material Request", "Material Request Item", "Item Group"
            ]], ["is_system_generated",'=',0]]
	},
    {
		"dt": "Property Setter", 
		"filters": [["doc_type", "in", [
            "Quality Inspection Template"
            ]], ["is_system_generated",'=',0], ["module","=","Jewellery Erpnext"]]
	},
    {
		"dt": "Stock Entry Type"
	}
]

# from erpnext.stock import get_item_details 
# from jewellery_erpnext.erpnext_override import get_price_list_rate_for
# get_item_details.get_price_list_rate_for = get_price_list_rate_for

# from erpnext.stock.doctype.item_price.item_price import ItemPrice
# from jewellery_erpnext.jewellery_erpnext.doc_events.item_price import check_duplicates
# ItemPrice.check_duplicates = check_duplicates 


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"jewellery_erpnext.auth.validate"
# ]

