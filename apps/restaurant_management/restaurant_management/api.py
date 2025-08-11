import frappe, json
from frappe import _
from frappe.utils import nowdate, getdate, now_datetime
from werkzeug.wrappers import Response

# ——————————————————————————————————————————————————————————————
# Helpers
# ——————————————————————————————————————————————————————————————

def _response(data, status=200, message="Success", code=None, errors=None, meta=None):
    payload = {
        "data": data,
        "status": "success" if status < 400 else "error",
        "message": message,
    }
    if code:
        payload["code"] = code
    if errors:
        payload["errors"] = errors
    if meta:
        payload["meta"] = meta

    # Use default=str so datetime (and other types) become strings
    return Response(
        json.dumps(payload, default=str), status=status, content_type="application/json"
    )

def _error(message, code, status, errors=None, meta=None):
    return _response(
        None, status=status, message=message, code=code, errors=errors, meta=meta
    )

# ============================================================================
# AUTHENTICATION & AUTHORIZATION APIs
# ============================================================================

def get_current_user():
    """Get current authenticated user"""
    return frappe.session.user

def has_permission(role_required, user=None):
    """Check if user has required role"""
    if not user:
        user = get_current_user()
    
    if user == "Administrator":
        return True
    
    user_roles = frappe.get_roles(user)
    
    # Role hierarchy (higher roles include lower role permissions)
    role_hierarchy = {
        "Restaurant Owner": ["Restaurant Manager", "Restaurant Staff", "Restaurant Kitchen", "Restaurant Cashier"],
        "Restaurant Manager": ["Restaurant Staff", "Restaurant Kitchen", "Restaurant Cashier"],
        "Restaurant Kitchen": [],
        "Restaurant Staff": [],
        "Restaurant Cashier": []
    }
    
    # Check if user has the required role or a higher role
    for user_role in user_roles:
        if user_role == role_required:
            return True
        if user_role in role_hierarchy and role_required in role_hierarchy[user_role]:
            return True
    
    return False

@frappe.whitelist(allow_guest=True, methods=["POST"])
def login():
    """Authenticate user and create session"""
    try:
        data = frappe.local.request.get_json() or {}
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return {
                "success": False,
                "message": "Email and password are required"
            }
        
        # Check if user exists and is staff member
        staff = frappe.db.get_value("Restaurant Staff", 
            {"email": email, "employment_status": "Active"}, 
            ["name", "full_name", "position", "department", "email"]
        )
        
        if not staff:
            return {
                "success": False,
                "message": "Invalid credentials or inactive account"
            }
        
        # Authenticate with Frappe
        from frappe.auth import LoginManager
        login_manager = LoginManager()
        login_manager.authenticate(email, password)
        
        if login_manager.user:
            # Get user roles and staff info
            user_roles = frappe.get_roles(email)
            
            return {
                "success": True,
                "message": "Login successful",
                "data": {
                    "user": email,
                    "full_name": staff[1],
                    "position": staff[2],
                    "department": staff[3],
                    "roles": user_roles,
                    "session_id": frappe.session.sid
                }
            }
        else:
            return {
                "success": False,
                "message": "Invalid credentials"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Login failed: {str(e)}"
        }

@frappe.whitelist()
def logout():
    """Logout current user"""
    try:
        frappe.local.login_manager.logout()
        return {
            "success": True,
            "message": "Logged out successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Logout failed: {str(e)}"
        }

