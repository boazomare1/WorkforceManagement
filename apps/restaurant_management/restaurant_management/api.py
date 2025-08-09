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
            fields=["name", "staff_id", "full_name", "position", "department", "employment_status", "phone", "email"],
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
            "staff_id": staff_doc.staff_id,
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
            filters["staff_id"] = staff_id
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