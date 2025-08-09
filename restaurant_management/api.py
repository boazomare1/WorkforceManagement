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
def modify_order(order_id, modifications):
    """Modify existing order - add/remove items, change quantities"""
    try:
        data = json.loads(modifications) if isinstance(modifications, str) else modifications
        
        order = frappe.get_doc("Restaurant Order", order_id)
        
        # Check if order can be modified
        if order.order_status in ["Completed", "Cancelled"]:
            return {
                "success": False,
                "message": "Cannot modify completed or cancelled orders"
            }
        
        # Track modifications for history
        modification_log = {
            "timestamp": frappe.utils.now(),
            "action": data.get("action"),  # "add_item", "remove_item", "change_quantity", "change_pricing"
            "details": data.get("details", {}),
            "staff_member": data.get("staff_member"),
            "reason": data.get("reason", "Customer request")
        }
        
        # Handle different modification types
        action = data.get("action")
        
        if action == "add_item":
            # Add new item to order
            new_item = {
                "item_name": data["item_name"],
                "quantity": data["quantity"],
                "unit_price": data["unit_price"],
                "special_instructions": data.get("special_instructions", ""),
                "pricing_context": data.get("pricing_context", "standard")  # VIP, happy_hour, etc.
            }
            order.append("items", new_item)
            
        elif action == "remove_item":
            # Remove item from order
            items_to_remove = []
            for i, item in enumerate(order.items):
                if item.item_name == data["item_name"]:
                    items_to_remove.append(i)
                    break
            
            for i in reversed(items_to_remove):
                order.items.pop(i)
                
        elif action == "change_quantity":
            # Update item quantity
            for item in order.items:
                if item.item_name == data["item_name"]:
                    item.quantity = data["new_quantity"]
                    break
                    
        elif action == "apply_pricing_context":
            # Apply VIP/special pricing to entire order
            pricing_context = data["pricing_context"]  # "vip", "happy_hour", "loyalty_discount"
            
            for item in order.items:
                item.pricing_context = pricing_context
                # Recalculate price based on context
                item.unit_price = get_dynamic_price(item.item_name, pricing_context, data.get("table_type"))
        
        # Add modification to history
        if not hasattr(order, 'modification_history'):
            order.modification_history = []
        order.modification_history.append(modification_log)
        
        # Recalculate totals
        order.save()
        
        return {
            "success": True,
            "message": f"Order {order.order_id} modified successfully",
            "data": {
                "order_id": order.order_id,
                "total_amount": order.total_amount,
                "modification_count": len(order.modification_history) if hasattr(order, 'modification_history') else 0
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error modifying order: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_dynamic_price(item_name, pricing_context=None, table_type=None):
    """Get dynamic pricing based on context (VIP room, time of day, customer type)"""
    try:
        # Get base price from menu item
        base_price = frappe.db.get_value("Restaurant Menu Item", item_name, "price")
        
        if not base_price:
            return 0
            
        # Apply pricing multipliers based on context
        multiplier = 1.0
        
        if pricing_context == "vip":
            multiplier = 1.3  # 30% premium for VIP
        elif pricing_context == "happy_hour":
            multiplier = 0.8  # 20% discount for happy hour
        elif pricing_context == "loyalty_discount":
            multiplier = 0.9  # 10% loyalty discount
        elif pricing_context == "group_booking":
            multiplier = 0.95  # 5% group discount
            
        # Table-based pricing
        if table_type == "private_dining":
            multiplier *= 1.15  # 15% premium for private dining
        elif table_type == "terrace":
            multiplier *= 1.1   # 10% premium for terrace seating
            
        # Time-based pricing (you can expand this)
        current_hour = frappe.utils.nowtime().hour
        if current_hour >= 18 and current_hour <= 21:  # Dinner rush
            multiplier *= 1.05  # 5% dinner rush premium
            
        final_price = base_price * multiplier
        
        return round(final_price, 2)
        
    except Exception as e:
        return base_price or 0

@frappe.whitelist(allow_guest=True)
def generate_final_receipt(order_id):
    """Generate final receipt with all modifications included"""
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        # Get modification history
        modifications = getattr(order, 'modification_history', [])
        
        receipt_data = {
            "order_id": order.order_id,
            "customer_name": order.customer_name,
            "table_number": order.table_number,
            "waiter": order.waiter,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "items": [
                {
                    "name": item.item_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total": item.quantity * item.unit_price,
                    "special_instructions": getattr(item, 'special_instructions', ''),
                    "pricing_context": getattr(item, 'pricing_context', 'standard')
                } for item in order.items
            ],
            "subtotal": order.subtotal,
            "discount_amount": order.discount_amount,
            "tax_amount": order.tax_amount,
            "total_amount": order.total_amount,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "modifications_made": len(modifications),
            "final_receipt": True,
            "receipt_timestamp": frappe.utils.now()
        }
        
        return {
            "success": True,
            "data": receipt_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating receipt: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_order_modification_history(order_id):
    """Get complete modification history for an order"""
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        modifications = getattr(order, 'modification_history', [])
        
        return {
            "success": True,
            "data": {
                "order_id": order.order_id,
                "modification_count": len(modifications),
                "modifications": modifications
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving modification history: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_pricing_contexts():
    """Get available pricing contexts/tiers"""
    pricing_contexts = [
        {
            "code": "standard",
            "name": "Standard Pricing",
            "multiplier": 1.0,
            "description": "Regular menu prices"
        },
        {
            "code": "vip",
            "name": "VIP Room",
            "multiplier": 1.3,
            "description": "30% premium for VIP experience"
        },
        {
            "code": "happy_hour",
            "name": "Happy Hour",
            "multiplier": 0.8,
            "description": "20% discount during happy hours"
        },
        {
            "code": "loyalty_discount",
            "name": "Loyalty Member",
            "multiplier": 0.9,
            "description": "10% discount for loyalty members"
        },
        {
            "code": "group_booking",
            "name": "Group Booking",
            "multiplier": 0.95,
            "description": "5% discount for group bookings"
        }
    ]
    
    return {
        "success": True,
        "data": pricing_contexts
    }

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
    """Process payment for an order with automatic tip recording"""
    try:
        data = json.loads(payment_data) if isinstance(payment_data, str) else payment_data
        
        order = frappe.get_doc("Restaurant Order", order_id)
        order.payment_method = data.get("payment_method")
        order.amount_paid = data.get("amount_paid")
        order.payment_reference = data.get("payment_reference")
        
        # Automatic tip processing
        tip_amount = data.get("tip_amount", 0)
        if tip_amount > 0:
            # Determine tip type based on payment method and customer preference
            tip_type = "Individual" if data.get("tip_specific_staff") else "Pooled"
            
            # For cash tips, record immediately to specific staff
            if order.payment_method == "Cash" and tip_type == "Individual":
                auto_record_individual_tip(order, tip_amount, data.get("specific_staff_id"))
            
            # For credit card tips, add to pool for later distribution
            elif order.payment_method in ["Credit Card", "Debit Card"]:
                auto_record_pooled_tip(order, tip_amount)
            
            # For digital payments, check customer preference
            else:
                if tip_type == "Individual" and data.get("specific_staff_id"):
                    auto_record_individual_tip(order, tip_amount, data.get("specific_staff_id"))
                else:
                    auto_record_pooled_tip(order, tip_amount)
        
        order.save()
        
        return {
            "success": True,
            "message": f"Payment processed successfully" + (f" with ${tip_amount} tip recorded" if tip_amount > 0 else ""),
            "data": {
                "change_amount": order.change_amount,
                "payment_status": order.payment_status,
                "tip_recorded": tip_amount > 0,
                "tip_amount": tip_amount
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing payment: {str(e)}"
        }

def auto_record_individual_tip(order, tip_amount, staff_id=None):
    """Automatically record individual tip linked to order"""
    try:
        # If no specific staff mentioned, tip goes to the waiter who served
        target_staff = staff_id or order.waiter
        
        if not target_staff:
            # If no waiter assigned, add to pool
            auto_record_pooled_tip(order, tip_amount)
            return
        
        tip_data = {
            "staff_id": target_staff,
            "amount": tip_amount,
            "tip_date": order.order_date,
            "tip_time": frappe.utils.nowtime(),
            "tip_type": "Individual",
            "source": order.payment_method,
            "order_id": order.order_id,
            "table_number": order.table_number,
            "customer_name": order.customer_name,
            "notes": f"Auto-recorded from order {order.order_id}",
            "recorded_by": "SYSTEM_AUTO"
        }
        
        record_single_tip(tip_data)
        
        # Log the automatic tip recording
        frappe.log_error(f"Auto-recorded individual tip: ${tip_amount} to {target_staff} from order {order.order_id}", "Tip Auto-Recording")
        
    except Exception as e:
        frappe.log_error(f"Error auto-recording individual tip: {str(e)}", "Tip Auto-Recording Error")

def auto_record_pooled_tip(order, tip_amount):
    """Automatically record tip for pool distribution"""
    try:
        tip_data = {
            "staff_id": "POOL",  # Special identifier for pooled tips
            "amount": tip_amount,
            "tip_date": order.order_date,
            "tip_time": frappe.utils.nowtime(),
            "tip_type": "Pooled",
            "source": order.payment_method,
            "order_id": order.order_id,
            "table_number": order.table_number,
            "customer_name": order.customer_name,
            "notes": f"Auto-recorded for pool distribution from order {order.order_id}",
            "recorded_by": "SYSTEM_AUTO"
        }
        
        record_single_tip(tip_data)
        
        # Log the automatic tip recording
        frappe.log_error(f"Auto-recorded pooled tip: ${tip_amount} from order {order.order_id}", "Tip Auto-Recording")
        
    except Exception as e:
        frappe.log_error(f"Error auto-recording pooled tip: {str(e)}", "Tip Auto-Recording Error")



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


# ============================================================================
# TABLE BOOKING & RESERVATION SYSTEM
# ============================================================================

@frappe.whitelist(allow_guest=True)
def create_table_booking(booking_data):
    """Create a new table reservation"""
    try:
        data = json.loads(booking_data) if isinstance(booking_data, str) else booking_data
        
        # Validate required fields
        required_fields = ["customer_name", "customer_phone", "booking_date", "booking_time", "party_size"]
        for field in required_fields:
            if not data.get(field):
                return {
                    "success": False,
                    "message": f"Missing required field: {field}"
                }
        
        # Check table availability
        available_tables = get_available_tables(
            data["booking_date"], 
            data["booking_time"], 
            data["party_size"],
            data.get("preferred_zone"),
            data.get("special_requirements")
        )
        
        if not available_tables.get("success") or not available_tables.get("data"):
            return {
                "success": False,
                "message": "No tables available for the requested time and party size",
                "suggested_times": get_alternative_time_slots(data["booking_date"], data["party_size"])
            }
        
        # Generate booking ID
        booking_id = f"RES-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        # Create booking document
        booking = frappe.get_doc({
            "doctype": "Restaurant Table Booking",
            "booking_id": booking_id,
            "customer_name": data["customer_name"],
            "customer_phone": data["customer_phone"],
            "customer_email": data.get("customer_email"),
            "booking_date": data["booking_date"],
            "booking_time": data["booking_time"],
            "party_size": data["party_size"],
            "duration_hours": data.get("duration_hours", 2),  # Default 2 hours
            "table_number": available_tables["data"][0]["table_number"],
            "table_zone": available_tables["data"][0]["zone"],
            "booking_status": "Confirmed",
            "special_requests": data.get("special_requests"),
            "dietary_requirements": data.get("dietary_requirements"),
            "occasion": data.get("occasion"),  # Birthday, Anniversary, etc.
            "preferred_seating": data.get("preferred_seating"),  # Window, Quiet, etc.
            "deposit_required": data.get("deposit_required", False),
            "deposit_amount": data.get("deposit_amount", 0),
            "booking_source": data.get("booking_source", "Walk-in"),  # Online, Phone, Walk-in
            "notes": data.get("notes", "")
        })
        
        booking.insert()
        
        # Send confirmation (you can implement SMS/Email later)
        return {
            "success": True,
            "message": f"Table reserved successfully! Booking ID: {booking_id}",
            "data": {
                "booking_id": booking_id,
                "table_number": booking.table_number,
                "table_zone": booking.table_zone,
                "booking_date": booking.booking_date,
                "booking_time": booking.booking_time,
                "party_size": booking.party_size,
                "confirmation_needed": booking.deposit_required
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating booking: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_available_tables(booking_date, booking_time, party_size, preferred_zone=None, special_requirements=None):
    """Get available tables for specific date, time and party size"""
    try:
        # Define restaurant table layout (you can move this to a DocType later)
        restaurant_tables = [
            {"table_number": 1, "capacity": 2, "zone": "Main Dining", "features": ["Window View"]},
            {"table_number": 2, "capacity": 4, "zone": "Main Dining", "features": ["Window View"]},
            {"table_number": 3, "capacity": 6, "zone": "Main Dining", "features": []},
            {"table_number": 4, "capacity": 8, "zone": "Main Dining", "features": ["Large Group"]},
            {"table_number": 5, "capacity": 2, "zone": "VIP Section", "features": ["Private", "Window View"]},
            {"table_number": 6, "capacity": 4, "zone": "VIP Section", "features": ["Private", "Quiet"]},
            {"table_number": 7, "capacity": 6, "zone": "VIP Section", "features": ["Private", "Large Group"]},
            {"table_number": 8, "capacity": 2, "zone": "Terrace", "features": ["Outdoor", "Romantic"]},
            {"table_number": 9, "capacity": 4, "zone": "Terrace", "features": ["Outdoor"]},
            {"table_number": 10, "capacity": 4, "zone": "Bar Area", "features": ["Casual", "Sports View"]},
            {"table_number": 11, "capacity": 6, "zone": "Private Dining", "features": ["Private", "Business Meeting"]},
            {"table_number": 12, "capacity": 8, "zone": "Private Dining", "features": ["Private", "Large Group", "Business Meeting"]}
        ]
        
        # Filter tables by capacity (can seat party size)
        suitable_tables = [t for t in restaurant_tables if t["capacity"] >= int(party_size)]
        
        # Filter by preferred zone if specified
        if preferred_zone:
            suitable_tables = [t for t in suitable_tables if t["zone"] == preferred_zone]
        
        # Filter by special requirements
        if special_requirements:
            req_list = [req.strip() for req in special_requirements.split(",")]
            suitable_tables = [t for t in suitable_tables 
                             if any(req in t["features"] for req in req_list)]
        
        # Check existing bookings for conflicts
        booking_start = f"{booking_date} {booking_time}"
        booking_end_time = frappe.utils.add_to_date(
            frappe.utils.get_datetime(booking_start), 
            hours=2  # Default 2-hour booking
        )
        
        existing_bookings = frappe.get_all("Restaurant Table Booking",
            filters={
                "booking_date": booking_date,
                "booking_status": ["in", ["Confirmed", "Seated"]]
            },
            fields=["table_number", "booking_time", "duration_hours"]
        )
        
        # Remove tables that are already booked
        available_tables = []
        for table in suitable_tables:
            is_available = True
            for booking in existing_bookings:
                if booking.table_number == table["table_number"]:
                    existing_start = f"{booking_date} {booking.booking_time}"
                    existing_end = frappe.utils.add_to_date(
                        frappe.utils.get_datetime(existing_start),
                        hours=booking.duration_hours or 2
                    )
                    
                    # Check for time overlap
                    if (frappe.utils.get_datetime(booking_start) < existing_end and
                        booking_end_time > frappe.utils.get_datetime(existing_start)):
                        is_available = False
                        break
            
            if is_available:
                available_tables.append(table)
        
        return {
            "success": True,
            "data": available_tables
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error checking availability: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_alternative_time_slots(booking_date, party_size):
    """Get alternative time slots when preferred time is not available"""
    try:
        # Define restaurant operating hours
        time_slots = [
            "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
            "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"
        ]
        
        available_slots = []
        for time_slot in time_slots:
            availability = get_available_tables(booking_date, time_slot, party_size)
            if availability.get("success") and availability.get("data"):
                available_slots.append({
                    "time": time_slot,
                    "available_tables": len(availability["data"])
                })
        
        return {
            "success": True,
            "data": available_slots
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting alternative slots: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_table_bookings(date=None, status=None):
    """Get table bookings with optional filters"""
    try:
        filters = {}
        if date:
            filters["booking_date"] = date
        if status:
            filters["booking_status"] = status
        
        bookings = frappe.get_all("Restaurant Table Booking",
            filters=filters,
            fields=["booking_id", "customer_name", "customer_phone", "booking_date", 
                   "booking_time", "party_size", "table_number", "table_zone", 
                   "booking_status", "special_requests", "occasion"],
            order_by="booking_date desc, booking_time desc"
        )
        
        return {
            "success": True,
            "data": bookings
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving bookings: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def update_booking_status(booking_id, new_status, notes=None):
    """Update booking status (Confirmed, Seated, Completed, Cancelled, No-Show)"""
    try:
        booking = frappe.get_doc("Restaurant Table Booking", booking_id)
        
        old_status = booking.booking_status
        booking.booking_status = new_status
        
        if notes:
            booking.notes = f"{booking.notes}\n{frappe.utils.now()}: {notes}" if booking.notes else notes
        
        # Add status change to log
        status_log = {
            "timestamp": frappe.utils.now(),
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": frappe.session.user,
            "notes": notes or ""
        }
        
        if not hasattr(booking, 'status_history'):
            booking.status_history = []
        booking.status_history.append(status_log)
        
        # Special actions based on status
        if new_status == "Seated":
            booking.actual_arrival_time = frappe.utils.nowtime()
        elif new_status == "Completed":
            booking.actual_departure_time = frappe.utils.nowtime()
        
        booking.save()
        
        return {
            "success": True,
            "message": f"Booking status updated to {new_status}",
            "data": {
                "booking_id": booking_id,
                "new_status": new_status,
                "table_number": booking.table_number
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating booking: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def add_to_waitlist(waitlist_data):
    """Add customer to waitlist when no tables available"""
    try:
        data = json.loads(waitlist_data) if isinstance(waitlist_data, str) else waitlist_data
        
        waitlist_id = f"WAIT-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        waitlist = frappe.get_doc({
            "doctype": "Restaurant Waitlist",
            "waitlist_id": waitlist_id,
            "customer_name": data["customer_name"],
            "customer_phone": data["customer_phone"],
            "customer_email": data.get("customer_email"),
            "requested_date": data["requested_date"],
            "requested_time": data["requested_time"],
            "party_size": data["party_size"],
            "preferred_zone": data.get("preferred_zone"),
            "special_requests": data.get("special_requests"),
            "waitlist_status": "Active",
            "added_time": frappe.utils.now(),
            "willing_to_wait": data.get("willing_to_wait", True),
            "alternative_dates": data.get("alternative_dates", [])
        })
        
        waitlist.insert()
        
        return {
            "success": True,
            "message": f"Added to waitlist. We'll contact you if a table becomes available.",
            "data": {
                "waitlist_id": waitlist_id,
                "position": get_waitlist_position(waitlist_id)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error adding to waitlist: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_waitlist_position(waitlist_id):
    """Get position in waitlist"""
    try:
        waitlist_entry = frappe.get_doc("Restaurant Waitlist", waitlist_id)
        
        # Count entries added before this one for same date/time
        earlier_entries = frappe.get_all("Restaurant Waitlist",
            filters={
                "requested_date": waitlist_entry.requested_date,
                "requested_time": waitlist_entry.requested_time,
                "waitlist_status": "Active",
                "added_time": ["<", waitlist_entry.added_time]
            }
        )
        
        return len(earlier_entries) + 1
        
    except Exception as e:
        return 0

@frappe.whitelist(allow_guest=True)
def get_customer_booking_history(customer_phone):
    """Get booking history for a customer"""
    try:
        bookings = frappe.get_all("Restaurant Table Booking",
            filters={"customer_phone": customer_phone},
            fields=["booking_id", "customer_name", "booking_date", "booking_time", 
                   "party_size", "table_number", "booking_status", "occasion"],
            order_by="booking_date desc"
        )
        
        # Get customer preferences from past bookings
        preferences = analyze_customer_preferences(bookings)
        
        return {
            "success": True,
            "data": {
                "bookings": bookings,
                "preferences": preferences,
                "total_visits": len([b for b in bookings if b.booking_status == "Completed"]),
                "vip_status": len(bookings) >= 5  # VIP after 5 bookings
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving customer history: {str(e)}"
        }

def analyze_customer_preferences(bookings):
    """Analyze customer preferences from booking history"""
    preferences = {
        "favorite_table_zones": {},
        "common_party_sizes": {},
        "preferred_times": {},
        "special_occasions": []
    }
    
    for booking in bookings:
        # Count zone preferences
        zone = booking.get("table_zone", "Main Dining")
        preferences["favorite_table_zones"][zone] = preferences["favorite_table_zones"].get(zone, 0) + 1
        
        # Count party size preferences
        size = str(booking.get("party_size", 2))
        preferences["common_party_sizes"][size] = preferences["common_party_sizes"].get(size, 0) + 1
        
        # Count time preferences
        time_hour = booking.get("booking_time", "19:00")[:2]
        preferences["preferred_times"][time_hour] = preferences["preferred_times"].get(time_hour, 0) + 1
        
        # Track occasions
        if booking.get("occasion"):
            preferences["special_occasions"].append(booking["occasion"])
    
    return preferences

@frappe.whitelist(allow_guest=True)
def get_restaurant_layout():
    """Get restaurant table layout and zones"""
    layout = {
        "zones": [
            {
                "name": "Main Dining",
                "tables": [
                    {"number": 1, "capacity": 2, "features": ["Window View"], "coordinates": {"x": 10, "y": 10}},
                    {"number": 2, "capacity": 4, "features": ["Window View"], "coordinates": {"x": 10, "y": 30}},
                    {"number": 3, "capacity": 6, "features": [], "coordinates": {"x": 10, "y": 50}},
                    {"number": 4, "capacity": 8, "features": ["Large Group"], "coordinates": {"x": 10, "y": 70}}
                ]
            },
            {
                "name": "VIP Section", 
                "tables": [
                    {"number": 5, "capacity": 2, "features": ["Private", "Window View"], "coordinates": {"x": 50, "y": 10}},
                    {"number": 6, "capacity": 4, "features": ["Private", "Quiet"], "coordinates": {"x": 50, "y": 30}},
                    {"number": 7, "capacity": 6, "features": ["Private", "Large Group"], "coordinates": {"x": 50, "y": 50}}
                ]
            },
            {
                "name": "Terrace",
                "tables": [
                    {"number": 8, "capacity": 2, "features": ["Outdoor", "Romantic"], "coordinates": {"x": 90, "y": 10}},
                    {"number": 9, "capacity": 4, "features": ["Outdoor"], "coordinates": {"x": 90, "y": 30}}
                ]
            },
            {
                "name": "Bar Area",
                "tables": [
                    {"number": 10, "capacity": 4, "features": ["Casual", "Sports View"], "coordinates": {"x": 30, "y": 90}}
                ]
            },
            {
                "name": "Private Dining",
                "tables": [
                    {"number": 11, "capacity": 6, "features": ["Private", "Business Meeting"], "coordinates": {"x": 70, "y": 70}},
                    {"number": 12, "capacity": 8, "features": ["Private", "Large Group", "Business Meeting"], "coordinates": {"x": 70, "y": 90}}
                ]
            }
        ],
        "operating_hours": {
            "lunch": {"start": "11:00", "end": "15:00"},
            "dinner": {"start": "17:00", "end": "22:00"}
        },
        "booking_policies": {
            "advance_booking_days": 30,
            "minimum_party_size": 1,
            "maximum_party_size": 12,
            "default_duration_hours": 2,
            "deposit_required_for_groups": 6
        }
    }
    
    return {
        "success": True,
        "data": layout
    }


# ============================================================================
# ADVANCE PAYMENTS & TIPS MANAGEMENT SYSTEM
# ============================================================================

@frappe.whitelist(allow_guest=True)
def request_advance_payment(advance_data):
    """Staff can request advance payment against future salary"""
    try:
        data = json.loads(advance_data) if isinstance(advance_data, str) else advance_data
        
        # Validate required fields
        required_fields = ["staff_id", "amount_requested", "reason"]
        for field in required_fields:
            if not data.get(field):
                return {
                    "success": False,
                    "message": f"Missing required field: {field}"
                }
        
        # Get staff information and check eligibility
        staff = frappe.get_doc("Restaurant Staff", data["staff_id"])
        
        # Check if staff is eligible for advance (employment duration, previous advances, etc.)
        eligibility = check_advance_eligibility(staff, data["amount_requested"])
        if not eligibility["eligible"]:
            return {
                "success": False,
                "message": eligibility["reason"]
            }
        
        # Generate advance request ID
        advance_id = f"ADV-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        # Create advance request
        advance_request = frappe.get_doc({
            "doctype": "Restaurant Staff Advance",
            "advance_id": advance_id,
            "staff_id": data["staff_id"],
            "staff_name": staff.full_name,
            "amount_requested": data["amount_requested"],
            "reason": data["reason"],
            "request_date": frappe.utils.nowdate(),
            "request_time": frappe.utils.nowtime(),
            "status": "Pending",
            "expected_deduction_start": data.get("expected_deduction_start"),
            "deduction_installments": data.get("deduction_installments", 1),
            "emergency_request": data.get("emergency_request", False),
            "supporting_documents": data.get("supporting_documents", ""),
            "requested_by": data["staff_id"],
            "notes": data.get("notes", "")
        })
        
        advance_request.insert()
        
        return {
            "success": True,
            "message": f"Advance payment request submitted successfully. Request ID: {advance_id}",
            "data": {
                "advance_id": advance_id,
                "amount_requested": advance_request.amount_requested,
                "status": advance_request.status,
                "max_eligible_amount": eligibility["max_amount"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating advance request: {str(e)}"
        }

def check_advance_eligibility(staff, requested_amount):
    """Check if staff is eligible for advance payment"""
    try:
        # Basic eligibility rules
        employment_duration = frappe.utils.date_diff(frappe.utils.nowdate(), staff.hire_date)
        
        # Must be employed for at least 30 days
        if employment_duration < 30:
            return {
                "eligible": False,
                "reason": "Must be employed for at least 30 days to request advance",
                "max_amount": 0
            }
        
        # Calculate maximum advance based on salary and existing advances
        monthly_salary = staff.base_hourly_rate * 160  # Assuming 160 hours/month
        max_advance_percentage = 0.5  # 50% of monthly salary
        max_eligible_amount = monthly_salary * max_advance_percentage
        
        # Check existing unpaid advances
        existing_advances = frappe.get_all("Restaurant Staff Advance",
            filters={
                "staff_id": staff.name,
                "status": ["in", ["Approved", "Partially Repaid"]]
            },
            fields=["amount_approved", "amount_repaid"]
        )
        
        total_outstanding = sum(
            (adv.amount_approved or 0) - (adv.amount_repaid or 0) 
            for adv in existing_advances
        )
        
        available_advance = max_eligible_amount - total_outstanding
        
        if requested_amount > available_advance:
            return {
                "eligible": False,
                "reason": f"Requested amount exceeds available advance limit. Available: ${available_advance:.2f}",
                "max_amount": available_advance
            }
        
        return {
            "eligible": True,
            "reason": "Eligible for advance",
            "max_amount": available_advance
        }
        
    except Exception as e:
        return {
            "eligible": False,
            "reason": f"Error checking eligibility: {str(e)}",
            "max_amount": 0
        }

@frappe.whitelist(allow_guest=True)
def approve_advance_payment(advance_id, approval_data):
    """Manager approves/rejects advance payment request"""
    try:
        data = json.loads(approval_data) if isinstance(approval_data, str) else approval_data
        
        advance = frappe.get_doc("Restaurant Staff Advance", advance_id)
        
        # Update advance request
        advance.status = data["status"]  # "Approved", "Rejected"
        advance.amount_approved = data.get("amount_approved", advance.amount_requested)
        advance.approved_by = data.get("approved_by")
        advance.approval_date = frappe.utils.nowdate()
        advance.approval_notes = data.get("approval_notes", "")
        advance.deduction_installments = data.get("deduction_installments", 1)
        advance.deduction_start_date = data.get("deduction_start_date")
        
        advance.save()
        
        # If approved, create payment record
        if data["status"] == "Approved":
            payment_id = create_advance_payment_record(advance)
            
            return {
                "success": True,
                "message": f"Advance payment approved and processed. Payment ID: {payment_id}",
                "data": {
                    "advance_id": advance_id,
                    "amount_approved": advance.amount_approved,
                    "payment_id": payment_id
                }
            }
        else:
            return {
                "success": True,
                "message": f"Advance payment request {data['status'].lower()}",
                "data": {
                    "advance_id": advance_id,
                    "status": advance.status
                }
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing advance approval: {str(e)}"
        }

def create_advance_payment_record(advance):
    """Create payment record for approved advance"""
    try:
        payment_id = f"PAY-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        payment = frappe.get_doc({
            "doctype": "Restaurant Staff Payment",
            "payment_id": payment_id,
            "staff_id": advance.staff_id,
            "payment_type": "Advance",
            "amount": advance.amount_approved,
            "payment_date": frappe.utils.nowdate(),
            "payment_method": "Bank Transfer",  # Default
            "reference_id": advance.advance_id,
            "description": f"Advance payment - {advance.reason}",
            "status": "Completed"
        })
        
        payment.insert()
        return payment_id
        
    except Exception as e:
        frappe.log_error(f"Error creating payment record: {str(e)}")
        return None

@frappe.whitelist(allow_guest=True)
def record_tips(tips_data):
    """Record tips received by staff"""
    try:
        data = json.loads(tips_data) if isinstance(tips_data, str) else tips_data
        
        # Support both individual and batch tip recording
        if "tips" in data:
            # Batch recording - multiple staff tips at once
            results = []
            for tip in data["tips"]:
                result = record_single_tip(tip)
                results.append(result)
            
            return {
                "success": True,
                "message": f"Recorded {len(results)} tip entries",
                "data": results
            }
        else:
            # Single tip recording
            result = record_single_tip(data)
            return {
                "success": True,
                "message": "Tip recorded successfully",
                "data": result
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error recording tips: {str(e)}"
        }

def record_single_tip(tip_data):
    """Record a single tip entry"""
    try:
        tip_id = f"TIP-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        tip = frappe.get_doc({
            "doctype": "Restaurant Staff Tips",
            "tip_id": tip_id,
            "staff_id": tip_data["staff_id"],
            "amount": tip_data["amount"],
            "tip_date": tip_data.get("tip_date", frappe.utils.nowdate()),
            "tip_time": tip_data.get("tip_time", frappe.utils.nowtime()),
            "tip_type": tip_data.get("tip_type", "Individual"),  # Individual, Pooled, Credit Card
            "source": tip_data.get("source", "Cash"),  # Cash, Credit Card, Digital
            "order_id": tip_data.get("order_id"),  # Link to specific order
            "table_number": tip_data.get("table_number"),
            "customer_name": tip_data.get("customer_name"),
            "notes": tip_data.get("notes", ""),
            "recorded_by": tip_data.get("recorded_by"),
            "status": "Confirmed"
        })
        
        tip.insert()
        
        return {
            "tip_id": tip_id,
            "staff_id": tip.staff_id,
            "amount": tip.amount,
            "tip_type": tip.tip_type
        }
        
    except Exception as e:
        frappe.log_error(f"Error recording single tip: {str(e)}")
        return {"error": str(e)}

@frappe.whitelist(allow_guest=True)
def distribute_pooled_tips(distribution_data):
    """Distribute pooled tips among staff based on predefined rules"""
    try:
        data = json.loads(distribution_data) if isinstance(distribution_data, str) else distribution_data
        
        total_pooled_amount = data["total_amount"]
        distribution_date = data.get("distribution_date", frappe.utils.nowdate())
        distribution_method = data.get("method", "equal")  # equal, hours_worked, performance
        
        # Get eligible staff for tip distribution
        eligible_staff = get_eligible_staff_for_tips(distribution_date)
        
        if not eligible_staff:
            return {
                "success": False,
                "message": "No eligible staff found for tip distribution"
            }
        
        # Calculate distribution based on method
        distributions = calculate_tip_distribution(
            eligible_staff, 
            total_pooled_amount, 
            distribution_method,
            distribution_date
        )
        
        # Record individual tip distributions
        distribution_id = f"DIST-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        for staff_id, amount in distributions.items():
            if amount > 0:
                tip_data = {
                    "staff_id": staff_id,
                    "amount": amount,
                    "tip_date": distribution_date,
                    "tip_type": "Pooled",
                    "source": "Pool Distribution",
                    "notes": f"Pool distribution {distribution_id} - {distribution_method}",
                    "recorded_by": data.get("distributed_by")
                }
                record_single_tip(tip_data)
        
        return {
            "success": True,
            "message": f"Pooled tips distributed to {len(distributions)} staff members",
            "data": {
                "distribution_id": distribution_id,
                "total_amount": total_pooled_amount,
                "staff_count": len(distributions),
                "distributions": distributions
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error distributing pooled tips: {str(e)}"
        }

def get_eligible_staff_for_tips(date):
    """Get staff who worked on the given date and are eligible for tips"""
    try:
        # Get staff who worked on the date
        attendance_records = frappe.get_all("Restaurant Attendance",
            filters={
                "attendance_date": date,
                "status": "Present"
            },
            fields=["staff_id", "hours_worked"]
        )
        
        eligible_staff = {}
        for record in attendance_records:
            staff = frappe.get_doc("Restaurant Staff", record.staff_id)
            # Only include tip-eligible positions
            if staff.position in ["Waiter", "Server", "Bartender", "Host"]:
                eligible_staff[record.staff_id] = {
                    "hours_worked": record.hours_worked or 8,
                    "position": staff.position,
                    "base_rate": staff.base_hourly_rate
                }
        
        return eligible_staff
        
    except Exception as e:
        frappe.log_error(f"Error getting eligible staff: {str(e)}")
        return {}

def calculate_tip_distribution(eligible_staff, total_amount, method, date):
    """Calculate how to distribute tips based on method"""
    distributions = {}
    
    try:
        if method == "equal":
            # Equal distribution
            amount_per_person = total_amount / len(eligible_staff)
            for staff_id in eligible_staff:
                distributions[staff_id] = round(amount_per_person, 2)
                
        elif method == "hours_worked":
            # Distribution based on hours worked
            total_hours = sum(staff["hours_worked"] for staff in eligible_staff.values())
            for staff_id, staff_info in eligible_staff.items():
                percentage = staff_info["hours_worked"] / total_hours
                distributions[staff_id] = round(total_amount * percentage, 2)
                
        elif method == "performance":
            # Distribution based on performance metrics (orders served, customer ratings, etc.)
            # This would require more complex calculation based on performance data
            # For now, fallback to hours worked
            return calculate_tip_distribution(eligible_staff, total_amount, "hours_worked", date)
        
        return distributions
        
    except Exception as e:
        frappe.log_error(f"Error calculating tip distribution: {str(e)}")
        return {}

@frappe.whitelist(allow_guest=True)
def get_staff_advances(staff_id=None, status=None):
    """Get advance payment records"""
    try:
        filters = {}
        if staff_id:
            filters["staff_id"] = staff_id
        if status:
            filters["status"] = status
        
        advances = frappe.get_all("Restaurant Staff Advance",
            filters=filters,
            fields=["advance_id", "staff_id", "staff_name", "amount_requested", 
                   "amount_approved", "amount_repaid", "status", "request_date", 
                   "reason", "deduction_installments"],
            order_by="request_date desc"
        )
        
        return {
            "success": True,
            "data": advances
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving advances: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_staff_tips(staff_id=None, date_from=None, date_to=None):
    """Get tip records for staff"""
    try:
        filters = {}
        if staff_id:
            filters["staff_id"] = staff_id
        if date_from:
            filters["tip_date"] = [">=", date_from]
        if date_to:
            if "tip_date" in filters:
                filters["tip_date"] = ["between", [date_from, date_to]]
            else:
                filters["tip_date"] = ["<=", date_to]
        
        tips = frappe.get_all("Restaurant Staff Tips",
            filters=filters,
            fields=["tip_id", "staff_id", "amount", "tip_date", "tip_time", 
                   "tip_type", "source", "order_id", "table_number", "customer_name"],
            order_by="tip_date desc, tip_time desc"
        )
        
        # Calculate summary
        total_tips = sum(tip.amount for tip in tips)
        tips_by_type = {}
        for tip in tips:
            tip_type = tip.tip_type
            tips_by_type[tip_type] = tips_by_type.get(tip_type, 0) + tip.amount
        
        return {
            "success": True,
            "data": {
                "tips": tips,
                "summary": {
                    "total_amount": total_tips,
                    "total_count": len(tips),
                    "by_type": tips_by_type
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving tips: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def calculate_staff_payroll(staff_id, period_start, period_end):
    """Calculate comprehensive payroll including salary, tips, advances"""
    try:
        staff = frappe.get_doc("Restaurant Staff", staff_id)
        
        # Get attendance for the period
        attendance = frappe.get_all("Restaurant Attendance",
            filters={
                "staff_id": staff_id,
                "attendance_date": ["between", [period_start, period_end]],
                "status": "Present"
            },
            fields=["attendance_date", "check_in_time", "check_out_time", "hours_worked", "overtime_hours"]
        )
        
        # Calculate basic salary
        total_hours = sum(att.hours_worked or 0 for att in attendance)
        total_overtime = sum(att.overtime_hours or 0 for att in attendance)
        
        basic_salary = total_hours * staff.base_hourly_rate
        overtime_pay = total_overtime * staff.weekend_rate  # Using weekend rate for overtime
        
        # Get tips for the period
        tips_response = get_staff_tips(staff_id, period_start, period_end)
        total_tips = tips_response["data"]["summary"]["total_amount"] if tips_response["success"] else 0
        
        # Get advances and calculate deductions
        advances = frappe.get_all("Restaurant Staff Advance",
            filters={
                "staff_id": staff_id,
                "status": ["in", ["Approved", "Partially Repaid"]],
                "deduction_start_date": ["<=", period_end]
            },
            fields=["advance_id", "amount_approved", "amount_repaid", "deduction_installments"]
        )
        
        total_advance_deduction = 0
        for advance in advances:
            outstanding = (advance.amount_approved or 0) - (advance.amount_repaid or 0)
            if outstanding > 0:
                installment_amount = outstanding / (advance.deduction_installments or 1)
                total_advance_deduction += min(installment_amount, outstanding)
        
        # Calculate net pay
        gross_pay = basic_salary + overtime_pay + total_tips
        net_pay = gross_pay - total_advance_deduction
        
        payroll_data = {
            "staff_id": staff_id,
            "staff_name": staff.full_name,
            "period_start": period_start,
            "period_end": period_end,
            "total_hours": total_hours,
            "overtime_hours": total_overtime,
            "basic_salary": basic_salary,
            "overtime_pay": overtime_pay,
            "total_tips": total_tips,
            "advance_deductions": total_advance_deduction,
            "gross_pay": gross_pay,
            "net_pay": net_pay,
            "attendance_days": len(attendance)
        }
        
        return {
            "success": True,
            "data": payroll_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error calculating payroll: {str(e)}"
        } 

# ============================================================================
# COMPLIMENTARY SYSTEM & VIP TREATMENT
# ============================================================================

@frappe.whitelist(allow_guest=True)
def auto_trigger_complimentary(customer_id, order_id, trigger_type=None):
    """Automatically trigger complimentary items based on customer profile and occasions"""
    try:
        customer = frappe.get_doc("Restaurant Customer Profile", customer_id)
        order = frappe.get_doc("Restaurant Order", order_id)
        
        complimentary_items = []
        
        # Birthday Detection
        if trigger_type == "birthday" or is_customer_birthday(customer):
            birthday_item = {
                "item_name": "Birthday Dessert with Candle",
                "item_type": "Dessert",
                "quantity": 1,
                "trigger_type": "Birthday",
                "complimentary_reason": f"Happy Birthday {customer.full_name}!",
                "cost_center": "Marketing"
            }
            complimentary_items.append(birthday_item)
        
        # Anniversary Detection
        if trigger_type == "anniversary" or is_customer_anniversary(customer):
            anniversary_item = {
                "item_name": "Complimentary Champagne",
                "item_type": "Champagne", 
                "quantity": 1,
                "trigger_type": "Anniversary",
                "complimentary_reason": f"Happy Anniversary {customer.full_name}!",
                "cost_center": "VIP Program"
            }
            complimentary_items.append(anniversary_item)
        
        # First Visit Welcome
        if customer.total_visits <= 1:
            welcome_item = {
                "item_name": "Welcome Amuse-bouche",
                "item_type": "Amuse-bouche",
                "quantity": 1,
                "trigger_type": "First Visit",
                "complimentary_reason": "Welcome to our restaurant!",
                "cost_center": "Marketing"
            }
            complimentary_items.append(welcome_item)
        
        # VIP Member Perks
        if customer.vip_status or customer.membership_tier in ["Platinum", "VIP", "Founder"]:
            vip_item = {
                "item_name": "VIP Welcome Drink",
                "item_type": "Drink",
                "quantity": 1,
                "trigger_type": "VIP Member",
                "complimentary_reason": f"VIP {customer.membership_tier} member perk",
                "cost_center": "VIP Program"
            }
            complimentary_items.append(vip_item)
        
        # High-Value Customer Recognition
        if customer.total_spent >= 5000:  # $5000+ lifetime spending
            recognition_item = {
                "item_name": "Chef's Special Appetizer",
                "item_type": "Appetizer",
                "quantity": 1,
                "trigger_type": "Loyalty Reward",
                "complimentary_reason": f"Thank you for being a valued customer (${customer.total_spent} lifetime)",
                "cost_center": "Loyalty Program"
            }
            complimentary_items.append(recognition_item)
        
        # Record all triggered complimentary items
        results = []
        for item in complimentary_items:
            result = create_complimentary_item(customer_id, order_id, item)
            results.append(result)
        
        return {
            "success": True,
            "message": f"Triggered {len(complimentary_items)} complimentary items",
            "data": {
                "customer_name": customer.full_name,
                "customer_tier": customer.membership_tier,
                "complimentary_items": results
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error triggering complimentary items: {str(e)}"
        }

def is_customer_birthday(customer):
    """Check if today is customer's birthday"""
    if not customer.date_of_birth:
        return False
    
    today = frappe.utils.nowdate()
    birth_date = customer.date_of_birth
    
    # Check if month and day match
    return (today.month == birth_date.month and today.day == birth_date.day)

def is_customer_anniversary(customer):
    """Check if today is customer's anniversary"""
    if not customer.anniversary_date:
        return False
    
    today = frappe.utils.nowdate()
    anniversary = customer.anniversary_date
    
    # Check if month and day match
    return (today.month == anniversary.month and today.day == anniversary.day)

def create_complimentary_item(customer_id, order_id, item_data):
    """Create a complimentary item record"""
    try:
        complimentary_id = f"COMP-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        # Get menu item price for tracking
        original_price = get_menu_item_price(item_data["item_name"])
        
        complimentary = frappe.get_doc({
            "doctype": "Restaurant Complimentary Item",
            "complimentary_id": complimentary_id,
            "customer_id": customer_id,
            "order_id": order_id,
            "trigger_type": item_data["trigger_type"],
            "item_name": item_data["item_name"],
            "item_type": item_data["item_type"],
            "quantity": item_data.get("quantity", 1),
            "original_price": original_price,
            "complimentary_reason": item_data["complimentary_reason"],
            "cost_center": item_data["cost_center"],
            "date_given": frappe.utils.nowdate(),
            "time_given": frappe.utils.nowtime(),
            "approved_by": "SYSTEM_AUTO",
            "status": "Pending"
        })
        
        complimentary.insert()
        
        return {
            "complimentary_id": complimentary_id,
            "item_name": item_data["item_name"],
            "reason": item_data["complimentary_reason"],
            "value": original_price
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating complimentary item: {str(e)}")
        return {"error": str(e)}

def get_menu_item_price(item_name):
    """Get price of menu item for cost tracking"""
    try:
        price = frappe.db.get_value("Restaurant Menu Item", {"item_name": item_name}, "price")
        return price if price else 0
    except:
        return 0

@frappe.whitelist(allow_guest=True)
def manual_add_complimentary(complimentary_data):
    """Manually add complimentary item (manager override)"""
    try:
        data = json.loads(complimentary_data) if isinstance(complimentary_data, str) else complimentary_data
        
        # Validate required fields
        required_fields = ["customer_id", "order_id", "item_name", "reason", "approved_by"]
        for field in required_fields:
            if not data.get(field):
                return {
                    "success": False,
                    "message": f"Missing required field: {field}"
                }
        
        item_data = {
            "trigger_type": "Manual Override",
            "item_name": data["item_name"],
            "item_type": data.get("item_type", "Service Upgrade"),
            "quantity": data.get("quantity", 1),
            "complimentary_reason": data["reason"],
            "cost_center": "Manager Discretion"
        }
        
        result = create_complimentary_item(data["customer_id"], data["order_id"], item_data)
        
        # Update the approved_by field
        if not result.get("error"):
            frappe.db.set_value("Restaurant Complimentary Item", result["complimentary_id"], "approved_by", data["approved_by"])
        
        return {
            "success": True,
            "message": "Complimentary item added successfully",
            "data": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error adding manual complimentary: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_complimentary_suggestions(customer_id, order_total=0):
    """Get AI-powered complimentary suggestions based on customer profile"""
    try:
        customer = frappe.get_doc("Restaurant Customer Profile", customer_id)
        suggestions = []
        
        # Birthday/Anniversary automatic suggestions
        if is_customer_birthday(customer):
            suggestions.append({
                "type": "birthday",
                "item": "Birthday Dessert with Candle",
                "reason": "Customer's birthday today",
                "priority": "high",
                "auto_trigger": True
            })
        
        if is_customer_anniversary(customer):
            suggestions.append({
                "type": "anniversary", 
                "item": "Complimentary Champagne",
                "reason": "Customer's anniversary today",
                "priority": "high",
                "auto_trigger": True
            })
        
        # VIP Treatment Suggestions
        if customer.membership_tier in ["Gold", "Platinum", "VIP"]:
            suggestions.append({
                "type": "vip_perk",
                "item": "Premium Wine Tasting",
                "reason": f"{customer.membership_tier} member privilege",
                "priority": "medium",
                "auto_trigger": False
            })
        
        # High-Value Order Suggestions
        if float(order_total) >= 200:
            suggestions.append({
                "type": "high_value",
                "item": "Chef's Signature Dessert",
                "reason": f"High-value order (${order_total})",
                "priority": "medium", 
                "auto_trigger": False
            })
        
        # Loyalty Milestone Suggestions
        if customer.total_visits % 10 == 0:  # Every 10 visits
            suggestions.append({
                "type": "loyalty_milestone",
                "item": "Loyalty Milestone Appetizer",
                "reason": f"Congratulations on your {customer.total_visits}th visit!",
                "priority": "medium",
                "auto_trigger": False
            })
        
        return {
            "success": True,
            "data": {
                "customer_name": customer.full_name,
                "customer_tier": customer.membership_tier,
                "suggestions": suggestions,
                "total_suggestions": len(suggestions)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting complimentary suggestions: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_complimentary_history(customer_id=None, date_from=None, date_to=None):
    """Get complimentary items history with cost analysis"""
    try:
        filters = {}
        
        if customer_id:
            filters["customer_id"] = customer_id
        
        if date_from:
            filters["date_given"] = [">=", date_from]
        
        if date_to:
            if "date_given" in filters:
                filters["date_given"] = ["between", [date_from, date_to]]
            else:
                filters["date_given"] = ["<=", date_to]
        
        complimentary_items = frappe.get_all("Restaurant Complimentary Item",
            filters=filters,
            fields=[
                "complimentary_id", "customer_id", "item_name", "item_type",
                "quantity", "original_price", "trigger_type", "complimentary_reason",
                "date_given", "time_given", "cost_center", "status"
            ],
            order_by="date_given desc"
        )
        
        # Calculate analytics
        total_value = sum(item.original_price * item.quantity for item in complimentary_items if item.original_price)
        by_trigger_type = {}
        by_cost_center = {}
        
        for item in complimentary_items:
            # Group by trigger type
            trigger = item.trigger_type
            if trigger not in by_trigger_type:
                by_trigger_type[trigger] = {"count": 0, "value": 0}
            by_trigger_type[trigger]["count"] += 1
            by_trigger_type[trigger]["value"] += (item.original_price or 0) * item.quantity
            
            # Group by cost center
            cost_center = item.cost_center
            if cost_center not in by_cost_center:
                by_cost_center[cost_center] = {"count": 0, "value": 0}
            by_cost_center[cost_center]["count"] += 1
            by_cost_center[cost_center]["value"] += (item.original_price or 0) * item.quantity
        
        return {
            "success": True,
            "data": {
                "complimentary_items": complimentary_items,
                "analytics": {
                    "total_items": len(complimentary_items),
                    "total_value": total_value,
                    "by_trigger_type": by_trigger_type,
                    "by_cost_center": by_cost_center
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting complimentary history: {str(e)}"
        }


# ============================================================================
# LOYALTY PROGRAM SYSTEM
# ============================================================================

@frappe.whitelist(allow_guest=True)
def add_loyalty_points(customer_id, order_total, bonus_reason=None):
    """Add loyalty points based on order total and tier multipliers"""
    try:
        # Get or create loyalty record
        loyalty = get_or_create_loyalty_record(customer_id)
        
        # Calculate base points (1 point per dollar spent)
        base_points = int(float(order_total))
        
        # Apply tier multiplier
        multiplier = loyalty.bonus_multiplier or 1.0
        tier_bonus = get_tier_bonus_multiplier(loyalty.current_tier)
        total_multiplier = multiplier * tier_bonus
        
        earned_points = int(base_points * total_multiplier)
        
        # Add bonus points if specified
        if bonus_reason:
            bonus_points = get_bonus_points(bonus_reason)
            earned_points += bonus_points
        
        # Update loyalty record
        loyalty.current_points += earned_points
        loyalty.lifetime_points += earned_points
        loyalty.last_activity = frappe.utils.now()
        
        # Check for tier upgrade
        new_tier = calculate_tier_upgrade(loyalty)
        tier_upgraded = new_tier != loyalty.current_tier
        
        if tier_upgraded:
            old_tier = loyalty.current_tier
            loyalty.current_tier = new_tier
            loyalty.tier_benefits = get_tier_benefits(new_tier)
            
            # Trigger tier upgrade rewards
            tier_upgrade_reward = get_tier_upgrade_reward(new_tier)
            if tier_upgrade_reward:
                loyalty.current_points += tier_upgrade_reward
                earned_points += tier_upgrade_reward
        
        loyalty.save()
        
        # Log points transaction
        log_points_transaction(customer_id, earned_points, "earned", f"Order purchase: ${order_total}")
        
        return {
            "success": True,
            "message": f"Earned {earned_points} points",
            "data": {
                "points_earned": earned_points,
                "total_points": loyalty.current_points,
                "current_tier": loyalty.current_tier,
                "tier_upgraded": tier_upgraded,
                "next_tier": get_next_tier(loyalty.current_tier),
                "points_to_next_tier": calculate_points_to_next_tier(loyalty)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error adding loyalty points: {str(e)}"
        }

def get_or_create_loyalty_record(customer_id):
    """Get existing loyalty record or create new one"""
    try:
        return frappe.get_doc("Restaurant Loyalty Program", customer_id)
    except frappe.DoesNotExistError:
        # Create new loyalty record
        loyalty = frappe.get_doc({
            "doctype": "Restaurant Loyalty Program",
            "customer_id": customer_id,
            "current_points": 0,
            "lifetime_points": 0,
            "current_tier": "Bronze",
            "member_since": frappe.utils.nowdate(),
            "referral_code": generate_referral_code(customer_id)
        })
        loyalty.insert()
        return loyalty

def get_tier_bonus_multiplier(tier):
    """Get point multiplier based on tier"""
    multipliers = {
        "Bronze": 1.0,
        "Silver": 1.1,
        "Gold": 1.25,
        "Platinum": 1.5,
        "VIP": 2.0,
        "Founder": 2.5
    }
    return multipliers.get(tier, 1.0)

def calculate_tier_upgrade(loyalty):
    """Calculate if customer should be upgraded to new tier"""
    tier_thresholds = {
        "Bronze": 0,
        "Silver": 500,
        "Gold": 1500,
        "Platinum": 5000,
        "VIP": 15000,
        "Founder": 50000
    }
    
    lifetime_points = loyalty.lifetime_points
    
    for tier, threshold in reversed(tier_thresholds.items()):
        if lifetime_points >= threshold:
            return tier
    
    return "Bronze"

def get_tier_benefits(tier):
    """Get benefits for specific tier"""
    benefits = {
        "Bronze": ["1x points", "Birthday reward"],
        "Silver": ["1.1x points", "Birthday reward", "Free appetizer monthly"],
        "Gold": ["1.25x points", "Birthday reward", "Free appetizer monthly", "Priority reservations"],
        "Platinum": ["1.5x points", "Birthday + Anniversary rewards", "Free appetizer monthly", "Priority reservations", "Complimentary valet"],
        "VIP": ["2x points", "All rewards", "Monthly free dinner", "Private dining access", "Personal concierge"],
        "Founder": ["2.5x points", "All rewards", "Weekly free dinner", "Exclusive events", "Chef's table access"]
    }
    return json.dumps(benefits.get(tier, []))

@frappe.whitelist(allow_guest=True)
def redeem_loyalty_points(customer_id, redemption_data):
    """Redeem loyalty points for rewards"""
    try:
        data = json.loads(redemption_data) if isinstance(redemption_data, str) else redemption_data
        
        loyalty = frappe.get_doc("Restaurant Loyalty Program", customer_id)
        
        redemption_type = data.get("redemption_type")
        points_to_redeem = int(data.get("points", 0))
        
        # Validate sufficient points
        if loyalty.current_points < points_to_redeem:
            return {
                "success": False,
                "message": f"Insufficient points. Available: {loyalty.current_points}, Required: {points_to_redeem}"
            }
        
        # Process redemption
        redemption_value = calculate_redemption_value(redemption_type, points_to_redeem)
        
        # Deduct points
        loyalty.current_points -= points_to_redeem
        loyalty.points_redeemed += points_to_redeem
        loyalty.save()
        
        # Log redemption
        log_points_transaction(customer_id, points_to_redeem, "redeemed", f"Redemption: {redemption_type}")
        
        return {
            "success": True,
            "message": f"Successfully redeemed {points_to_redeem} points",
            "data": {
                "points_redeemed": points_to_redeem,
                "redemption_value": redemption_value,
                "remaining_points": loyalty.current_points,
                "redemption_details": data
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error redeeming points: {str(e)}"
        }

def log_points_transaction(customer_id, points, transaction_type, description):
    """Log points transaction for audit trail"""
    try:
        transaction_id = f"PTS-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        # This would create a points transaction log
        # For now, just log to system
        frappe.log_error(f"Points Transaction: {customer_id} - {transaction_type} {points} points - {description}", "Loyalty Points")
        
    except Exception as e:
        frappe.log_error(f"Error logging points transaction: {str(e)}")


# ============================================================================
# EVENT MANAGEMENT SYSTEM
# ============================================================================

@frappe.whitelist(allow_guest=True)
def create_event_booking(event_data):
    """Create new event booking"""
    try:
        data = json.loads(event_data) if isinstance(event_data, str) else event_data
        
        event_id = f"EVT-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        # Calculate suggested deposit (20% of estimated cost)
        estimated_cost = estimate_event_cost(data)
        suggested_deposit = estimated_cost * 0.2
        
        event = frappe.get_doc({
            "doctype": "Restaurant Event Booking",
            "event_id": event_id,
            "event_type": data["event_type"],
            "event_name": data["event_name"],
            "host_name": data["host_name"],
            "host_contact": data["host_contact"],
            "host_email": data.get("host_email"),
            "event_date": data["event_date"],
            "event_time": data["event_time"],
            "duration_hours": data.get("duration_hours", 3.0),
            "expected_guests": data["expected_guests"],
            "private_dining_room": data.get("private_dining_room"),
            "special_requirements": data.get("special_requirements"),
            "menu_preferences": data.get("menu_preferences"),
            "dietary_restrictions": data.get("dietary_restrictions"),
            "budget_range": data.get("budget_range"),
            "deposit_amount": suggested_deposit,
            "deposit_status": "Pending",
            "event_status": "Inquiry"
        })
        
        event.insert()
        
        # Send confirmation email (simulate)
        send_event_confirmation_email(event)
        
        return {
            "success": True,
            "message": "Event booking created successfully",
            "data": {
                "event_id": event_id,
                "estimated_cost": estimated_cost,
                "suggested_deposit": suggested_deposit,
                "next_steps": [
                    "Review event details",
                    "Confirm availability",
                    "Send proposal",
                    "Collect deposit"
                ]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating event booking: {str(e)}"
        }

def estimate_event_cost(event_data):
    """Estimate event cost based on parameters"""
    base_cost_per_person = 75  # Base cost per guest
    
    guests = int(event_data.get("expected_guests", 0))
    duration = float(event_data.get("duration_hours", 3.0))
    
    base_cost = guests * base_cost_per_person
    
    # Duration multiplier
    if duration > 4:
        base_cost *= 1.2
    elif duration > 6:
        base_cost *= 1.4
    
    # Event type multiplier
    event_type_multipliers = {
        "Wedding Reception": 1.5,
        "Corporate Event": 1.3,
        "Wine Tasting": 1.2,
        "Chef's Table": 1.8,
        "Birthday Party": 1.0,
        "Private Dining": 1.1
    }
    
    event_type = event_data.get("event_type", "Private Dining")
    multiplier = event_type_multipliers.get(event_type, 1.0)
    
    estimated_cost = base_cost * multiplier
    
    return round(estimated_cost, 2)

@frappe.whitelist(allow_guest=True)
def check_event_availability(event_date, event_time, duration_hours, room_preference=None):
    """Check availability for event booking"""
    try:
        # Get existing bookings for the date
        existing_bookings = frappe.get_all("Restaurant Event Booking",
            filters={
                "event_date": event_date,
                "event_status": ["not in", ["Cancelled"]]
            },
            fields=["event_time", "duration_hours", "private_dining_room"]
        )
        
        # Check room availability
        available_rooms = get_available_rooms(event_date, event_time, duration_hours, existing_bookings)
        
        # Check staff availability
        staff_availability = check_staff_availability(event_date, event_time, duration_hours)
        
        # Suggest alternative times if requested time is unavailable
        alternative_times = []
        if room_preference and room_preference not in available_rooms:
            alternative_times = suggest_alternative_times(event_date, duration_hours, room_preference)
        
        return {
            "success": True,
            "data": {
                "date": event_date,
                "time": event_time,
                "duration": duration_hours,
                "available_rooms": available_rooms,
                "staff_available": staff_availability,
                "alternative_times": alternative_times,
                "fully_available": len(available_rooms) > 0 and staff_availability
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error checking availability: {str(e)}"
        }

def get_available_rooms(event_date, event_time, duration_hours, existing_bookings):
    """Get list of available private dining rooms"""
    all_rooms = [
        "Main Private Room",
        "VIP Suite", 
        "Wine Cellar Room",
        "Chef's Table",
        "Outdoor Terrace",
        "Rooftop Space"
    ]
    
    # Filter out booked rooms
    booked_rooms = []
    for booking in existing_bookings:
        if is_time_conflict(event_time, duration_hours, booking.event_time, booking.duration_hours):
            booked_rooms.append(booking.private_dining_room)
    
    available_rooms = [room for room in all_rooms if room not in booked_rooms]
    
    return available_rooms


# ============================================================================
# CUSTOMER FEEDBACK SYSTEM  
# ============================================================================

@frappe.whitelist(allow_guest=True)
def submit_customer_feedback(feedback_data):
    """Submit customer feedback"""
    try:
        data = json.loads(feedback_data) if isinstance(feedback_data, str) else feedback_data
        
        feedback_id = f"FB-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        # Determine priority based on ratings and feedback type
        priority = determine_feedback_priority(data)
        
        feedback = frappe.get_doc({
            "doctype": "Restaurant Customer Feedback",
            "feedback_id": feedback_id,
            "customer_id": data.get("customer_id"),
            "order_id": data.get("order_id"),
            "table_number": data.get("table_number"),
            "visit_date": data.get("visit_date", frappe.utils.nowdate()),
            "feedback_type": data["feedback_type"],
            "overall_rating": data["overall_rating"],
            "food_quality_rating": data.get("food_quality_rating"),
            "service_rating": data.get("service_rating"),
            "ambiance_rating": data.get("ambiance_rating"),
            "value_rating": data.get("value_rating"),
            "speed_rating": data.get("speed_rating"),
            "staff_member_mentioned": data.get("staff_member_mentioned"),
            "positive_comments": data.get("positive_comments"),
            "negative_comments": data.get("negative_comments"),
            "suggestions": data.get("suggestions"),
            "would_recommend": data.get("would_recommend"),
            "likelihood_to_return": data.get("likelihood_to_return"),
            "feedback_source": data.get("feedback_source", "In-Person"),
            "priority": priority,
            "status": "New"
        })
        
        feedback.insert()
        
        # Auto-trigger actions based on feedback
        trigger_feedback_actions(feedback)
        
        return {
            "success": True,
            "message": "Thank you for your feedback!",
            "data": {
                "feedback_id": feedback_id,
                "priority": priority,
                "follow_up_expected": priority in ["High", "Urgent"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error submitting feedback: {str(e)}"
        }

def determine_feedback_priority(data):
    """Determine feedback priority based on content"""
    overall_rating = int(data.get("overall_rating", "3").split()[0])
    feedback_type = data.get("feedback_type", "")
    
    # High priority conditions
    if overall_rating <= 2:
        return "High"
    
    if feedback_type in ["Complaint", "Food Issue", "Service Issue", "Billing Issue"]:
        return "High"
    
    if data.get("negative_comments") and len(data.get("negative_comments", "")) > 50:
        return "Medium"
    
    if feedback_type == "Staff Recognition":
        return "Medium"
    
    return "Low"

def trigger_feedback_actions(feedback):
    """Trigger automatic actions based on feedback"""
    try:
        # High priority feedback triggers immediate alerts
        if feedback.priority in ["High", "Urgent"]:
            send_management_alert(feedback)
        
        # Positive feedback triggers staff recognition
        if feedback.staff_member_mentioned and feedback.overall_rating >= "4":
            record_staff_recognition(feedback.staff_member_mentioned, feedback.positive_comments)
        
        # Low ratings trigger follow-up requirements
        if int(feedback.overall_rating.split()[0]) <= 3:
            schedule_follow_up(feedback)
            
    except Exception as e:
        frappe.log_error(f"Error triggering feedback actions: {str(e)}")

@frappe.whitelist(allow_guest=True)
def get_feedback_analytics(date_from=None, date_to=None):
    """Get comprehensive feedback analytics"""
    try:
        filters = {}
        
        if date_from:
            filters["visit_date"] = [">=", date_from]
        if date_to:
            if "visit_date" in filters:
                filters["visit_date"] = ["between", [date_from, date_to]]
            else:
                filters["visit_date"] = ["<=", date_to]
        
        feedbacks = frappe.get_all("Restaurant Customer Feedback",
            filters=filters,
            fields=[
                "feedback_id", "feedback_type", "overall_rating", "food_quality_rating",
                "service_rating", "ambiance_rating", "value_rating", "speed_rating",
                "would_recommend", "likelihood_to_return", "visit_date", "priority", "status"
            ]
        )
        
        # Calculate analytics
        total_feedback = len(feedbacks)
        
        # Average ratings
        ratings = {
            "overall": calculate_average_rating([f.overall_rating for f in feedbacks]),
            "food_quality": calculate_average_rating([f.food_quality_rating for f in feedbacks if f.food_quality_rating]),
            "service": calculate_average_rating([f.service_rating for f in feedbacks if f.service_rating]),
            "ambiance": calculate_average_rating([f.ambiance_rating for f in feedbacks if f.ambiance_rating]),
            "value": calculate_average_rating([f.value_rating for f in feedbacks if f.value_rating]),
            "speed": calculate_average_rating([f.speed_rating for f in feedbacks if f.speed_rating])
        }
        
        # Satisfaction metrics
        satisfied_customers = len([f for f in feedbacks if int(f.overall_rating.split()[0]) >= 4])
        satisfaction_rate = (satisfied_customers / total_feedback * 100) if total_feedback > 0 else 0
        
        # Recommendation metrics  
        recommend_yes = len([f for f in feedbacks if f.would_recommend == "Yes"])
        nps_score = calculate_nps_score(feedbacks)
        
        # Feedback trends
        feedback_by_type = {}
        for feedback in feedbacks:
            fb_type = feedback.feedback_type
            if fb_type not in feedback_by_type:
                feedback_by_type[fb_type] = 0
            feedback_by_type[fb_type] += 1
        
        return {
            "success": True,
            "data": {
                "summary": {
                    "total_feedback": total_feedback,
                    "satisfaction_rate": round(satisfaction_rate, 1),
                    "nps_score": nps_score,
                    "recommendation_rate": round((recommend_yes / total_feedback * 100) if total_feedback > 0 else 0, 1)
                },
                "average_ratings": ratings,
                "feedback_by_type": feedback_by_type,
                "period": {
                    "from": date_from,
                    "to": date_to
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting feedback analytics: {str(e)}"
        }

def calculate_average_rating(ratings):
    """Calculate average rating from string ratings"""
    if not ratings:
        return 0
    
    total = 0
    count = 0
    
    for rating in ratings:
        if rating:
            # Extract number from "4 - Very Good" format
            rating_value = int(rating.split()[0])
            total += rating_value
            count += 1
    
    return round(total / count, 1) if count > 0 else 0

def calculate_nps_score(feedbacks):
    """Calculate Net Promoter Score"""
    ratings = []
    for feedback in feedbacks:
        if feedback.overall_rating:
            rating = int(feedback.overall_rating.split()[0])
            ratings.append(rating)
    
    if not ratings:
        return 0
    
    promoters = len([r for r in ratings if r >= 4])  # 4-5 stars
    detractors = len([r for r in ratings if r <= 2])  # 1-2 stars
    
    nps = ((promoters - detractors) / len(ratings)) * 100
    return round(nps, 1)

# ============================================================================
# HELPER FUNCTIONS FOR ALL SYSTEMS
# ============================================================================

def generate_referral_code(customer_id):
    """Generate unique referral code for customer"""
    return f"REF{customer_id[-4:].upper()}{frappe.utils.random_string(4).upper()}"

def get_bonus_points(reason):
    """Get bonus points based on reason"""
    bonus_points = {
        "birthday": 100,
        "anniversary": 150,
        "referral": 200,
        "review": 50,
        "social_share": 25,
        "first_visit": 100,
        "large_order": 50
    }
    return bonus_points.get(reason, 0)

def get_tier_upgrade_reward(tier):
    """Get bonus points for tier upgrade"""
    upgrade_rewards = {
        "Silver": 100,
        "Gold": 250,
        "Platinum": 500,
        "VIP": 1000,
        "Founder": 2500
    }
    return upgrade_rewards.get(tier, 0)

def get_next_tier(current_tier):
    """Get next tier in progression"""
    tier_progression = {
        "Bronze": "Silver",
        "Silver": "Gold", 
        "Gold": "Platinum",
        "Platinum": "VIP",
        "VIP": "Founder",
        "Founder": "Founder"  # Max tier
    }
    return tier_progression.get(current_tier, "Bronze")

def calculate_points_to_next_tier(loyalty):
    """Calculate points needed for next tier"""
    tier_thresholds = {
        "Bronze": 500,
        "Silver": 1500,
        "Gold": 5000,
        "Platinum": 15000,
        "VIP": 50000,
        "Founder": 0  # Max tier
    }
    
    current_tier = loyalty.current_tier
    next_tier = get_next_tier(current_tier)
    
    if next_tier == current_tier:  # Already at max tier
        return 0
    
    next_threshold = tier_thresholds.get(next_tier, 0)
    return max(0, next_threshold - loyalty.lifetime_points)

def calculate_redemption_value(redemption_type, points):
    """Calculate redemption value based on type and points"""
    redemption_rates = {
        "discount": 0.01,  # $0.01 per point
        "free_appetizer": 500,  # 500 points = free appetizer
        "free_dessert": 300,   # 300 points = free dessert
        "free_drink": 200,     # 200 points = free drink
        "percentage_off": 0.005  # $0.005 per point (5% off per 1000 points)
    }
    
    if redemption_type in ["free_appetizer", "free_dessert", "free_drink"]:
        return redemption_type.replace("_", " ").title()
    else:
        rate = redemption_rates.get(redemption_type, 0.01)
        return points * rate

def is_time_conflict(time1, duration1, time2, duration2):
    """Check if two time periods conflict"""
    try:
        # Convert times to minutes for easier calculation
        start1 = time_to_minutes(time1)
        end1 = start1 + (duration1 * 60)
        
        start2 = time_to_minutes(time2)
        end2 = start2 + (duration2 * 60)
        
        # Check for overlap
        return not (end1 <= start2 or end2 <= start1)
        
    except:
        return False

def time_to_minutes(time_str):
    """Convert time string to minutes since midnight"""
    try:
        if isinstance(time_str, str):
            parts = time_str.split(":")
            hours = int(parts[0])
            minutes = int(parts[1])
            return hours * 60 + minutes
        return 0
    except:
        return 0

def suggest_alternative_times(event_date, duration_hours, room_preference):
    """Suggest alternative times for event booking"""
    # This would implement logic to suggest available time slots
    # For now, return some sample alternatives
    alternatives = [
        {"time": "10:00", "room": room_preference},
        {"time": "14:00", "room": room_preference},
        {"time": "18:00", "room": room_preference}
    ]
    return alternatives

def check_staff_availability(event_date, event_time, duration_hours):
    """Check if sufficient staff available for event"""
    # This would check staff schedules
    # For now, assume staff is available
    return True

def send_event_confirmation_email(event):
    """Send confirmation email for event booking"""
    # This would integrate with email system
    frappe.log_error(f"Event confirmation email sent for {event.event_id}", "Event Booking")

def send_management_alert(feedback):
    """Send alert to management for high-priority feedback"""
    frappe.log_error(f"High priority feedback alert: {feedback.feedback_id}", "Feedback Alert")

def record_staff_recognition(staff_member, comments):
    """Record positive staff recognition"""
    frappe.log_error(f"Staff recognition: {staff_member} - {comments}", "Staff Recognition")

def schedule_follow_up(feedback):
    """Schedule follow-up for negative feedback"""
    # Set follow-up date and flag
    frappe.db.set_value("Restaurant Customer Feedback", feedback.name, {
        "follow_up_required": 1,
        "follow_up_date": frappe.utils.add_days(frappe.utils.nowdate(), 3)
    })

# ============================================================================
# INTEGRATION APIS - CONNECTING ALL SYSTEMS
# ============================================================================

@frappe.whitelist(allow_guest=True)
def process_order_completion(order_id):
    """Complete order processing with all integrations"""
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        results = {}
        
        # 1. Add loyalty points
        if order.customer_id:
            loyalty_result = add_loyalty_points(order.customer_id, order.total_amount)
            results["loyalty"] = loyalty_result
        
        # 2. Trigger complimentary items
        if order.customer_id:
            comp_result = auto_trigger_complimentary(order.customer_id, order_id)
            results["complimentary"] = comp_result
        
        # 3. Request feedback
        feedback_request = {
            "customer_id": order.customer_id,
            "order_id": order_id,
            "table_number": order.table_number,
            "feedback_request_sent": True
        }
        results["feedback_request"] = feedback_request
        
        return {
            "success": True,
            "message": "Order completed with all integrations",
            "data": results
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing order completion: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_customer_360_view(customer_id):
    """Get complete 360-degree view of customer"""
    try:
        # Customer profile
        customer = frappe.get_doc("Restaurant Customer Profile", customer_id)
        
        # Loyalty information
        try:
            loyalty = frappe.get_doc("Restaurant Loyalty Program", customer_id)
        except:
            loyalty = None
        
        # Recent orders
        recent_orders = frappe.get_all("Restaurant Order",
            filters={"customer_id": customer_id},
            fields=["order_id", "order_date", "total_amount", "order_status"],
            order_by="order_date desc",
            limit=10
        )
        
        # Feedback history
        feedback_history = frappe.get_all("Restaurant Customer Feedback",
            filters={"customer_id": customer_id},
            fields=["feedback_id", "visit_date", "overall_rating", "feedback_type"],
            order_by="visit_date desc",
            limit=5
        )
        
        # Complimentary items received
        complimentary_items = frappe.get_all("Restaurant Complimentary Item",
            filters={"customer_id": customer_id},
            fields=["complimentary_id", "item_name", "date_given", "trigger_type"],
            order_by="date_given desc",
            limit=5
        )
        
        # Calculate customer metrics
        total_spent = sum([order.total_amount for order in recent_orders])
        avg_order_value = total_spent / len(recent_orders) if recent_orders else 0
        avg_rating = calculate_average_rating([f.overall_rating for f in feedback_history])
        
        return {
            "success": True,
            "data": {
                "customer_profile": {
                    "customer_id": customer.customer_id,
                    "full_name": customer.full_name,
                    "email": customer.email,
                    "phone": customer.phone,
                    "membership_tier": customer.membership_tier,
                    "customer_since": customer.customer_since,
                    "total_visits": customer.total_visits,
                    "vip_status": customer.vip_status
                },
                "loyalty_info": {
                    "current_points": loyalty.current_points if loyalty else 0,
                    "lifetime_points": loyalty.lifetime_points if loyalty else 0,
                    "current_tier": loyalty.current_tier if loyalty else "Bronze",
                    "referral_code": loyalty.referral_code if loyalty else None
                },
                "order_history": {
                    "recent_orders": recent_orders,
                    "total_spent": total_spent,
                    "average_order_value": round(avg_order_value, 2)
                },
                "feedback_summary": {
                    "recent_feedback": feedback_history,
                    "average_rating": avg_rating,
                    "total_feedback_count": len(feedback_history)
                },
                "complimentary_history": complimentary_items,
                "insights": {
                    "customer_value": calculate_customer_value_score(customer, loyalty, recent_orders),
                    "satisfaction_level": get_satisfaction_level(avg_rating),
                    "engagement_level": calculate_engagement_level(customer, recent_orders, feedback_history)
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting customer 360 view: {str(e)}"
        }

def calculate_customer_value_score(customer, loyalty, orders):
    """Calculate customer value score"""
    # Simple scoring algorithm
    score = 0
    
    # Spending score (40%)
    total_spent = sum([order.total_amount for order in orders])
    spending_score = min(total_spent / 100, 40)  # Max 40 points for $4000+ spent
    score += spending_score
    
    # Loyalty score (30%)
    if loyalty:
        loyalty_score = min(loyalty.lifetime_points / 100, 30)  # Max 30 points for 3000+ points
        score += loyalty_score
    
    # Frequency score (30%)
    frequency_score = min(customer.total_visits * 2, 30)  # Max 30 points for 15+ visits
    score += frequency_score
    
    return round(score, 1)

def get_satisfaction_level(avg_rating):
    """Get satisfaction level from average rating"""
    if avg_rating >= 4.5:
        return "Highly Satisfied"
    elif avg_rating >= 4.0:
        return "Satisfied" 
    elif avg_rating >= 3.0:
        return "Neutral"
    elif avg_rating >= 2.0:
        return "Dissatisfied"
    else:
        return "Highly Dissatisfied"

def calculate_engagement_level(customer, orders, feedback):
    """Calculate customer engagement level"""
    # Based on visit frequency, feedback participation, etc.
    engagement_score = 0
    
    # Recent activity
    if orders and len(orders) > 0:
        engagement_score += 30
    
    # Feedback participation
    if feedback and len(feedback) > 0:
        engagement_score += 25
    
    # Membership tenure
    if customer.total_visits >= 10:
        engagement_score += 25
    
    # VIP status
    if customer.vip_status:
        engagement_score += 20
    
    if engagement_score >= 80:
        return "Highly Engaged"
    elif engagement_score >= 60:
        return "Engaged"
    elif engagement_score >= 40:
        return "Moderately Engaged"
    else:
        return "Low Engagement"