@frappe.whitelist()
def get_current_user_info():
    """Get current user information"""
    try:
        user = get_current_user()
        if user == "Guest":
            return {
                "success": False,
                "message": "Not authenticated"
            }
        
        # Get staff information
        staff = frappe.db.get_value("Restaurant Staff", 
            {"email": user}, 
            ["staff_id", "full_name", "position", "department", "employment_status"],
            as_dict=True
        )
        
        if not staff:
            return {
                "success": False,
                "message": "Staff record not found"
            }
        
        return {
            "success": True,
            "data": {
                "email": user,
                "staff_id": staff.staff_id,
                "full_name": staff.full_name,
                "position": staff.position,
                "department": staff.department,
                "roles": frappe.get_roles(user),
                "employment_status": staff.employment_status
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting user info: {str(e)}"
        }

# ——————————————————————————————————————————————————————————————
# Test & Basic APIs
# ——————————————————————————————————————————————————————————————

@frappe.whitelist(allow_guest=True)
def test_api():
    """Test API endpoint"""
    return _response({
        "message": "Restaurant Management API is working!",
        "timestamp": now_datetime().strftime("%Y-%m-%d %H:%M:%S")
    })

@frappe.whitelist(allow_guest=True)
def get_positions():
    """Get list of available positions"""
    positions = [
        "Manager", "Waiter", "Chef", "Kitchen Staff", 
        "Cashier", "Host/Hostess", "Bartender", "Dishwasher"
    ]
    
    return _response(positions)

@frappe.whitelist(allow_guest=True)
def get_departments():
    """Get list of available departments"""
    departments = [
        "Management", "Service", "Kitchen", "Bar", "Support"
    ]
    
    return _response(departments)

# ——————————————————————————————————————————————————————————————
# Staff Management APIs
# ——————————————————————————————————————————————————————————————

@frappe.whitelist(allow_guest=True)
def get_staff_list():
    """Get list of all staff members"""
    try:
        staff_list = frappe.get_all(
            "Restaurant Staff",
            fields=["name", "full_name", "position", "department", "employment_status", "phone", "email"],
            order_by="full_name"
        )
        return _response(staff_list)
    except Exception as e:
        return _error(f"Failed to get staff list: {str(e)}", "STAFF_LIST_ERROR", 500)

@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_staff():
    """Create a new staff member"""
    try:
        data = frappe.local.request.get_json().get("data", {})
        
        # Validate required fields
        required_fields = ["full_name", "position", "department", "phone"]
        for field in required_fields:
            if not data.get(field):
                return _error(f"Missing required field: {field}", "MISSING_FIELD", 400)
        
        # Create staff document
        staff_doc = frappe.get_doc({
            "doctype": "Restaurant Staff",
            **data
        })
        staff_doc.insert(ignore_permissions=True)
        
        return _response({
            "name": staff_doc.name,
            "staff_id": staff_doc.name,
            "message": "Staff member created successfully"
        })
    except Exception as e:
        return _error(f"Failed to create staff: {str(e)}", "CREATE_STAFF_ERROR", 500)

@frappe.whitelist(allow_guest=True)
def get_staff_details(staff_id=None, name=None):
    """Get detailed information about a staff member"""
    try:
        if not staff_id and not name:
            return _error("Provide either staff_id or name", "MISSING_PARAMETER", 400)
        
        filters = {}
        if staff_id:
            filters["name"] = staff_id
        if name:
            filters["name"] = name
            
        staff = frappe.get_all("Restaurant Staff", filters=filters, fields=["*"], limit_page_length=1)
        
        if not staff:
            return _error("Staff member not found", "NOT_FOUND", 404)
            
        return _response(staff[0])
    except Exception as e:
        return _error(f"Failed to get staff details: {str(e)}", "STAFF_DETAILS_ERROR", 500)

# ——————————————————————————————————————————————————————————————
# Menu Management APIs
# ——————————————————————————————————————————————————————————————

@frappe.whitelist(allow_guest=True)
def get_menu_categories():
    """Get list of menu categories"""
    try:
        categories = frappe.get_all(
            "Restaurant Menu Category",
            filters={"is_active": 1},
            fields=["name", "category_name", "category_code", "description", "display_order"],
            order_by="display_order, category_name"
        )
        return _response(categories)
    except Exception as e:
        return _error(f"Failed to get menu categories: {str(e)}", "CATEGORIES_ERROR", 500)

@frappe.whitelist(allow_guest=True)
def get_menu_items(category=None, is_available=None):
    """Get list of menu items"""
    try:
        filters = {}
        if category:
            filters["category"] = category
        if is_available is not None:
            filters["is_available"] = int(is_available)
            
        items = frappe.get_all(
            "Restaurant Menu Item",
            filters=filters,
            fields=["name", "item_code", "item_name", "item_description", "price", "category", "is_available", "is_vegetarian", "is_vegan", "spice_level"],
            order_by="item_name"
        )
        return _response(items)
    except Exception as e:
        return _error(f"Failed to get menu items: {str(e)}", "MENU_ITEMS_ERROR", 500)

@frappe.whitelist(allow_guest=True)
def get_popular_items():
    """Get list of popular menu items"""
    try:
        items = frappe.get_all(
            "Restaurant Menu Item",
            filters={"is_popular": 1, "is_available": 1},
            fields=["name", "item_code", "item_name", "item_description", "price", "category"],
            order_by="item_name"
        )
        return _response(items)
    except Exception as e:
        return _error(f"Failed to get popular items: {str(e)}", "POPULAR_ITEMS_ERROR", 500)

@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_menu_item():
    """Create a new menu item"""
    try:
        data = frappe.local.request.get_json().get("data", {})
        
        # Validate required fields
        required_fields = ["item_name", "price", "category"]
        for field in required_fields:
            if not data.get(field):
                return _error(f"Missing required field: {field}", "MISSING_FIELD", 400)
        
        # Create menu item document
        item_doc = frappe.get_doc({
            "doctype": "Restaurant Menu Item",
            **data
        })
        item_doc.insert(ignore_permissions=True)
        
        return _response({
            "name": item_doc.name,
            "item_code": item_doc.item_code,
            "message": "Menu item created successfully"
        })
    except Exception as e:
        return _error(f"Failed to create menu item: {str(e)}", "CREATE_ITEM_ERROR", 500)

# ——————————————————————————————————————————————————————————————
# Order Management APIs
# ——————————————————————————————————————————————————————————————

@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_order():
    """Create a new order"""
    try:
        data = frappe.local.request.get_json().get("data", {})
        
        # Validate required fields
        if not data.get("items") or not isinstance(data["items"], list):
            return _error("Order must contain items list", "MISSING_ITEMS", 400)
        
        # Create order document
        order_doc = frappe.get_doc({
            "doctype": "Restaurant Order",
            "order_type": data.get("order_type", "Dine-in"),
            "table_number": data.get("table_number"),
            "customer_name": data.get("customer_name"),
            "customer_phone": data.get("customer_phone"),
            "items": data["items"]
        })
        order_doc.insert(ignore_permissions=True)
        
        return _response({
            "name": order_doc.name,
            "order_id": order_doc.order_id,
            "message": "Order created successfully"
        })
    except Exception as e:
        return _error(f"Failed to create order: {str(e)}", "CREATE_ORDER_ERROR", 500)

@frappe.whitelist(allow_guest=True)
def get_orders(status=None, order_type=None):
    """Get list of orders"""
    try:
        filters = {}
        if status:
            filters["order_status"] = status
        if order_type:
            filters["order_type"] = order_type
            
        orders = frappe.get_all(
            "Restaurant Order",
            filters=filters,
            fields=["name", "order_id", "order_type", "table_number", "customer_name", "order_status", "total_amount", "order_date", "order_time"],
            order_by="creation desc"
        )
        return _response(orders)
    except Exception as e:
        return _error(f"Failed to get orders: {str(e)}", "ORDERS_ERROR", 500)

@frappe.whitelist(allow_guest=True)
def get_order_details(order_id=None, name=None):
    """Get detailed information about an order"""
    try:
        if not order_id and not name:
            return _error("Provide either order_id or name", "MISSING_PARAMETER", 400)
        
        filters = {}
        if order_id:
            filters["order_id"] = order_id
        if name:
            filters["name"] = name
            
        orders = frappe.get_all("Restaurant Order", filters=filters, fields=["*"], limit_page_length=1)
        
        if not orders:
            return _error("Order not found", "NOT_FOUND", 404)
            
        return _response(orders[0])
    except Exception as e:
        return _error(f"Failed to get order details: {str(e)}", "ORDER_DETAILS_ERROR", 500)

@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_order_status():
    """Update order status"""
    try:
        data = frappe.local.request.get_json().get("data", {})
        
        if not data.get("name") or not data.get("order_status"):
            return _error("Missing name or order_status", "MISSING_PARAMETER", 400)
        
        order_doc = frappe.get_doc("Restaurant Order", data["name"])
        order_doc.order_status = data["order_status"]
        order_doc.save(ignore_permissions=True)
        
        return _response({
            "name": order_doc.name,
            "order_status": order_doc.order_status,
            "message": "Order status updated successfully"
        })
    except Exception as e:
        return _error(f"Failed to update order status: {str(e)}", "UPDATE_STATUS_ERROR", 500)

# ——————————————————————————————————————————————————————————————
# Payment APIs
# ——————————————————————————————————————————————————————————————

@frappe.whitelist(allow_guest=True)
def get_payment_methods():
    """Get list of available payment methods"""
    payment_methods = [
        {"code": "cash", "name": "Cash", "description": "Cash payment"},
        {"code": "card", "name": "Credit/Debit Card", "description": "Card payment"},
        {"code": "mobile_money", "name": "Mobile Money", "description": "Mobile money transfer"},
        {"code": "bank_transfer", "name": "Bank Transfer", "description": "Direct bank transfer"},
        {"code": "digital_wallet", "name": "Digital Wallet", "description": "Digital wallet payment"}
    ]
    return _response(payment_methods)

@frappe.whitelist(allow_guest=True, methods=["POST"])
def process_payment():
    """Process payment for an order"""
    try:
        data = frappe.local.request.get_json().get("data", {})
        
        required_fields = ["order_name", "payment_method", "amount_paid"]
        for field in required_fields:
            if not data.get(field):
                return _error(f"Missing required field: {field}", "MISSING_FIELD", 400)
        
        order_doc = frappe.get_doc("Restaurant Order", data["order_name"])
        order_doc.payment_method = data["payment_method"]
        order_doc.amount_paid = data["amount_paid"]
        order_doc.payment_status = "Paid" if data["amount_paid"] >= order_doc.total_amount else "Partial"
        order_doc.save(ignore_permissions=True)
        
        return _response({
            "order_id": order_doc.order_id,
            "payment_status": order_doc.payment_status,
            "amount_paid": order_doc.amount_paid,
            "change_amount": order_doc.amount_paid - order_doc.total_amount if order_doc.amount_paid > order_doc.total_amount else 0,
            "message": "Payment processed successfully"
        })
    except Exception as e:
        return _error(f"Failed to process payment: {str(e)}", "PAYMENT_ERROR", 500)

# ——————————————————————————————————————————————————————————————
# Reports APIs
# ——————————————————————————————————————————————————————————————

@frappe.whitelist(allow_guest=True)
def get_sales_report(start_date=None, end_date=None):
    """Get sales report for a date range"""
    try:
        if not start_date:
            start_date = nowdate()
        if not end_date:
            end_date = nowdate()
            
        orders = frappe.get_all(
            "Restaurant Order",
            filters={
                "order_date": ["between", [start_date, end_date]],
                "payment_status": "Paid"
            },
            fields=["name", "order_id", "total_amount", "order_date", "order_type"],
            order_by="order_date desc"
        )
        
        total_sales = sum(order.total_amount for order in orders)
        total_orders = len(orders)
        
        return _response({
            "period": {"start_date": start_date, "end_date": end_date},
            "summary": {
                "total_sales": total_sales,
                "total_orders": total_orders,
                "average_order_value": total_sales / total_orders if total_orders > 0 else 0
            },
            "orders": orders
        })
    except Exception as e:
        return _error(f"Failed to get sales report: {str(e)}", "SALES_REPORT_ERROR", 500)

@frappe.whitelist(allow_guest=True)
def get_order_status_summary():
    """Get summary of order statuses"""
    try:
        orders = frappe.get_all(
            "Restaurant Order",
            fields=["order_status"],
            order_by="creation desc"
        )
        
        status_counts = {}
        for order in orders:
            status = order.order_status or "Pending"
            status_counts[status] = status_counts.get(status, 0) + 1
            
        return _response({
            "total_orders": len(orders),
            "status_breakdown": status_counts
        })
    except Exception as e:
        return _error(f"Failed to get order status summary: {str(e)}", "STATUS_SUMMARY_ERROR", 500) 

# ——————————————————————————————————————————————————————————————



def get_role_for_position(position):
    """Get the appropriate role for a staff position"""
    role_mapping = {
        "Restaurant Owner": "Restaurant Owner",
        "Manager": "Restaurant Manager", 
        "Chef": "Restaurant Kitchen",
        "Kitchen Staff": "Restaurant Kitchen",
        "Waiter": "Restaurant Staff",
        "Waitress": "Restaurant Staff",
        "Cashier": "Restaurant Cashier",
        "Host": "Restaurant Staff",
        "Bartender": "Restaurant Staff"
    }
    
    return role_mapping.get(position, "Restaurant Staff")

# —————————————————————————————————————————————————————————————— 