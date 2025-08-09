import frappe
from frappe import _
from frappe.utils import nowdate, getdate, now_datetime
import json

# ============================================================================
# STAFF MANAGEMENT APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def create_staff(staff_data):
    """Create a new staff member"""
    try:
        data = json.loads(staff_data) if isinstance(staff_data, str) else staff_data
        
        # Create new staff document
        staff = frappe.get_doc({
            "doctype": "Restaurant Staff",
            "full_name": data.get("full_name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "date_of_birth": data.get("date_of_birth"),
            "gender": data.get("gender"),
            "address": data.get("address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "postal_code": data.get("postal_code"),
            "emergency_contact_name": data.get("emergency_contact_name"),
            "emergency_contact_phone": data.get("emergency_contact_phone"),
            "position": data.get("position"),
            "department": data.get("department"),
            "hire_date": data.get("hire_date"),
            "base_hourly_rate": data.get("base_hourly_rate"),
            "weekend_rate": data.get("weekend_rate"),
            "holiday_rate": data.get("holiday_rate"),
            "tax_id": data.get("tax_id"),
            "bank_account": data.get("bank_account"),
            "notes": data.get("notes")
        })
        
        staff.insert()
        
        return {
            "success": True,
            "message": f"Staff member {staff.full_name} created successfully",
            "data": {
                "staff_id": staff.staff_id,
                "name": staff.name,
                "full_name": staff.full_name,
                "email": staff.email
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating staff: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_staff(staff_id=None):
    """Get staff member(s)"""
    try:
        if staff_id:
            # Get specific staff member
            staff = frappe.get_doc("Restaurant Staff", staff_id)
            return {
                "success": True,
                "data": {
                    "staff_id": staff.staff_id,
                    "name": staff.name,
                    "full_name": staff.full_name,
                    "email": staff.email,
                    "phone": staff.phone,
                    "position": staff.position,
                    "department": staff.department,
                    "base_hourly_rate": staff.base_hourly_rate,
                    "overtime_rate": staff.overtime_rate,
                    "employment_status": staff.employment_status,
                    "face_registered": staff.face_registered,
                    "hire_date": staff.hire_date
                }
            }
        else:
            # Get all active staff
            staff_list = frappe.get_all("Restaurant Staff", 
                filters={"employment_status": "Active"},
                fields=["name", "staff_id", "full_name", "email", "phone", 
                        "position", "department", "base_hourly_rate", "face_registered"])
            
            return {
                "success": True,
                "data": staff_list
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving staff: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def update_staff(staff_id, update_data):
    """Update staff member"""
    try:
        data = json.loads(update_data) if isinstance(update_data, str) else update_data
        
        staff = frappe.get_doc("Restaurant Staff", staff_id)
        
        # Update fields
        for field, value in data.items():
            if hasattr(staff, field):
                setattr(staff, field, value)
        
        staff.save()
        
        return {
            "success": True,
            "message": f"Staff member {staff.full_name} updated successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating staff: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def delete_staff(staff_id):
    """Delete staff member (soft delete by setting status to Terminated)"""
    try:
        staff = frappe.get_doc("Restaurant Staff", staff_id)
        staff.employment_status = "Terminated"
        staff.save()
        
        return {
            "success": True,
            "message": f"Staff member {staff.full_name} terminated successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error terminating staff: {str(e)}"
        }

# ============================================================================
# PAYROLL APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def calculate_payroll(staff_id, start_date, end_date):
    """Calculate payroll for a staff member"""
    try:
        staff = frappe.get_doc("Restaurant Staff", staff_id)
        payroll_data = staff.calculate_payroll(start_date, end_date)
        
        return {
            "success": True,
            "data": payroll_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error calculating payroll: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_payroll_report(start_date, end_date, department=None):
    """Get payroll report for all staff or by department"""
    try:
        filters = {"employment_status": "Active"}
        if department:
            filters["department"] = department
        
        staff_list = frappe.get_all("Restaurant Staff", filters=filters)
        payroll_report = []
        
        for staff in staff_list:
            staff_doc = frappe.get_doc("Restaurant Staff", staff.name)
            payroll_data = staff_doc.calculate_payroll(start_date, end_date)
            payroll_report.append(payroll_data)
        
        # Calculate totals
        total_hours = sum(item["total_hours"] for item in payroll_report)
        total_pay = sum(item["total_pay"] for item in payroll_report)
        
        return {
            "success": True,
            "data": {
                "payroll_items": payroll_report,
                "summary": {
                    "total_staff": len(payroll_report),
                    "total_hours": total_hours,
                    "total_pay": total_pay,
                    "period": f"{start_date} to {end_date}"
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating payroll report: {str(e)}"
        }

# ============================================================================
# FACE RECOGNITION APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def register_face(staff_id, face_encoding):
    """Register face encoding for staff member"""
    try:
        staff = frappe.get_doc("Restaurant Staff", staff_id)
        staff.face_encoding = face_encoding
        staff.face_registered = 1
        staff.save()
        
        return {
            "success": True,
            "message": f"Face registered successfully for {staff.full_name}",
            "data": {
                "staff_id": staff.staff_id,
                "full_name": staff.full_name,
                "face_registered": staff.face_registered
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error registering face: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def identify_staff_by_face(face_encoding):
    """Identify staff member by face encoding"""
    try:
        staff = frappe.get_all("Restaurant Staff", 
            filters={"face_encoding": face_encoding, "employment_status": "Active"},
            fields=["name", "staff_id", "full_name", "position"])
        
        if staff:
            return {
                "success": True,
                "data": staff[0]
            }
        else:
            return {
                "success": False,
                "message": "No staff member found with this face encoding"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error identifying staff: {str(e)}"
        }

# ============================================================================
# ATTENDANCE APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def mark_attendance(staff_id, action="check_in"):
    """Mark attendance for staff member"""
    try:
        staff = frappe.get_doc("Restaurant Staff", staff_id)
        current_time = now_datetime()
        current_date = nowdate()
        
        # Check if attendance record exists for today
        existing_attendance = frappe.get_all("Restaurant Attendance", 
            filters={"staff_id": staff_id, "date": current_date},
            limit=1)
        
        if existing_attendance:
            # Update existing record
            attendance = frappe.get_doc("Restaurant Attendance", existing_attendance[0].name)
            if action == "check_out" and not attendance.check_out_time:
                attendance.check_out_time = current_time
                attendance.save()
                message = f"Check-out recorded for {staff.full_name}"
            elif action == "check_in" and not attendance.check_in_time:
                attendance.check_in_time = current_time
                attendance.save()
                message = f"Check-in recorded for {staff.full_name}"
            else:
                return {
                    "success": False,
                    "message": f"Attendance already marked for {action}"
                }
        else:
            # Create new attendance record
            attendance = frappe.get_doc({
                "doctype": "Restaurant Attendance",
                "staff_id": staff_id,
                "date": current_date,
                "check_in_time": current_time if action == "check_in" else None,
                "check_out_time": current_time if action == "check_out" else None
            })
            attendance.insert()
            message = f"Check-in recorded for {staff.full_name}"
        
        return {
            "success": True,
            "message": message,
            "data": {
                "staff_id": staff.staff_id,
                "staff_name": staff.full_name,
                "action": action,
                "time": current_time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error marking attendance: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_attendance_report(staff_id=None, start_date=None, end_date=None):
    """Get attendance report"""
    try:
        filters = {}
        
        if staff_id:
            filters["staff_id"] = staff_id
        if start_date:
            filters["date"] = [">=", start_date]
        if end_date:
            filters["date"] = ["<=", end_date]
        
        attendance_records = frappe.get_all("Restaurant Attendance", 
            filters=filters,
            fields=["*"],
            order_by="date desc, check_in_time desc")
        
        return {
            "success": True,
            "data": attendance_records
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving attendance: {str(e)}"
        }

# ============================================================================
# UTILITY APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def get_positions():
    """Get list of available positions"""
    positions = [
        "Manager", "Waiter", "Chef", "Kitchen Staff", 
        "Cashier", "Host/Hostess", "Bartender", "Dishwasher"
    ]
    
    return {
        "success": True,
        "data": positions
    }

@frappe.whitelist(allow_guest=True)
def get_departments():
    """Get list of available departments"""
    departments = [
        "Management", "Service", "Kitchen", "Bar", "Support"
    ]
    
    return {
        "success": True,
        "data": departments
    }

@frappe.whitelist(allow_guest=True)
def get_order_types():
    """Get list of available order types"""
    order_types = [
        "Dine In", "Takeaway", "Delivery", "Catering"
    ]
    
    return {
        "success": True,
        "data": order_types
    }

@frappe.whitelist(allow_guest=True)
def get_order_statuses():
    """Get list of available order statuses"""
    order_statuses = [
        "Pending", "Confirmed", "Preparing", "Ready", "Served", "Completed", "Cancelled"
    ]
    
    return {
        "success": True,
        "data": order_statuses
    }

@frappe.whitelist(allow_guest=True)
def get_payment_methods():
    """Get list of available payment methods"""
    payment_methods = [
        "Cash", "Credit Card", "Debit Card", "Mobile Money", 
        "Bank Transfer", "Digital Wallet"
    ]
    
    return {
        "success": True,
        "data": payment_methods
    }

@frappe.whitelist(allow_guest=True)
def get_spice_levels():
    """Get list of available spice levels"""
    spice_levels = [
        "Mild", "Medium", "Hot", "Extra Hot"
    ]
    
    return {
        "success": True,
        "data": spice_levels
    }

@frappe.whitelist(allow_guest=True)
def get_employment_statuses():
    """Get list of available employment statuses"""
    employment_statuses = [
        "Active", "Inactive", "Terminated", "On Leave"
    ]
    
    return {
        "success": True,
        "data": employment_statuses
    }

@frappe.whitelist(allow_guest=True)
def get_genders():
    """Get list of available gender options"""
    genders = [
        "Male", "Female", "Other", "Prefer not to say"
    ]
    
    return {
        "success": True,
        "data": genders
    }

@frappe.whitelist(allow_guest=True)
def get_discount_types():
    """Get list of available discount types"""
    discount_types = [
        "Fixed Amount", "Percentage", "None"
    ]
    
    return {
        "success": True,
        "data": discount_types
    }

# ============================================================================
# MENU MANAGEMENT APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def create_menu_item(item_data):
    """Create a new menu item"""
    try:
        data = json.loads(item_data) if isinstance(item_data, str) else item_data
        
        # Create new menu item document
        item = frappe.get_doc({
            "doctype": "Restaurant Menu Item",
            "item_name": data.get("item_name"),
            "item_description": data.get("item_description"),
            "price": data.get("price"),
            "cost_price": data.get("cost_price"),
            "category": data.get("category"),
            "subcategory": data.get("subcategory"),
            "is_vegetarian": data.get("is_vegetarian", 0),
            "is_vegan": data.get("is_vegan", 0),
            "spice_level": data.get("spice_level", "Mild"),
            "preparation_time": data.get("preparation_time", 15),
            "is_popular": data.get("is_popular", 0),
            "is_chef_special": data.get("is_chef_special", 0),
            "tax_rate": data.get("tax_rate", 0),
            "allergens": data.get("allergens"),
            "nutritional_info": data.get("nutritional_info"),
            "cooking_instructions": data.get("cooking_instructions"),
            "serving_suggestions": data.get("serving_suggestions"),
            "notes": data.get("notes")
        })
        
        item.insert()
        
        return {
            "success": True,
            "message": f"Menu item {item.item_name} created successfully",
            "data": {
                "item_code": item.item_code,
                "name": item.name,
                "item_name": item.item_name,
                "price": item.price
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating menu item: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_menu_items(category=None, is_available=True):
    """Get menu items with optional filters"""
    try:
        filters = {"is_available": is_available}
        
        if category:
            filters["category"] = category
        
        menu_items = frappe.get_all("Restaurant Menu Item", 
            filters=filters,
            fields=["name", "item_code", "item_name", "item_description", "price", 
                    "category", "is_vegetarian", "is_vegan", "spice_level", "preparation_time", "item_image"])
        
        return {
            "success": True,
            "data": menu_items
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving menu items: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_popular_items():
    """Get popular menu items"""
    try:
        popular_items = frappe.get_all("Restaurant Menu Item", 
            filters={"is_popular": 1, "is_available": 1},
            fields=["name", "item_code", "item_name", "item_description", "price", 
                    "category", "item_image"],
            order_by="modified desc",
            limit=10)
        
        return {
            "success": True,
            "data": popular_items
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving popular items: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_chef_specials():
    """Get chef special menu items"""
    try:
        chef_specials = frappe.get_all("Restaurant Menu Item", 
            filters={"is_chef_special": 1, "is_available": 1},
            fields=["name", "item_code", "item_name", "item_description", "price", 
                    "category", "item_image"],
            order_by="modified desc")
        
        return {
            "success": True,
            "data": chef_specials
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving chef specials: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def create_menu_category(category_data):
    """Create a new menu category"""
    try:
        data = json.loads(category_data) if isinstance(category_data, str) else category_data
        
        # Create new category document
        category = frappe.get_doc({
            "doctype": "Restaurant Menu Category",
            "category_name": data.get("category_name"),
            "description": data.get("description"),
            "parent_category": data.get("parent_category"),
            "display_order": data.get("display_order", 0),
            "color_code": data.get("color_code"),
            "notes": data.get("notes")
        })
        
        category.insert()
        
        return {
            "success": True,
            "message": f"Category {category.category_name} created successfully",
            "data": {
                "category_code": category.category_code,
                "name": category.name,
                "category_name": category.category_name
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating category: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_menu_categories():
    """Get all menu categories"""
    try:
        categories = frappe.get_all("Restaurant Menu Category", 
            filters={"is_active": 1},
            fields=["name", "category_code", "category_name", "description", 
                    "parent_category", "display_order", "color_code"],
            order_by="display_order, category_name")
        
        return {
            "success": True,
            "data": categories
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving categories: {str(e)}"
        }

# ============================================================================
# ORDER MANAGEMENT APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def create_order(order_data):
    """Create a new restaurant order"""
    try:
        data = json.loads(order_data) if isinstance(order_data, str) else order_data
        
        # Create new order document
        order = frappe.get_doc({
            "doctype": "Restaurant Order",
            "order_type": data.get("order_type", "Dine In"),
            "table_number": data.get("table_number"),
            "waiter": data.get("waiter"),
            "customer_name": data.get("customer_name"),
            "customer_phone": data.get("customer_phone"),
            "customer_email": data.get("customer_email"),
            "delivery_address": data.get("delivery_address"),
            "special_instructions": data.get("special_instructions"),
            "items": data.get("items", []),
            "discount_type": data.get("discount_type", "Fixed Amount"),
            "discount_percentage": data.get("discount_percentage", 0),
            "payment_method": data.get("payment_method"),
            "amount_paid": data.get("amount_paid", 0)
        })
        
        order.insert()
        
        return {
            "success": True,
            "message": f"Order {order.order_id} created successfully",
            "data": {
                "order_id": order.order_id,
                "name": order.name,
                "total_amount": order.total_amount
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating order: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_orders(filters=None):
    """Get orders with optional filters"""
    try:
        if filters:
            filters = json.loads(filters) if isinstance(filters, str) else filters
        else:
            filters = {}
        
        orders = frappe.get_all("Restaurant Order", 
            filters=filters,
            fields=["name", "order_id", "order_type", "customer_name", "order_date", 
                    "order_time", "total_amount", "payment_status", "order_status"],
            order_by="creation desc")
        
        return {
            "success": True,
            "data": orders
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving orders: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_order_details(order_id):
    """Get detailed order information"""
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        # Get order items
        items = []
        for item in order.items:
            items.append({
                "menu_item": item.menu_item,
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
                "tax_amount": item.tax_amount,
                "total_amount": item.total_amount,
                "special_instructions": item.special_instructions
            })
        
        order_data = {
            "order_id": order.order_id,
            "order_type": order.order_type,
            "table_number": order.table_number,
            "waiter": order.waiter,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_email": order.customer_email,
            "delivery_address": order.delivery_address,
            "special_instructions": order.special_instructions,
            "subtotal": order.subtotal,
            "tax_amount": order.tax_amount,
            "discount_amount": order.discount_amount,
            "delivery_fee": order.delivery_fee,
            "total_amount": order.total_amount,
            "payment_status": order.payment_status,
            "payment_method": order.payment_method,
            "amount_paid": order.amount_paid,
            "change_amount": order.change_amount,
            "order_status": order.order_status,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "items": items
        }
        
        return {
            "success": True,
            "data": order_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving order details: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def update_order_status(order_id, new_status):
    """Update order status"""
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        order.order_status = new_status
        
        if new_status == "Completed":
            order.completion_time = now_datetime()
        
        order.save()
        
        return {
            "success": True,
            "message": f"Order status updated to {new_status}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating order status: {str(e)}"
        }

# ============================================================================
# PAYMENT APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def process_payment(order_id, payment_data):
    """Process payment for an order"""
    try:
        data = json.loads(payment_data) if isinstance(payment_data, str) else payment_data
        
        order = frappe.get_doc("Restaurant Order", order_id)
        order.payment_method = data.get("payment_method")
        order.amount_paid = data.get("amount_paid")
        order.payment_reference = data.get("payment_reference")
        
        order.save()
        
        return {
            "success": True,
            "message": f"Payment processed successfully",
            "data": {
                "change_amount": order.change_amount,
                "payment_status": order.payment_status
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing payment: {str(e)}"
        }



# ============================================================================
# REPORTS APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def get_sales_report(start_date, end_date):
    """Get sales report for a date range"""
    try:
        orders = frappe.get_all("Restaurant Order", 
            filters={
                "order_date": [">=", start_date],
                "order_date": ["<=", end_date],
                "order_status": ["!=", "Cancelled"]
            },
            fields=["order_id", "order_type", "customer_name", "order_date", 
                    "total_amount", "payment_status", "order_status"])
        
        total_sales = sum(order.total_amount for order in orders)
        total_orders = len(orders)
        
        return {
            "success": True,
            "data": {
                "orders": orders,
                "summary": {
                    "total_sales": total_sales,
                    "total_orders": total_orders,
                    "average_order_value": total_sales / total_orders if total_orders > 0 else 0,
                    "period": f"{start_date} to {end_date}"
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating sales report: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_order_status_summary():
    """Get summary of order statuses"""
    try:
        status_counts = {}
        statuses = ["Pending", "Confirmed", "Preparing", "Ready", "Served", "Completed", "Cancelled"]
        
        for status in statuses:
            count = frappe.db.count("Restaurant Order", filters={"order_status": status})
            status_counts[status] = count
        
        return {
            "success": True,
            "data": status_counts
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting order status summary: {str(e)}"
        }

# ============================================================================
# UTILITY APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def get_staff_stats():
    """Get staff statistics"""
    try:
        total_staff = frappe.db.count("Restaurant Staff", filters={"employment_status": "Active"})
        staff_by_position = frappe.get_all("Restaurant Staff", 
            filters={"employment_status": "Active"},
            fields=["position"],
            group_by="position")
        
        position_stats = {}
        for item in staff_by_position:
            position = item.position
            if position not in position_stats:
                position_stats[position] = 0
            position_stats[position] += 1
        
        return {
            "success": True,
            "data": {
                "total_active_staff": total_staff,
                "staff_by_position": position_stats
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting staff stats: {str(e)}"
        } 