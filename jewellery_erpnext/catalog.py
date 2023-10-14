import frappe



# @frappe.whitelist()
# def get_item(item_category=None, item_subcategory=None, setting_type=None):
#     filters = {}
#     if item_category:
#         filters['item_category'] = item_category
#     if item_subcategory:
#         filters['item_subcategory'] = item_subcategory
#     if setting_type:
#         filters['setting_type'] = setting_type  # Add the setting_type filter

#     items = frappe.get_all('Item', filters=filters, fields=['name', 'item_name', 'image', 'item_category', 'item_subcategory', 'setting_type'])

#     # Add sorting based on setting_type
#     if setting_type:
#         items = sorted(items, key=lambda x: x['setting_type'] == setting_type, reverse=True)

#     return items


# @frappe.whitelist()
# def get_bom(item=None):
#     filters = {}
#     if item:
#         filters['item'] = item

#     bomItem = frappe.get_all('BOM', filters=filters, fields=['name', 'item'] )
#     print(bomItem)
#     return bomItem

# @frappe.whitelist()
# def get_item_categories():
#     # Query unique item_category values from the Item Doctype
#     categories = frappe.get_all('Item', distinct=True, fields=['item_category'])
#     return [{'value': category['item_category'], 'label': category['item_category']} for category in categories]



# @frappe.whitelist()
# def get_item_catalog_data():
#     # Fetch item data using Frappe ORM
#     item_data = frappe.get_all(
#         'Item',
#         fields=['name', 'item_name', 'image', 'item_category', 'item_subcategory'],
#         filters={'docstatus': 1}
#     )

#     # Fetch other data from BOM Doctype or other relevant Doctypes
#     # Customize this part based on your data structure

#     return item_data
# backend.py (a custom Frappe app)

# from frappe import _
# @frappe.whitelist()
# def get_items(item_category=None, item_subcategory=None, setting_type=None):
#     filters = {}
#     if item_category:
#         filters["item_category"] = item_category
#     if item_subcategory:
#         filters["item_subcategory"] = item_subcategory
#     if setting_type:
#         filters["setting_type"] = setting_type

#     items = frappe.get_all("Item", filters=filters, fields=["name", "item_name", "item_category", "item_subcategory", "setting_type", "image"])

#     return items

# @frappe.whitelist()
# def fetch_items():
#     args = frappe.local.form_dict  # Get all request arguments
#     item_category = args.get("item_category")
#     item_subcategory = args.get("item_subcategory")
#     setting_type = args.get("setting_type")

#     items = get_items(item_category, item_subcategory, setting_type)

#     return items
# @frappe.whitelist()
# def get_distinct_item_categories():
#     # Query the 'Item' DocType to get distinct item categories
#     categories = frappe.get_all("Item", distinct=True, fields=["item_category"])
#     return [category["item_category"] for category in categories if category["item_category"]]

# # Similar functions for subcategories and setting types

# @frappe.whitelist()
# def get_filter_options():
#     item_categories = get_distinct_item_categories()
#     item_subcategories = get_distinct_item_subcategories()
#     setting_types = get_distinct_setting_types()
    
#     return {
#         "item_categories": item_categories,
#         "item_subcategories": item_subcategories,
#         "setting_types": setting_types
#     }

# @frappe.whitelist()
# def get_filtered_items(item_category=None, item_subcategory=None, setting_type=None):
#     filters = {}
#     if item_category:
#         filters["item_category"] = item_category
#     if item_subcategory:
#         filters["item_subcategory"] = item_subcategory
#     if setting_type:
#         filters["setting_type"] = setting_type

#     items = frappe.get_all("Item", filters=filters, fields=["name", "item_name", "item_category", "item_subcategory", "setting_type", "image"])

#     return items

# @frappe.whitelist()
# def get_distinct_item_subcategories():
#     subcategories = frappe.get_all("Item", distinct=True, fields=["item_subcategory"])
#     return [subcategory.item_subcategory for subcategory in subcategories]

# def get_distinct_setting_types():
#     setting_types = frappe.get_all("Item", distinct=True, fields=["setting_type"])
#     return [stype.setting_type for stype in setting_types]

# Your Python script (item_filters.py)

# import frappe
# from frappe import _

# @frappe.whitelist()
# def get_item_categories():
#     item_categories = frappe.get_all("Item", distinct=True, fields=["item_category"])
#     return [category["item_category"] for category in item_categories]

# Import necessary modules
from frappe import _

@frappe.whitelist()
def get_bom_details_by_item_code(item):
    bom_docs = frappe.get_all("BOM", filters={"item": item}, fields=["item", "item_category", "item_subcategory"])
    return bom_docs

# import frappe
# from frappe import _

# @frappe.whitelist()
# def get_item_details(item_code):
#     try:
#         # Fetch item details
#         item = frappe.get_doc("Item", item_code)
#         item_category = item.item_category
#         item_subcategory = item.item_subcategory
#         item_setting = item.setting_type

#         # Retrieve the BOM for the item where the item matches the specified item code
#         bom = frappe.get_all(
#             "BOM",
#             filters={"item": item_code},
#             fields=["name", "metal_type", "metal_weight"]  # Add other relevant BOM fields here
#         )

#         # Initialize a list to store BOM details
#         bom_details = []

#         # Iterate through the matching BOMs and fetch their details
#         for bom_item in bom:
#             bom_details.append({
#                 "bom_name": bom_item.name,
#                 "metal_type": bom_item.metal_type,
#                 "metal_weight": bom_item.metal_weight,
#                 # Add other relevant BOM fields here
#             })

#         # Return the item details along with a list of matching BOM details
#         return {
#             "item_code": item_code,
#             "item_category": item_category,
#             "item_subcategory": item_subcategory,
#             "item_setting": item_setting,
#             "bom_details": bom_details
#         }
#     except frappe.DoesNotExistError:
#         # Handle the case where the item doesn't exist
#         frappe.throw(f"Item {item_code} not found.")
