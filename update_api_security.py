#!/usr/bin/env python3
"""
Restaurant Management API Security Update Script
================================================

This script helps categorize and update API endpoints with proper authentication
and role-based access control.

Security Categories:
1. PUBLIC - Keep allow_guest=True (login, reset password, etc.)
2. STAFF - Require any restaurant staff role
3. MANAGER - Require Restaurant Manager or higher
4. OWNER - Require Restaurant Owner role
5. ROLE_SPECIFIC - Require specific roles (Kitchen, Cashier, etc.)
"""

import re

# Define API security classifications
API_SECURITY_CONFIG = {
    # PUBLIC APIs - Keep allow_guest=True
    "PUBLIC": {
        "apis": [
            "login",
            "logout", 
            "reset_password",
            "confirm_password_reset",
        ],
        "decorator": "@frappe.whitelist(allow_guest=True)",
        "description": "Public endpoints that don't require authentication"
    },
    
    # STAFF APIs - Any authenticated restaurant staff
    "STAFF": {
        "apis": [
            "get_current_user_info",
            "change_password",
            "get_staff_details",
            "mark_attendance",
            "get_attendance_records",
            "get_menu_items",
            "get_menu_categories",
            "get_orders",
            "get_order_details",
            "get_table_bookings",
            "get_customer_profile",
            "get_loyalty_status",
            "get_kitchen_display_orders",
            "update_kitchen_order_status",
        ],
        "decorator": "@frappe.whitelist()",
        "role_check": "Restaurant Staff",
        "description": "General staff endpoints - requires any restaurant staff role"
    },
    
    # MANAGER APIs - Manager or Owner only
    "MANAGER": {
        "apis": [
            "register_staff",
            "create_staff", 
            "update_staff",
            "delete_staff",
            "get_staff_list",
            "create_menu_item",
            "update_menu_item", 
            "delete_menu_item",
            "create_menu_category",
            "get_daily_operations_report",
            "get_weekly_performance_report",
            "get_inventory_status",
            "get_inventory_valuation_report",
            "create_marketing_campaign",
            "launch_campaign",
            "get_campaign_analytics",
            "approve_advance_payment",
            "get_staff_advances",
            "get_staff_tips",
            "calculate_staff_payroll",
            "auto_distribute_daily_pooled_tips",
        ],
        "decorator": "@frappe.whitelist()",
        "role_check": "Restaurant Manager",
        "description": "Management endpoints - requires Manager or Owner role"
    },
    
    # OWNER APIs - Owner only
    "OWNER": {
        "apis": [
            "delete_staff_permanent",
            "modify_staff_roles",
            "system_settings",
            "backup_data",
            "restore_data",
            "financial_reports",
        ],
        "decorator": "@frappe.whitelist()",
        "role_check": "Restaurant Owner", 
        "description": "Owner-only endpoints - requires Owner role"
    },
    
    # POS/CASHIER APIs - Cashier, Staff, Manager, Owner
    "CASHIER": {
        "apis": [
            "create_order",
            "modify_order", 
            "process_payment",
            "generate_final_receipt",
            "get_dynamic_price",
            "apply_promotion",
            "validate_promotion",
            "record_tips",
            "auto_record_individual_tip",
            "auto_record_pooled_tip",
            "customer_add_tip",
        ],
        "decorator": "@frappe.whitelist()",
        "role_check": "Restaurant Cashier",
        "description": "POS/Cashier endpoints - requires Cashier, Staff, Manager, or Owner role"
    },
    
    # KITCHEN APIs - Kitchen staff, Manager, Owner
    "KITCHEN": {
        "apis": [
            "send_to_kitchen",
            "update_kitchen_order_status", 
            "get_kitchen_display_orders",
            "update_order_status",
            "get_order_modification_history",
        ],
        "decorator": "@frappe.whitelist()",
        "role_check": "Restaurant Kitchen",
        "description": "Kitchen endpoints - requires Kitchen, Manager, or Owner role"
    },
    
    # TABLE/BOOKING APIs - Staff, Manager, Owner
    "BOOKING": {
        "apis": [
            "create_table_booking",
            "update_booking_status", 
            "get_available_tables",
            "get_alternative_time_slots",
            "add_to_waitlist",
            "get_waitlist_position",
            "get_customer_booking_history",
            "analyze_customer_preferences",
            "create_event_booking",
            "update_event_status",
        ],
        "decorator": "@frappe.whitelist()",
        "role_check": "Restaurant Staff", 
        "description": "Table/Booking endpoints - requires Staff, Manager, or Owner role"
    }
}

def generate_role_check_function(role_required):
    """Generate role check function for API"""
    if role_required == "Restaurant Staff":
        # Any restaurant role is sufficient
        return f'''
    # Check authentication and role
    if frappe.session.user == "Guest":
        return {{"success": False, "message": "Authentication required"}}
    
    if not has_permission("{role_required}"):
        return {{"success": False, "message": "Insufficient permissions"}}'''
    
    else:
        return f'''
    # Check authentication and role
    if frappe.session.user == "Guest":
        return {{"success": False, "message": "Authentication required"}}
    
    if not has_permission("{role_required}"):
        return {{"success": False, "message": "Insufficient permissions. {role_required} role required."}}'''

def print_security_summary():
    """Print summary of security changes"""
    print("🔐 RESTAURANT API SECURITY CLASSIFICATION")
    print("=" * 50)
    
    total_apis = 0
    for category, config in API_SECURITY_CONFIG.items():
        print(f"\n📁 {category} ({len(config['apis'])} APIs)")
        print(f"   {config['description']}")
        print(f"   Decorator: {config['decorator']}")
        if 'role_check' in config:
            print(f"   Role Required: {config['role_check']}")
        
        for api in config['apis']:
            print(f"   • {api}")
        
        total_apis += len(config['apis'])
    
    print(f"\n📊 TOTAL APIs to secure: {total_apis}")
    print(f"\n⚠️  CRITICAL: {80-total_apis}+ APIs still need classification!")

def create_api_update_template():
    """Create template for updating API security"""
    template = '''
# Example of updating an API from guest access to role-based:

# BEFORE:
@frappe.whitelist(allow_guest=True)
def some_api():
    """Some API function"""
    try:
        # API logic here
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

# AFTER:
@frappe.whitelist()
def some_api():
    """Some API function"""
    try:
        # Check authentication and role
        if frappe.session.user == "Guest":
            return {"success": False, "message": "Authentication required"}
        
        if not has_permission("Restaurant Staff"):  # or other required role
            return {"success": False, "message": "Insufficient permissions"}
        
        # API logic here
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}
'''
    return template

if __name__ == "__main__":
    print_security_summary()
    print("\n" + "="*50)
    print("📝 UPDATE TEMPLATE:")
    print(create_api_update_template())