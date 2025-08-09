# -*- coding: utf-8 -*-
"""
Configuration for docs
"""

# source_link = "https://github.com/[org_name]/restaurant_management"
# docs_base_url = "https://[org_name].github.io/restaurant_management"
# headline = "App that does everything"
# sub_heading = "Yes, you got that right the first time, everything"

def get_context(context):
	context.brand_html = "Restaurant Management"

# API Whitelist Configuration
app_include_js = [
	"assets/restaurant_management/js/restaurant_management.js"
]

app_include_css = [
	"assets/restaurant_management/css/restaurant_management.css"
]

# Whitelist API methods for restaurant management
app_whitelisted_methods = [
	"restaurant_management.api.get_positions",
	"restaurant_management.api.get_departments",
	"restaurant_management.api.get_staff",
	"restaurant_management.api.create_staff",
	"restaurant_management.api.get_menu_items",
	"restaurant_management.api.create_menu_item",
	"restaurant_management.api.get_popular_items",
	"restaurant_management.api.get_chef_specials",
	"restaurant_management.api.create_menu_category",
	"restaurant_management.api.get_menu_categories",
	"restaurant_management.api.create_order",
	"restaurant_management.api.get_orders",
	"restaurant_management.api.get_order_details",
	"restaurant_management.api.update_order_status",
	"restaurant_management.api.process_payment",
	"restaurant_management.api.get_payment_methods",
	"restaurant_management.api.get_sales_report",
	"restaurant_management.api.get_order_status_summary",
	"restaurant_management.api.get_staff_stats"
] 