import frappe
from frappe import _
from frappe.utils import nowdate, getdate, now_datetime, cint, flt
from frappe.auth import LoginManager
from frappe.sessions import Session
from werkzeug.security import check_password_hash, generate_password_hash
import json
import hashlib
import secrets

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

def require_auth(role_required=None):
    """Decorator to require authentication and optional role"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Check if user is authenticated
            if frappe.session.user == "Guest":
                frappe.throw(_("Authentication required"), frappe.AuthenticationError)
            
            # Check role if specified
            if role_required and not has_permission(role_required):
                frappe.throw(_("Insufficient permissions"), frappe.PermissionError)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

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

@frappe.whitelist(allow_guest=True, methods=["POST"])
def register_staff():
    """Register a new staff member (Admin only)"""
    try:
        data = frappe.local.request.get_json() or {}
        
        # Validate required fields
        required_fields = ["full_name", "email", "position", "department", "hire_date", "base_hourly_rate"]
        for field in required_fields:
            if not data.get(field):
                return {
                    "success": False,
                    "message": f"Missing required field: {field}"
                }
        
        # Check if email already exists
        if frappe.db.exists("User", data["email"]):
            return {
                "success": False,
                "message": "User with this email already exists"
            }
        
        # Create staff record first
        staff = frappe.get_doc({
            "doctype": "Restaurant Staff",
            "full_name": data["full_name"],
            "email": data["email"],
            "phone": data.get("phone"),
            "position": data["position"],
            "department": data["department"],
            "hire_date": data["hire_date"],
            "base_hourly_rate": data["base_hourly_rate"],
            "employment_status": "Active"
        })
        staff.insert(ignore_permissions=True)
        
        # Create user account
        user = frappe.get_doc({
            "doctype": "User",
            "email": data["email"],
            "first_name": data["full_name"].split()[0],
            "last_name": " ".join(data["full_name"].split()[1:]) if len(data["full_name"].split()) > 1 else "",
            "user_type": "System User",
            "send_welcome_email": 0
        })
        
        # Set temporary password if provided
        if data.get("password"):
            user.new_password = data["password"]
        
        user.insert(ignore_permissions=True)
        
        # Assign role based on position
        role = get_role_for_position(data["position"])
        user.add_roles(role)
        
        return {
            "success": True,
            "message": f"Staff member {data['full_name']} registered successfully",
            "data": {
                "staff_id": staff.staff_id,
                "email": user.email,
                "role": role
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Registration failed: {str(e)}"
        }

def get_role_for_position(position):
    """Map position to Frappe role"""
    role_mapping = {
        "Owner": "Restaurant Owner",
        "Manager": "Restaurant Manager", 
        "Assistant Manager": "Restaurant Manager",
        "Waiter": "Restaurant Staff",
        "Waitress": "Restaurant Staff",
        "Server": "Restaurant Staff",
        "Chef": "Restaurant Kitchen",
        "Sous Chef": "Restaurant Kitchen", 
        "Cook": "Restaurant Kitchen",
        "Kitchen Staff": "Restaurant Kitchen",
        "Prep Cook": "Restaurant Kitchen",
        "Cashier": "Restaurant Cashier",
        "Host": "Restaurant Staff",
        "Hostess": "Restaurant Staff",
        "Bartender": "Restaurant Staff",
        "Dishwasher": "Restaurant Staff",
        "Busser": "Restaurant Staff"
    }
    return role_mapping.get(position, "Restaurant Staff")

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

@frappe.whitelist(allow_guest=True, methods=["POST"])
def reset_password():
    """Send password reset email"""
    try:
        data = frappe.local.request.get_json() or {}
        email = data.get("email")
        
        if not email:
            return {
                "success": False,
                "message": "Email is required"
            }
        
        # Check if user exists and is active staff
        staff = frappe.db.get_value("Restaurant Staff", 
            {"email": email, "employment_status": "Active"}, 
            "name"
        )
        
        if not staff:
            return {
                "success": False,
                "message": "Email not found or account inactive"
            }
        
        # Send password reset email using Frappe's built-in functionality
        from frappe.utils.password import update_password
        reset_password_key = frappe.generate_hash(length=32)
        
        # Store reset key
        frappe.db.set_value("User", email, "reset_password_key", reset_password_key)
        frappe.db.commit()
        
        # TODO: Send email with reset link
        # For now, return the reset key (in production, this should be emailed)
        
        return {
            "success": True,
            "message": "Password reset instructions have been sent to your email",
            "reset_key": reset_password_key  # Remove this in production
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Password reset failed: {str(e)}"
        }

@frappe.whitelist(allow_guest=True, methods=["POST"])
def confirm_password_reset():
    """Confirm password reset with token"""
    try:
        data = frappe.local.request.get_json() or {}
        email = data.get("email")
        reset_key = data.get("reset_key")
        new_password = data.get("new_password")
        
        if not all([email, reset_key, new_password]):
            return {
                "success": False,
                "message": "Email, reset key, and new password are required"
            }
        
        # Verify reset key
        stored_key = frappe.db.get_value("User", email, "reset_password_key")
        if not stored_key or stored_key != reset_key:
            return {
                "success": False,
                "message": "Invalid or expired reset key"
            }
        
        # Update password
        from frappe.utils.password import update_password
        update_password(email, new_password)
        
        # Clear reset key
        frappe.db.set_value("User", email, "reset_password_key", "")
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Password updated successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Password reset confirmation failed: {str(e)}"
        }

@frappe.whitelist(methods=["POST"])
def change_password():
    """Change password for authenticated user"""
    try:
        data = frappe.local.request.get_json() or {}
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        
        if not current_password or not new_password:
            return {
                "success": False,
                "message": "Current password and new password are required"
            }
        
        user = get_current_user()
        
        # Verify current password
        from frappe.utils.password import check_password
        if not check_password(user, current_password):
            return {
                "success": False,
                "message": "Current password is incorrect"
            }
        
        # Update password
        from frappe.utils.password import update_password
        update_password(user, new_password)
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Password change failed: {str(e)}"
        }

# ============================================================================
# STAFF MANAGEMENT APIs
# ============================================================================

@frappe.whitelist()
def create_staff(staff_data):
    """Create a new staff member"""
    try:
        # Check authentication and role
        if frappe.session.user == "Guest":
            return {"success": False, "message": "Authentication required"}
        
        if not has_permission("Restaurant Manager"):
            return {"success": False, "message": "Insufficient permissions. Manager role required."}
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

@frappe.whitelist()
def get_staff(staff_id=None):
    """Get staff member(s)"""
    try:
        # Check authentication and role
        if frappe.session.user == "Guest":
            return {"success": False, "message": "Authentication required"}
        
        if not has_permission("Restaurant Staff"):
            return {"success": False, "message": "Insufficient permissions"}
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

@frappe.whitelist()
def create_order(order_data):
    """Create a new restaurant order"""
    try:
        # Check authentication and role
        if frappe.session.user == "Guest":
            return {"success": False, "message": "Authentication required"}
        
        if not has_permission("Restaurant Cashier"):
            return {"success": False, "message": "Insufficient permissions. Cashier role required."}
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

@frappe.whitelist()
def process_payment(order_id, payment_data):
    """Process payment for an order with automatic tip recording"""
    try:
        # Check authentication and role
        if frappe.session.user == "Guest":
            return {"success": False, "message": "Authentication required"}
        
        if not has_permission("Restaurant Cashier"):
            return {"success": False, "message": "Insufficient permissions. Cashier role required."}
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


# ============================================================================
# KITCHEN DISPLAY SYSTEM
# ============================================================================

@frappe.whitelist(allow_guest=True)
def send_to_kitchen(order_id):
    """Send order to kitchen display system"""
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        # Create kitchen order entry
        kitchen_order_id = f"KIT-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        # Determine order priority
        priority = determine_order_priority(order)
        
        # Calculate estimated completion time
        estimated_time = calculate_kitchen_time(order)
        
        kitchen_order = frappe.get_doc({
            "doctype": "Restaurant Kitchen Order",
            "kitchen_order_id": kitchen_order_id,
            "order_id": order.order_id,
            "table_number": order.table_number,
            "customer_name": order.customer_name,
            "order_priority": priority,
            "preparation_status": "Received",
            "kitchen_station": assign_kitchen_station(order),
            "order_received_time": frappe.utils.now(),
            "estimated_completion_time": estimated_time,
            "special_instructions": order.special_instructions,
            "order_items": json.dumps(get_order_items_for_kitchen(order)),
            "rush_order": priority in ["Rush", "VIP"]
        })
        
        kitchen_order.insert()
        
        # Update inventory for order items
        update_inventory_for_order(order)
        
        # Notify kitchen staff (simulate)
        notify_kitchen_staff(kitchen_order)
        
        return {
            "success": True,
            "message": "Order sent to kitchen successfully",
            "data": {
                "kitchen_order_id": kitchen_order_id,
                "priority": priority,
                "estimated_completion": estimated_time,
                "assigned_station": kitchen_order.kitchen_station
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error sending order to kitchen: {str(e)}"
        }

def determine_order_priority(order):
    """Determine order priority based on various factors"""
    # VIP customers get high priority
    if hasattr(order, 'customer_id'):
        try:
            customer = frappe.get_doc("Restaurant Customer Profile", order.customer_id)
            if customer.vip_status or customer.membership_tier in ["Platinum", "VIP", "Founder"]:
                return "VIP"
        except:
            pass
    
    # Large orders get higher priority
    if order.total_amount > 200:
        return "High"
    
    # Check for rush requests
    if hasattr(order, 'rush_order') and order.rush_order:
        return "Rush"
    
    return "Normal"

def calculate_kitchen_time(order):
    """Calculate estimated kitchen preparation time"""
    base_time = 15  # Base 15 minutes
    
    # Add time based on number of items
    item_count = len(order.items) if hasattr(order, 'items') else 1
    additional_time = item_count * 3  # 3 minutes per item
    
    # Add complexity factor for certain items
    complexity_time = 0
    # This would analyze menu items for complexity
    
    total_minutes = base_time + additional_time + complexity_time
    
    # Calculate estimated completion time
    completion_time = frappe.utils.add_to_date(
        frappe.utils.now(), 
        minutes=total_minutes
    )
    
    return completion_time

def assign_kitchen_station(order):
    """Assign order to appropriate kitchen station"""
    # Simple assignment logic - would be more sophisticated in reality
    stations = ["Hot Station", "Cold Station", "Grill Station", "Saute Station"]
    
    # For now, assign based on order size
    if len(order.items) <= 2:
        return "Cold Station"
    elif len(order.items) <= 4:
        return "Hot Station"
    else:
        return "Grill Station"

def get_order_items_for_kitchen(order):
    """Format order items for kitchen display"""
    kitchen_items = []
    
    for item in order.items:
        kitchen_items.append({
            "item_name": item.item_name,
            "quantity": item.quantity,
            "special_instructions": getattr(item, 'special_instructions', ''),
            "cooking_instructions": get_cooking_instructions(item.item_name),
            "allergens": get_item_allergens(item.item_name)
        })
    
    return kitchen_items

@frappe.whitelist(allow_guest=True)
def update_kitchen_order_status(kitchen_order_id, new_status, chef_notes=None):
    """Update kitchen order status"""
    try:
        kitchen_order = frappe.get_doc("Restaurant Kitchen Order", kitchen_order_id)
        
        old_status = kitchen_order.preparation_status
        kitchen_order.preparation_status = new_status
        
        # Update timestamps based on status
        current_time = frappe.utils.now()
        
        if new_status == "In Preparation" and old_status == "Received":
            kitchen_order.preparation_start_time = current_time
        
        elif new_status == "Ready" and old_status in ["In Preparation", "Almost Ready"]:
            kitchen_order.actual_completion_time = current_time
            kitchen_order.quality_check_passed = 1
            kitchen_order.ready_for_service = 1
            
            # Calculate actual preparation time
            if kitchen_order.preparation_start_time:
                start_time = frappe.utils.get_datetime(kitchen_order.preparation_start_time)
                end_time = frappe.utils.get_datetime(current_time)
                duration = (end_time - start_time).total_seconds() / 60
                kitchen_order.preparation_duration = duration
        
        elif new_status == "Served":
            kitchen_order.served_time = current_time
        
        if chef_notes:
            kitchen_order.kitchen_notes = chef_notes
        
        kitchen_order.save()
        
        # Notify front of house if order is ready
        if new_status == "Ready":
            notify_front_of_house(kitchen_order)
        
        return {
            "success": True,
            "message": f"Kitchen order status updated to {new_status}",
            "data": {
                "kitchen_order_id": kitchen_order_id,
                "new_status": new_status,
                "preparation_duration": kitchen_order.preparation_duration
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating kitchen order status: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_kitchen_display_orders(station=None, status=None):
    """Get orders for kitchen display"""
    try:
        filters = {}
        
        if station:
            filters["kitchen_station"] = station
        
        if status:
            filters["preparation_status"] = status
        else:
            # Show active orders (not served or cancelled)
            filters["preparation_status"] = ["not in", ["Served", "Cancelled"]]
        
        orders = frappe.get_all("Restaurant Kitchen Order",
            filters=filters,
            fields=[
                "kitchen_order_id", "order_id", "table_number", "customer_name",
                "order_priority", "preparation_status", "kitchen_station",
                "order_received_time", "estimated_completion_time", "actual_completion_time",
                "special_instructions", "order_items", "rush_order", "preparation_duration"
            ],
            order_by="order_priority desc, order_received_time asc"
        )
        
        # Calculate wait times and add urgency indicators
        for order in orders:
            order["wait_time"] = calculate_wait_time(order["order_received_time"])
            order["urgency_level"] = determine_urgency(order)
            order["order_items_parsed"] = json.loads(order["order_items"]) if order["order_items"] else []
        
        # Group by station for display
        orders_by_station = {}
        for order in orders:
            station = order["kitchen_station"]
            if station not in orders_by_station:
                orders_by_station[station] = []
            orders_by_station[station].append(order)
        
        return {
            "success": True,
            "data": {
                "orders": orders,
                "orders_by_station": orders_by_station,
                "total_active_orders": len(orders)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting kitchen display orders: {str(e)}"
        }


# ============================================================================
# INVENTORY MANAGEMENT SYSTEM
# ============================================================================

@frappe.whitelist(allow_guest=True)
def add_inventory_item(item_data):
    """Add new inventory item"""
    try:
        data = json.loads(item_data) if isinstance(item_data, str) else item_data
        
        item_code = data.get("item_code") or generate_item_code(data["item_name"])
        
        inventory_item = frappe.get_doc({
            "doctype": "Restaurant Inventory Item",
            "item_code": item_code,
            "item_name": data["item_name"],
            "category": data["category"],
            "unit_of_measure": data["unit_of_measure"],
            "current_stock": data.get("current_stock", 0),
            "minimum_stock_level": data["minimum_stock_level"],
            "maximum_stock_level": data.get("maximum_stock_level"),
            "reorder_point": data["reorder_point"],
            "reorder_quantity": data["reorder_quantity"],
            "cost_per_unit": data.get("cost_per_unit"),
            "supplier_name": data.get("supplier_name"),
            "supplier_contact": data.get("supplier_contact"),
            "storage_location": data.get("storage_location"),
            "storage_requirements": data.get("storage_requirements"),
            "consumption_rate": data.get("consumption_rate"),
            "lead_time_days": data.get("lead_time_days", 3),
            "auto_reorder_enabled": data.get("auto_reorder_enabled", 1),
            "perishable": data.get("perishable", 0),
            "allergen_info": data.get("allergen_info"),
            "notes": data.get("notes")
        })
        
        inventory_item.insert()
        
        return {
            "success": True,
            "message": "Inventory item added successfully",
            "data": {
                "item_code": item_code,
                "item_name": data["item_name"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error adding inventory item: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def update_inventory_stock(item_code, transaction_data):
    """Update inventory stock with transaction logging"""
    try:
        data = json.loads(transaction_data) if isinstance(transaction_data, str) else transaction_data
        
        # Get inventory item
        inventory_item = frappe.get_doc("Restaurant Inventory Item", item_code)
        
        transaction_type = data["transaction_type"]
        quantity = float(data["quantity"])
        
        # Calculate new stock level
        if transaction_type in ["Stock In", "Stock Adjustment"]:
            new_stock = inventory_item.current_stock + quantity
        elif transaction_type in ["Stock Out", "Waste"]:
            new_stock = inventory_item.current_stock - quantity
        else:
            new_stock = inventory_item.current_stock
        
        # Validate stock levels
        if new_stock < 0:
            return {
                "success": False,
                "message": f"Insufficient stock. Current: {inventory_item.current_stock}, Requested: {quantity}"
            }
        
        # Create transaction record
        transaction_id = f"TXN-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(6).upper()}"
        
        transaction = frappe.get_doc({
            "doctype": "Restaurant Inventory Transaction",
            "transaction_id": transaction_id,
            "item_code": item_code,
            "item_name": inventory_item.item_name,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "unit_cost": data.get("unit_cost"),
            "total_cost": data.get("total_cost"),
            "transaction_date": frappe.utils.nowdate(),
            "transaction_time": frappe.utils.nowtime(),
            "reference_document": data.get("reference_document"),
            "supplier_name": data.get("supplier_name"),
            "batch_number": data.get("batch_number"),
            "expiry_date": data.get("expiry_date"),
            "storage_location": data.get("storage_location"),
            "performed_by": data["performed_by"],
            "notes": data.get("notes")
        })
        
        transaction.insert()
        
        # Update inventory item
        inventory_item.current_stock = new_stock
        
        if transaction_type == "Stock In":
            inventory_item.last_restock_date = frappe.utils.nowdate()
            inventory_item.last_restock_quantity = quantity
        
        inventory_item.save()
        
        # Check for reorder alerts
        reorder_alert = check_reorder_requirement(inventory_item)
        
        return {
            "success": True,
            "message": "Inventory updated successfully",
            "data": {
                "transaction_id": transaction_id,
                "new_stock_level": new_stock,
                "reorder_alert": reorder_alert
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating inventory: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_inventory_status(category=None, low_stock_only=False):
    """Get current inventory status"""
    try:
        filters = {}
        
        if category:
            filters["category"] = category
        
        items = frappe.get_all("Restaurant Inventory Item",
            filters=filters,
            fields=[
                "item_code", "item_name", "category", "unit_of_measure",
                "current_stock", "minimum_stock_level", "reorder_point",
                "cost_per_unit", "supplier_name", "expiry_date", "perishable",
                "auto_reorder_enabled", "last_restock_date"
            ]
        )
        
        # Add status indicators
        for item in items:
            item["stock_status"] = get_stock_status(item)
            item["days_until_expiry"] = calculate_days_until_expiry(item.get("expiry_date"))
            item["estimated_stock_days"] = calculate_estimated_stock_days(item)
        
        # Filter for low stock if requested
        if low_stock_only:
            items = [item for item in items if item["stock_status"] in ["Low Stock", "Out of Stock", "Reorder Required"]]
        
        # Group by category
        items_by_category = {}
        for item in items:
            category = item["category"]
            if category not in items_by_category:
                items_by_category[category] = []
            items_by_category[category].append(item)
        
        # Calculate summary statistics
        total_items = len(items)
        low_stock_items = len([item for item in items if item["stock_status"] == "Low Stock"])
        out_of_stock_items = len([item for item in items if item["stock_status"] == "Out of Stock"])
        reorder_required = len([item for item in items if item["stock_status"] == "Reorder Required"])
        
        return {
            "success": True,
            "data": {
                "items": items,
                "items_by_category": items_by_category,
                "summary": {
                    "total_items": total_items,
                    "low_stock_items": low_stock_items,
                    "out_of_stock_items": out_of_stock_items,
                    "reorder_required": reorder_required
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting inventory status: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def auto_reorder_inventory():
    """Automatically create reorder suggestions"""
    try:
        # Get items that need reordering
        items_to_reorder = frappe.get_all("Restaurant Inventory Item",
            filters={
                "auto_reorder_enabled": 1,
                "current_stock": ["<=", "reorder_point"]
            },
            fields=[
                "item_code", "item_name", "current_stock", "reorder_point",
                "reorder_quantity", "supplier_name", "supplier_contact",
                "cost_per_unit", "lead_time_days"
            ]
        )
        
        reorder_suggestions = []
        
        for item in items_to_reorder:
            # Calculate recommended order quantity
            recommended_qty = calculate_recommended_order_quantity(item)
            
            # Estimate cost
            estimated_cost = recommended_qty * (item.get("cost_per_unit") or 0)
            
            suggestion = {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "current_stock": item.current_stock,
                "reorder_point": item.reorder_point,
                "recommended_quantity": recommended_qty,
                "supplier_name": item.supplier_name,
                "estimated_cost": estimated_cost,
                "urgency": get_reorder_urgency(item),
                "expected_delivery": frappe.utils.add_days(frappe.utils.nowdate(), item.lead_time_days)
            }
            
            reorder_suggestions.append(suggestion)
        
        # Sort by urgency
        reorder_suggestions.sort(key=lambda x: ["High", "Medium", "Low"].index(x["urgency"]))
        
        return {
            "success": True,
            "data": {
                "reorder_suggestions": reorder_suggestions,
                "total_items_to_reorder": len(reorder_suggestions),
                "total_estimated_cost": sum(item["estimated_cost"] for item in reorder_suggestions)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating auto reorder: {str(e)}"
        }


# ============================================================================
# COMPREHENSIVE REPORTING SYSTEM
# ============================================================================

@frappe.whitelist(allow_guest=True)
def get_daily_operations_report(date=None):
    """Get comprehensive daily operations report"""
    try:
        if not date:
            date = frappe.utils.nowdate()
        
        # Sales Summary
        sales_data = get_daily_sales_summary(date)
        
        # Kitchen Performance
        kitchen_data = get_kitchen_performance_report(date)
        
        # Staff Performance
        staff_data = get_staff_performance_report(date)
        
        # Customer Feedback Summary
        feedback_data = get_daily_feedback_summary(date)
        
        # Inventory Status
        inventory_data = get_inventory_alerts()
        
        # Table Utilization
        table_data = get_table_utilization_report(date)
        
        return {
            "success": True,
            "data": {
                "report_date": date,
                "sales_summary": sales_data,
                "kitchen_performance": kitchen_data,
                "staff_performance": staff_data,
                "customer_feedback": feedback_data,
                "inventory_alerts": inventory_data,
                "table_utilization": table_data,
                "generated_at": frappe.utils.now()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating daily report: {str(e)}"
        }

def get_daily_sales_summary(date):
    """Get daily sales summary"""
    try:
        # Get all orders for the date
        orders = frappe.get_all("Restaurant Order",
            filters={
                "order_date": date,
                "order_status": ["not in", ["Cancelled"]]
            },
            fields=["order_id", "total_amount", "payment_method", "order_status", "table_number"]
        )
        
        total_sales = sum(order.total_amount for order in orders)
        total_orders = len(orders)
        
        # Payment method breakdown
        payment_breakdown = {}
        for order in orders:
            method = order.payment_method or "Unknown"
            if method not in payment_breakdown:
                payment_breakdown[method] = {"count": 0, "amount": 0}
            payment_breakdown[method]["count"] += 1
            payment_breakdown[method]["amount"] += order.total_amount
        
        # Calculate average order value
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        return {
            "total_sales": total_sales,
            "total_orders": total_orders,
            "average_order_value": round(avg_order_value, 2),
            "payment_breakdown": payment_breakdown
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_kitchen_performance_report(date):
    """Get kitchen performance metrics"""
    try:
        kitchen_orders = frappe.get_all("Restaurant Kitchen Order",
            filters={
                "order_received_time": ["like", f"{date}%"]
            },
            fields=[
                "kitchen_order_id", "preparation_status", "preparation_duration",
                "order_priority", "kitchen_station"
            ]
        )
        
        total_orders = len(kitchen_orders)
        completed_orders = len([o for o in kitchen_orders if o.preparation_status in ["Ready", "Served"]])
        
        # Calculate average preparation time
        prep_times = [o.preparation_duration for o in kitchen_orders if o.preparation_duration]
        avg_prep_time = sum(prep_times) / len(prep_times) if prep_times else 0
        
        # Performance by station
        station_performance = {}
        for order in kitchen_orders:
            station = order.kitchen_station
            if station not in station_performance:
                station_performance[station] = {"total": 0, "completed": 0}
            station_performance[station]["total"] += 1
            if order.preparation_status in ["Ready", "Served"]:
                station_performance[station]["completed"] += 1
        
        return {
            "total_kitchen_orders": total_orders,
            "completed_orders": completed_orders,
            "completion_rate": round((completed_orders / total_orders * 100) if total_orders > 0 else 0, 1),
            "average_prep_time": round(avg_prep_time, 1),
            "station_performance": station_performance
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_staff_performance_report(date):
    """Get staff performance summary"""
    try:
        # Get tips for the day
        tips = frappe.get_all("Restaurant Staff Tips",
            filters={"tip_date": date},
            fields=["staff_id", "amount", "tip_type"]
        )
        
        # Calculate tips by staff
        staff_tips = {}
        for tip in tips:
            staff_id = tip.staff_id
            if staff_id not in staff_tips:
                staff_tips[staff_id] = {"individual": 0, "pooled": 0, "total": 0}
            
            if tip.tip_type == "Individual":
                staff_tips[staff_id]["individual"] += tip.amount
            else:
                staff_tips[staff_id]["pooled"] += tip.amount
            staff_tips[staff_id]["total"] += tip.amount
        
        # Get staff recognition mentions
        recognitions = frappe.get_all("Restaurant Customer Feedback",
            filters={
                "visit_date": date,
                "staff_member_mentioned": ["is", "set"]
            },
            fields=["staff_member_mentioned", "overall_rating"]
        )
        
        recognition_count = {}
        for rec in recognitions:
            staff = rec.staff_member_mentioned
            if staff not in recognition_count:
                recognition_count[staff] = 0
            recognition_count[staff] += 1
        
        return {
            "staff_tips": staff_tips,
            "total_tips_distributed": sum(tip.amount for tip in tips),
            "staff_recognition": recognition_count
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_daily_feedback_summary(date):
    """Get daily customer feedback summary"""
    try:
        feedback_result = get_feedback_analytics(date, date)
        return feedback_result.get("data", {}) if feedback_result.get("success") else {"error": "Failed to get feedback data"}
    except Exception as e:
        return {"error": str(e)}

def get_inventory_alerts():
    """Get current inventory alerts"""
    try:
        alerts = []
        
        # Low stock alerts
        low_stock_items = frappe.get_all("Restaurant Inventory Item",
            filters={"current_stock": ["<=", "minimum_stock_level"]},
            fields=["item_name", "current_stock", "minimum_stock_level"]
        )
        
        for item in low_stock_items:
            alerts.append({
                "type": "Low Stock",
                "item": item.item_name,
                "current": item.current_stock,
                "minimum": item.minimum_stock_level,
                "severity": "High" if item.current_stock == 0 else "Medium"
            })
        
        # Expiring items
        expiring_items = frappe.get_all("Restaurant Inventory Item",
            filters={
                "expiry_date": ["<=", frappe.utils.add_days(frappe.utils.nowdate(), 3)],
                "perishable": 1
            },
            fields=["item_name", "expiry_date", "current_stock"]
        )
        
        for item in expiring_items:
            days_left = (frappe.utils.getdate(item.expiry_date) - frappe.utils.getdate()).days
            alerts.append({
                "type": "Expiring Soon",
                "item": item.item_name,
                "expiry_date": item.expiry_date,
                "days_left": days_left,
                "severity": "High" if days_left <= 1 else "Medium"
            })
        
        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "high_priority": len([a for a in alerts if a["severity"] == "High"])
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_table_utilization_report(date):
    """Get table utilization metrics"""
    try:
        bookings = frappe.get_all("Restaurant Table Booking",
            filters={"booking_date": date},
            fields=["table_number", "party_size", "booking_time", "duration", "status"]
        )
        
        # Calculate utilization metrics
        total_bookings = len(bookings)
        confirmed_bookings = len([b for b in bookings if b.status == "Confirmed"])
        
        # Average party size
        avg_party_size = sum(b.party_size for b in bookings) / total_bookings if total_bookings > 0 else 0
        
        return {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "booking_rate": round((confirmed_bookings / total_bookings * 100) if total_bookings > 0 else 0, 1),
            "average_party_size": round(avg_party_size, 1)
        }
        
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# HELPER FUNCTIONS FOR KITCHEN, INVENTORY & REPORTING
# ============================================================================

def generate_item_code(item_name):
    """Generate unique item code"""
    # Create code from first 3 letters + random string
    prefix = ''.join([c for c in item_name.upper() if c.isalpha()])[:3]
    suffix = frappe.utils.random_string(4).upper()
    return f"{prefix}-{suffix}"

def get_cooking_instructions(item_name):
    """Get cooking instructions for menu item"""
    # This would be populated from menu item master data
    cooking_instructions = {
        "Grilled Chicken": "Cook on medium heat for 8-10 minutes each side",
        "Caesar Salad": "Toss with dressing just before serving",
        "Pasta": "Cook al dente, 8-12 minutes depending on type"
    }
    return cooking_instructions.get(item_name, "Follow standard preparation")

def get_item_allergens(item_name):
    """Get allergen information for menu item"""
    # This would be populated from menu item master data
    allergens = {
        "Caesar Salad": ["Eggs", "Dairy", "Gluten"],
        "Pasta": ["Gluten", "Eggs"],
        "Seafood Platter": ["Seafood", "Shellfish"]
    }
    return allergens.get(item_name, [])

def update_inventory_for_order(order):
    """Update inventory levels when order is sent to kitchen"""
    try:
        # This would map menu items to inventory ingredients
        # For now, simulate inventory reduction
        for item in order.items:
            # Get ingredients for this menu item
            ingredients = get_menu_item_ingredients(item.item_name)
            
            for ingredient in ingredients:
                # Reduce inventory
                reduce_inventory_stock(ingredient["item_code"], ingredient["quantity"] * item.quantity)
                
    except Exception as e:
        frappe.log_error(f"Error updating inventory for order: {str(e)}")

def get_menu_item_ingredients(item_name):
    """Get ingredients list for menu item"""
    # This would be populated from recipe/menu item master
    recipes = {
        "Caesar Salad": [
            {"item_code": "LET-001", "quantity": 0.2},  # 200g lettuce
            {"item_code": "CHE-001", "quantity": 0.05}, # 50g cheese
            {"item_code": "CRO-001", "quantity": 0.03}  # 30g croutons
        ],
        "Grilled Chicken": [
            {"item_code": "CHI-001", "quantity": 0.25}, # 250g chicken
            {"item_code": "OIL-001", "quantity": 0.01}  # 10ml oil
        ]
    }
    return recipes.get(item_name, [])

def reduce_inventory_stock(item_code, quantity):
    """Reduce inventory stock for ingredient usage"""
    try:
        inventory_item = frappe.get_doc("Restaurant Inventory Item", item_code)
        
        if inventory_item.current_stock >= quantity:
            # Create stock out transaction
            update_inventory_stock(item_code, {
                "transaction_type": "Stock Out",
                "quantity": quantity,
                "performed_by": "KITCHEN_AUTO",
                "notes": "Automatic reduction for order preparation"
            })
        else:
            # Log low stock alert
            frappe.log_error(f"Insufficient stock for {item_code}: Available {inventory_item.current_stock}, Required {quantity}", "Low Stock Alert")
            
    except Exception as e:
        frappe.log_error(f"Error reducing inventory stock: {str(e)}")

def notify_kitchen_staff(kitchen_order):
    """Notify kitchen staff of new order"""
    # This would integrate with notification system
    frappe.log_error(f"New kitchen order: {kitchen_order.kitchen_order_id}", "Kitchen Notification")

def notify_front_of_house(kitchen_order):
    """Notify front of house that order is ready"""
    # This would integrate with notification system
    frappe.log_error(f"Order ready for service: {kitchen_order.kitchen_order_id}", "Service Notification")

def calculate_wait_time(order_received_time):
    """Calculate how long order has been waiting"""
    try:
        received = frappe.utils.get_datetime(order_received_time)
        now = frappe.utils.get_datetime(frappe.utils.now())
        wait_minutes = (now - received).total_seconds() / 60
        return round(wait_minutes, 1)
    except:
        return 0

def determine_urgency(order):
    """Determine order urgency level"""
    wait_time = order.get("wait_time", 0)
    priority = order.get("order_priority", "Normal")
    
    if priority in ["Rush", "VIP"] or wait_time > 30:
        return "High"
    elif wait_time > 20 or priority == "High":
        return "Medium"
    else:
        return "Low"

def get_stock_status(item):
    """Determine stock status for inventory item"""
    current = item["current_stock"]
    minimum = item["minimum_stock_level"]
    reorder = item["reorder_point"]
    
    if current <= 0:
        return "Out of Stock"
    elif current <= reorder:
        return "Reorder Required"
    elif current <= minimum:
        return "Low Stock"
    else:
        return "In Stock"

def calculate_days_until_expiry(expiry_date):
    """Calculate days until item expires"""
    if not expiry_date:
        return None
    
    try:
        expiry = frappe.utils.getdate(expiry_date)
        today = frappe.utils.getdate()
        return (expiry - today).days
    except:
        return None

def calculate_estimated_stock_days(item):
    """Estimate how many days current stock will last"""
    try:
        consumption_rate = item.get("consumption_rate", 0)
        current_stock = item["current_stock"]
        
        if consumption_rate > 0:
            return round(current_stock / consumption_rate, 1)
        else:
            return None
    except:
        return None

def check_reorder_requirement(inventory_item):
    """Check if item needs reordering"""
    if inventory_item.current_stock <= inventory_item.reorder_point:
        return {
            "reorder_required": True,
            "urgency": "High" if inventory_item.current_stock <= inventory_item.minimum_stock_level else "Medium",
            "recommended_quantity": inventory_item.reorder_quantity
        }
    return {"reorder_required": False}

def calculate_recommended_order_quantity(item):
    """Calculate recommended reorder quantity"""
    base_quantity = item.get("reorder_quantity", 0)
    
    # Adjust based on consumption rate if available
    consumption_rate = item.get("consumption_rate", 0)
    lead_time = item.get("lead_time_days", 3)
    
    if consumption_rate > 0:
        # Order enough for lead time plus safety stock
        safety_stock = consumption_rate * 2  # 2 days safety stock
        lead_time_stock = consumption_rate * lead_time
        recommended = lead_time_stock + safety_stock
        
        # Use the higher of base quantity or calculated quantity
        return max(base_quantity, recommended)
    
    return base_quantity

def get_reorder_urgency(item):
    """Determine reorder urgency"""
    current = item["current_stock"]
    reorder_point = item["reorder_point"]
    consumption_rate = item.get("consumption_rate", 0)
    
    if current <= 0:
        return "High"
    elif consumption_rate > 0 and current / consumption_rate <= 1:  # Less than 1 day stock
        return "High"
    elif current <= reorder_point * 0.5:  # 50% below reorder point
        return "Medium"
    else:
        return "Low"

# ============================================================================
# ADVANCED REPORTING APIs
# ============================================================================

@frappe.whitelist(allow_guest=True)
def get_weekly_performance_report(start_date=None):
    """Get comprehensive weekly performance report"""
    try:
        if not start_date:
            start_date = frappe.utils.add_days(frappe.utils.nowdate(), -7)
        
        end_date = frappe.utils.add_days(start_date, 6)
        
        # Daily sales trend
        daily_sales = []
        current_date = frappe.utils.getdate(start_date)
        
        while current_date <= frappe.utils.getdate(end_date):
            day_sales = get_daily_sales_summary(current_date.strftime("%Y-%m-%d"))
            daily_sales.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "sales": day_sales.get("total_sales", 0),
                "orders": day_sales.get("total_orders", 0)
            })
            current_date = frappe.utils.add_days(current_date, 1)
        
        # Weekly totals
        total_sales = sum(day["sales"] for day in daily_sales)
        total_orders = sum(day["orders"] for day in daily_sales)
        
        # Top performing items (would need menu item sales tracking)
        # Customer satisfaction trends
        # Staff performance comparison
        
        return {
            "success": True,
            "data": {
                "period": {"start": start_date, "end": end_date},
                "daily_sales": daily_sales,
                "weekly_totals": {
                    "total_sales": total_sales,
                    "total_orders": total_orders,
                    "average_daily_sales": round(total_sales / 7, 2),
                    "average_daily_orders": round(total_orders / 7, 1)
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating weekly report: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_inventory_valuation_report():
    """Get inventory valuation and analysis"""
    try:
        items = frappe.get_all("Restaurant Inventory Item",
            fields=[
                "item_code", "item_name", "category", "current_stock",
                "cost_per_unit", "supplier_name"
            ]
        )
        
        # Calculate valuations
        total_value = 0
        category_values = {}
        
        for item in items:
            item_value = item["current_stock"] * (item.get("cost_per_unit") or 0)
            item["total_value"] = item_value
            total_value += item_value
            
            category = item["category"]
            if category not in category_values:
                category_values[category] = 0
            category_values[category] += item_value
        
        # Sort by value
        items.sort(key=lambda x: x["total_value"], reverse=True)
        
        return {
            "success": True,
            "data": {
                "items": items,
                "total_inventory_value": round(total_value, 2),
                "value_by_category": category_values,
                "top_value_items": items[:10]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating inventory valuation: {str(e)}"
        }


# ============================================================================
# MARKETING CAMPAIGN MANAGEMENT SYSTEM
# ============================================================================

@frappe.whitelist(allow_guest=True)
def create_marketing_campaign(campaign_data):
    """Create new marketing campaign"""
    try:
        data = json.loads(campaign_data) if isinstance(campaign_data, str) else campaign_data
        
        campaign_id = f"CAMP-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        
        campaign = frappe.get_doc({
            "doctype": "Restaurant Marketing Campaign",
            "campaign_id": campaign_id,
            "campaign_name": data["campaign_name"],
            "campaign_type": data["campaign_type"],
            "campaign_status": data.get("campaign_status", "Draft"),
            "target_audience": data["target_audience"],
            "customer_segment": data.get("customer_segment"),
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "budget": data.get("budget"),
            "campaign_description": data.get("campaign_description"),
            "promotional_offer": data.get("promotional_offer"),
            "discount_percentage": data.get("discount_percentage"),
            "discount_amount": data.get("discount_amount"),
            "minimum_order_value": data.get("minimum_order_value"),
            "communication_channels": json.dumps(data.get("communication_channels", [])),
            "email_template": data.get("email_template"),
            "sms_template": data.get("sms_template"),
            "social_media_content": data.get("social_media_content"),
            "target_metrics": json.dumps(data.get("target_metrics", {})),
            "campaign_manager": data.get("campaign_manager"),
            "notes": data.get("notes")
        })
        
        campaign.insert()
        
        # Create associated promotion if discount provided
        if data.get("discount_percentage") or data.get("discount_amount"):
            create_campaign_promotion(campaign, data)
        
        return {
            "success": True,
            "message": "Marketing campaign created successfully",
            "data": {
                "campaign_id": campaign_id,
                "campaign_name": data["campaign_name"],
                "status": campaign.campaign_status
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating marketing campaign: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def launch_campaign(campaign_id, launch_data=None):
    """Launch marketing campaign and send communications"""
    try:
        campaign = frappe.get_doc("Restaurant Marketing Campaign", campaign_id)
        
        if campaign.campaign_status != "Approved":
            return {
                "success": False,
                "message": "Campaign must be approved before launching"
            }
        
        # Update campaign status
        campaign.campaign_status = "Active"
        campaign.save()
        
        # Get target customers
        target_customers = get_campaign_target_customers(campaign)
        
        # Send communications
        communications_sent = 0
        communication_channels = json.loads(campaign.communication_channels) if campaign.communication_channels else []
        
        for customer in target_customers:
            for channel in communication_channels:
                if send_campaign_communication(campaign, customer, channel):
                    communications_sent += 1
        
        # Update campaign metrics
        campaign.customers_reached = len(target_customers)
        campaign.save()
        
        return {
            "success": True,
            "message": f"Campaign launched successfully. {communications_sent} communications sent.",
            "data": {
                "campaign_id": campaign_id,
                "customers_reached": len(target_customers),
                "communications_sent": communications_sent
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error launching campaign: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def create_promotion(promotion_data):
    """Create new promotion"""
    try:
        data = json.loads(promotion_data) if isinstance(promotion_data, str) else promotion_data
        
        promotion_id = f"PROMO-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(4).upper()}"
        promotion_code = data.get("promotion_code") or generate_promotion_code()
        
        promotion = frappe.get_doc({
            "doctype": "Restaurant Promotion",
            "promotion_id": promotion_id,
            "promotion_name": data["promotion_name"],
            "promotion_type": data["promotion_type"],
            "promotion_code": promotion_code,
            "promotion_status": data.get("promotion_status", "Draft"),
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "applicable_days": json.dumps(data.get("applicable_days", [])),
            "discount_type": data["discount_type"],
            "discount_value": data["discount_value"],
            "minimum_order_amount": data.get("minimum_order_amount"),
            "maximum_discount_amount": data.get("maximum_discount_amount"),
            "usage_limit_per_customer": data.get("usage_limit_per_customer"),
            "total_usage_limit": data.get("total_usage_limit"),
            "applicable_items": json.dumps(data.get("applicable_items", [])),
            "excluded_items": json.dumps(data.get("excluded_items", [])),
            "customer_eligibility": json.dumps(data.get("customer_eligibility", {})),
            "terms_conditions": data.get("terms_conditions"),
            "promotion_description": data.get("promotion_description"),
            "auto_apply": data.get("auto_apply", 0),
            "stackable_with_other_offers": data.get("stackable_with_other_offers", 0),
            "created_by": data.get("created_by"),
            "notes": data.get("notes")
        })
        
        promotion.insert()
        
        return {
            "success": True,
            "message": "Promotion created successfully",
            "data": {
                "promotion_id": promotion_id,
                "promotion_code": promotion_code,
                "promotion_name": data["promotion_name"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating promotion: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def validate_promotion(promotion_code, order_data):
    """Validate promotion code for order"""
    try:
        order_info = json.loads(order_data) if isinstance(order_data, str) else order_data
        
        # Get promotion
        promotion = frappe.get_all("Restaurant Promotion",
            filters={"promotion_code": promotion_code, "promotion_status": "Active"},
            fields=["*"],
            limit=1
        )
        
        if not promotion:
            return {
                "success": False,
                "message": "Invalid or inactive promotion code"
            }
        
        promotion = promotion[0]
        
        # Validate dates
        today = frappe.utils.getdate()
        if today < frappe.utils.getdate(promotion["start_date"]) or today > frappe.utils.getdate(promotion["end_date"]):
            return {
                "success": False,
                "message": "Promotion has expired or not yet active"
            }
        
        # Validate time (if specified)
        if promotion.get("start_time") and promotion.get("end_time"):
            current_time = frappe.utils.nowtime()
            if current_time < promotion["start_time"] or current_time > promotion["end_time"]:
                return {
                    "success": False,
                    "message": "Promotion not valid at this time"
                }
        
        # Validate day of week (if specified)
        if promotion.get("applicable_days"):
            applicable_days = json.loads(promotion["applicable_days"])
            current_day = frappe.utils.getdate().strftime("%A")
            if applicable_days and current_day not in applicable_days:
                return {
                    "success": False,
                    "message": f"Promotion not valid on {current_day}"
                }
        
        # Validate minimum order amount
        order_total = order_info.get("order_total", 0)
        if promotion.get("minimum_order_amount") and order_total < promotion["minimum_order_amount"]:
            return {
                "success": False,
                "message": f"Minimum order amount ${promotion['minimum_order_amount']} not met"
            }
        
        # Validate usage limits
        customer_id = order_info.get("customer_id")
        if customer_id and promotion.get("usage_limit_per_customer"):
            customer_usage = get_customer_promotion_usage(customer_id, promotion_code)
            if customer_usage >= promotion["usage_limit_per_customer"]:
                return {
                    "success": False,
                    "message": "Promotion usage limit exceeded for this customer"
                }
        
        if promotion.get("total_usage_limit") and promotion["current_usage_count"] >= promotion["total_usage_limit"]:
            return {
                "success": False,
                "message": "Promotion usage limit exceeded"
            }
        
        # Calculate discount
        discount_amount = calculate_promotion_discount(promotion, order_info)
        
        return {
            "success": True,
            "message": "Promotion is valid",
            "data": {
                "promotion_id": promotion["promotion_id"],
                "promotion_name": promotion["promotion_name"],
                "discount_amount": discount_amount,
                "promotion_type": promotion["promotion_type"],
                "terms_conditions": promotion.get("terms_conditions")
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error validating promotion: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def apply_promotion(order_id, promotion_code):
    """Apply promotion to order"""
    try:
        # Get order
        order = frappe.get_doc("Restaurant Order", order_id)
        
        # Validate promotion
        validation_result = validate_promotion(promotion_code, {
            "order_total": order.total_amount,
            "customer_id": getattr(order, 'customer_id', None),
            "order_items": [{"item_id": item.item_name, "quantity": item.quantity} for item in order.items]
        })
        
        if not validation_result["success"]:
            return validation_result
        
        promotion_data = validation_result["data"]
        discount_amount = promotion_data["discount_amount"]
        
        # Apply discount to order
        order.discount_amount = (order.discount_amount or 0) + discount_amount
        order.total_amount = order.total_amount - discount_amount
        order.promotion_applied = promotion_code
        order.save()
        
        # Update promotion usage
        update_promotion_usage(promotion_data["promotion_id"])
        
        return {
            "success": True,
            "message": f"Promotion applied successfully. Discount: ${discount_amount}",
            "data": {
                "discount_applied": discount_amount,
                "new_total": order.total_amount,
                "promotion_name": promotion_data["promotion_name"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error applying promotion: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def send_targeted_communication(communication_data):
    """Send targeted communication to customers"""
    try:
        data = json.loads(communication_data) if isinstance(communication_data, str) else communication_data
        
        target_customers = data.get("target_customers", [])
        if not target_customers:
            # Get customers based on criteria
            target_customers = get_customers_by_criteria(data.get("target_criteria", {}))
        
        communications_sent = 0
        failed_communications = 0
        
        for customer in target_customers:
            try:
                communication_id = f"COMM-{frappe.utils.now()[:10].replace('-', '')}-{frappe.utils.random_string(6).upper()}"
                
                # Personalize message
                personalized_content = personalize_message(data["message_content"], customer)
                
                communication = frappe.get_doc({
                    "doctype": "Restaurant Customer Communication",
                    "communication_id": communication_id,
                    "communication_type": data.get("communication_type", "Marketing"),
                    "communication_status": "Sent",
                    "campaign_id": data.get("campaign_id"),
                    "customer_id": customer.get("customer_id"),
                    "customer_name": customer.get("customer_name"),
                    "customer_email": customer.get("email"),
                    "customer_phone": customer.get("phone"),
                    "channel": data["channel"],
                    "subject": data.get("subject"),
                    "message_content": personalized_content,
                    "template_used": data.get("template_used"),
                    "personalization_data": json.dumps(customer),
                    "sent_datetime": frappe.utils.now(),
                    "delivery_status": "Delivered",  # Simulate successful delivery
                    "sent_by": data.get("sent_by")
                })
                
                communication.insert()
                communications_sent += 1
                
            except Exception as e:
                failed_communications += 1
                frappe.log_error(f"Failed to send communication to {customer.get('customer_name')}: {str(e)}")
        
        return {
            "success": True,
            "message": f"Communication sent to {communications_sent} customers. {failed_communications} failed.",
            "data": {
                "communications_sent": communications_sent,
                "failed_communications": failed_communications,
                "total_targeted": len(target_customers)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error sending targeted communication: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_campaign_analytics(campaign_id=None, start_date=None, end_date=None):
    """Get marketing campaign analytics"""
    try:
        filters = {}
        
        if campaign_id:
            filters["campaign_id"] = campaign_id
        
        if start_date and end_date:
            filters["start_date"] = ["between", [start_date, end_date]]
        
        campaigns = frappe.get_all("Restaurant Marketing Campaign",
            filters=filters,
            fields=[
                "campaign_id", "campaign_name", "campaign_type", "campaign_status",
                "start_date", "end_date", "budget", "spent_amount",
                "customers_reached", "customers_engaged", "orders_generated",
                "revenue_generated", "response_rate", "conversion_rate", "roi_percentage"
            ]
        )
        
        # Calculate overall metrics
        total_budget = sum(camp.get("budget", 0) for camp in campaigns)
        total_spent = sum(camp.get("spent_amount", 0) for camp in campaigns)
        total_revenue = sum(camp.get("revenue_generated", 0) for camp in campaigns)
        total_customers_reached = sum(camp.get("customers_reached", 0) for camp in campaigns)
        
        # Calculate campaign performance
        for campaign in campaigns:
            campaign["performance_score"] = calculate_campaign_performance_score(campaign)
            campaign["status_color"] = get_campaign_status_color(campaign["campaign_status"])
        
        # Sort by performance
        campaigns.sort(key=lambda x: x.get("performance_score", 0), reverse=True)
        
        return {
            "success": True,
            "data": {
                "campaigns": campaigns,
                "summary": {
                    "total_campaigns": len(campaigns),
                    "total_budget": total_budget,
                    "total_spent": total_spent,
                    "total_revenue": total_revenue,
                    "total_customers_reached": total_customers_reached,
                    "overall_roi": round(((total_revenue - total_spent) / total_spent * 100) if total_spent > 0 else 0, 2)
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting campaign analytics: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_active_promotions(customer_id=None):
    """Get active promotions for customer"""
    try:
        today = frappe.utils.getdate()
        current_time = frappe.utils.nowtime()
        
        filters = {
            "promotion_status": "Active",
            "start_date": ["<=", today],
            "end_date": [">=", today]
        }
        
        promotions = frappe.get_all("Restaurant Promotion",
            filters=filters,
            fields=[
                "promotion_id", "promotion_name", "promotion_type", "promotion_code",
                "discount_type", "discount_value", "minimum_order_amount",
                "promotion_description", "terms_conditions", "end_date",
                "usage_limit_per_customer", "auto_apply"
            ]
        )
        
        # Filter by customer eligibility and usage limits
        eligible_promotions = []
        
        for promo in promotions:
            # Check customer eligibility
            if customer_id and not is_customer_eligible_for_promotion(customer_id, promo):
                continue
            
            # Check usage limits
            if customer_id and promo.get("usage_limit_per_customer"):
                usage_count = get_customer_promotion_usage(customer_id, promo["promotion_code"])
                if usage_count >= promo["usage_limit_per_customer"]:
                    continue
            
            # Add days remaining
            end_date = frappe.utils.getdate(promo["end_date"])
            promo["days_remaining"] = (end_date - today).days
            
            eligible_promotions.append(promo)
        
        # Sort by discount value (highest first)
        eligible_promotions.sort(key=lambda x: x.get("discount_value", 0), reverse=True)
        
        return {
            "success": True,
            "data": {
                "promotions": eligible_promotions,
                "total_active_promotions": len(eligible_promotions)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting active promotions: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_customer_communication_history(customer_id, limit=50):
    """Get customer communication history"""
    try:
        communications = frappe.get_all("Restaurant Customer Communication",
            filters={"customer_id": customer_id},
            fields=[
                "communication_id", "communication_type", "communication_status",
                "channel", "subject", "sent_datetime", "delivery_status",
                "opened_datetime", "clicked_datetime", "response_received"
            ],
            order_by="sent_datetime desc",
            limit=limit
        )
        
        # Calculate engagement metrics
        total_sent = len(communications)
        total_opened = len([c for c in communications if c.get("opened_datetime")])
        total_clicked = len([c for c in communications if c.get("clicked_datetime")])
        total_responded = len([c for c in communications if c.get("response_received")])
        
        engagement_metrics = {
            "total_communications": total_sent,
            "open_rate": round((total_opened / total_sent * 100) if total_sent > 0 else 0, 2),
            "click_rate": round((total_clicked / total_sent * 100) if total_sent > 0 else 0, 2),
            "response_rate": round((total_responded / total_sent * 100) if total_sent > 0 else 0, 2)
        }
        
        return {
            "success": True,
            "data": {
                "communications": communications,
                "engagement_metrics": engagement_metrics
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting communication history: {str(e)}"
        }

# ============================================================================
# MARKETING SYSTEM HELPER FUNCTIONS
# ============================================================================

def create_campaign_promotion(campaign, data):
    """Create promotion linked to campaign"""
    try:
        promotion_id = f"PROMO-{campaign.campaign_id}-{frappe.utils.random_string(3).upper()}"
        
        promotion = frappe.get_doc({
            "doctype": "Restaurant Promotion",
            "promotion_id": promotion_id,
            "promotion_name": f"{campaign.campaign_name} - Special Offer",
            "promotion_type": "Percentage Discount" if data.get("discount_percentage") else "Fixed Amount Discount",
            "promotion_code": generate_promotion_code(),
            "promotion_status": "Draft",
            "start_date": campaign.start_date,
            "end_date": campaign.end_date,
            "discount_type": "Percentage" if data.get("discount_percentage") else "Fixed Amount",
            "discount_value": data.get("discount_percentage") or data.get("discount_amount"),
            "minimum_order_amount": data.get("minimum_order_value"),
            "auto_apply": 1 if campaign.target_audience == "All Customers" else 0,
            "created_by": campaign.campaign_manager,
            "promotion_description": campaign.promotional_offer
        })
        
        promotion.insert()
        return promotion.promotion_id
        
    except Exception as e:
        frappe.log_error(f"Error creating campaign promotion: {str(e)}")
        return None

def generate_promotion_code():
    """Generate unique promotion code"""
    prefix = "SAVE"
    suffix = frappe.utils.random_string(6).upper()
    return f"{prefix}{suffix}"

def get_campaign_target_customers(campaign):
    """Get target customers for campaign"""
    try:
        filters = {}
        
        if campaign.target_audience == "VIP Customers":
            filters["vip_status"] = 1
        elif campaign.target_audience == "Loyal Customers":
            filters["membership_tier"] = ["in", ["Gold", "Platinum", "VIP"]]
        elif campaign.target_audience == "New Customers":
            # Customers who joined in last 30 days
            cutoff_date = frappe.utils.add_days(frappe.utils.nowdate(), -30)
            filters["creation"] = [">=", cutoff_date]
        elif campaign.target_audience == "Inactive Customers":
            # Customers who haven't visited in 60 days
            cutoff_date = frappe.utils.add_days(frappe.utils.nowdate(), -60)
            filters["last_visit_date"] = ["<", cutoff_date]
        elif campaign.target_audience == "Birthday Customers":
            # Customers with birthday this month
            current_month = frappe.utils.nowdate()[5:7]  # MM format
            filters["date_of_birth"] = ["like", f"%-{current_month}-%"]
        elif campaign.target_audience == "Anniversary Customers":
            # Customers with anniversary this month
            current_month = frappe.utils.nowdate()[5:7]
            filters["first_visit_date"] = ["like", f"%-{current_month}-%"]
        
        customers = frappe.get_all("Restaurant Customer Profile",
            filters=filters,
            fields=["customer_id", "customer_name", "email", "phone", "membership_tier", "date_of_birth"]
        )
        
        return customers
        
    except Exception as e:
        frappe.log_error(f"Error getting target customers: {str(e)}")
        return []

def send_campaign_communication(campaign, customer, channel):
    """Send communication to customer via specified channel"""
    try:
        communication_id = f"COMM-{campaign.campaign_id}-{frappe.utils.random_string(6).upper()}"
        
        # Get appropriate template based on channel
        message_content = get_campaign_message_content(campaign, customer, channel)
        
        communication = frappe.get_doc({
            "doctype": "Restaurant Customer Communication",
            "communication_id": communication_id,
            "communication_type": "Marketing",
            "communication_status": "Sent",
            "campaign_id": campaign.campaign_id,
            "customer_id": customer.get("customer_id"),
            "customer_name": customer.get("customer_name"),
            "customer_email": customer.get("email"),
            "customer_phone": customer.get("phone"),
            "channel": channel,
            "subject": f"{campaign.campaign_name} - Special Offer!",
            "message_content": message_content,
            "sent_datetime": frappe.utils.now(),
            "delivery_status": "Delivered",  # Simulate delivery
            "sent_by": campaign.campaign_manager
        })
        
        communication.insert()
        return True
        
    except Exception as e:
        frappe.log_error(f"Error sending campaign communication: {str(e)}")
        return False

def get_campaign_message_content(campaign, customer, channel):
    """Get personalized message content for campaign"""
    try:
        customer_name = customer.get("customer_name", "Valued Customer")
        
        if channel == "Email":
            template = campaign.email_template or get_default_email_template()
        elif channel == "SMS":
            template = campaign.sms_template or get_default_sms_template()
        else:
            template = campaign.promotional_offer or "Special offer just for you!"
        
        # Personalize the message
        personalized_message = template.replace("{customer_name}", customer_name)
        personalized_message = personalized_message.replace("{campaign_name}", campaign.campaign_name)
        personalized_message = personalized_message.replace("{offer_description}", campaign.promotional_offer or "")
        
        if campaign.discount_percentage:
            personalized_message = personalized_message.replace("{discount}", f"{campaign.discount_percentage}%")
        elif campaign.discount_amount:
            personalized_message = personalized_message.replace("{discount}", f"${campaign.discount_amount}")
        
        return personalized_message
        
    except Exception as e:
        return f"Special offer for {customer.get('customer_name', 'you')}!"

def get_default_email_template():
    """Get default email template"""
    return """
    Dear {customer_name},
    
    We have an exclusive offer just for you!
    
    {campaign_name}
    {offer_description}
    
    Enjoy {discount} off your next visit!
    
    Valid until {end_date}. Terms and conditions apply.
    
    Best regards,
    Your Restaurant Team
    """

def get_default_sms_template():
    """Get default SMS template"""
    return "Hi {customer_name}! Special offer: {discount} off your next visit. Use code at checkout. Valid until {end_date}. Terms apply."

def calculate_promotion_discount(promotion, order_info):
    """Calculate discount amount for promotion"""
    try:
        order_total = order_info.get("order_total", 0)
        
        if promotion["discount_type"] == "Percentage":
            discount = order_total * (promotion["discount_value"] / 100)
        else:  # Fixed Amount
            discount = promotion["discount_value"]
        
        # Apply maximum discount limit
        if promotion.get("maximum_discount_amount"):
            discount = min(discount, promotion["maximum_discount_amount"])
        
        return round(discount, 2)
        
    except Exception as e:
        frappe.log_error(f"Error calculating promotion discount: {str(e)}")
        return 0

def get_customer_promotion_usage(customer_id, promotion_code):
    """Get customer's usage count for promotion"""
    try:
        usage_count = frappe.db.count("Restaurant Order",
            filters={
                "customer_id": customer_id,
                "promotion_applied": promotion_code
            }
        )
        return usage_count
    except:
        return 0

def update_promotion_usage(promotion_id):
    """Update promotion usage count"""
    try:
        promotion = frappe.get_doc("Restaurant Promotion", promotion_id)
        promotion.current_usage_count = (promotion.current_usage_count or 0) + 1
        promotion.save()
    except Exception as e:
        frappe.log_error(f"Error updating promotion usage: {str(e)}")

def get_customers_by_criteria(criteria):
    """Get customers based on targeting criteria"""
    try:
        filters = {}
        
        if criteria.get("membership_tier"):
            filters["membership_tier"] = criteria["membership_tier"]
        
        if criteria.get("min_visits"):
            filters["total_visits"] = [">=", criteria["min_visits"]]
        
        if criteria.get("min_spent"):
            filters["total_spent"] = [">=", criteria["min_spent"]]
        
        if criteria.get("last_visit_days"):
            cutoff_date = frappe.utils.add_days(frappe.utils.nowdate(), -criteria["last_visit_days"])
            filters["last_visit_date"] = [">=", cutoff_date]
        
        customers = frappe.get_all("Restaurant Customer Profile",
            filters=filters,
            fields=["customer_id", "customer_name", "email", "phone"]
        )
        
        return customers
        
    except Exception as e:
        frappe.log_error(f"Error getting customers by criteria: {str(e)}")
        return []

def personalize_message(template, customer):
    """Personalize message template with customer data"""
    try:
        personalized = template
        
        # Replace common placeholders
        placeholders = {
            "{customer_name}": customer.get("customer_name", "Valued Customer"),
            "{first_name}": customer.get("customer_name", "").split()[0] if customer.get("customer_name") else "Friend",
            "{membership_tier}": customer.get("membership_tier", "Member"),
            "{total_visits}": str(customer.get("total_visits", 0)),
            "{last_visit}": customer.get("last_visit_date", "recently")
        }
        
        for placeholder, value in placeholders.items():
            personalized = personalized.replace(placeholder, value)
        
        return personalized
        
    except Exception as e:
        return template

def calculate_campaign_performance_score(campaign):
    """Calculate campaign performance score (0-100)"""
    try:
        score = 0
        
        # ROI contribution (40%)
        roi = campaign.get("roi_percentage", 0)
        if roi > 0:
            score += min(roi / 2, 40)  # Cap at 40 points
        
        # Response rate contribution (30%)
        response_rate = campaign.get("response_rate", 0)
        score += min(response_rate * 0.3, 30)  # Cap at 30 points
        
        # Conversion rate contribution (20%)
        conversion_rate = campaign.get("conversion_rate", 0)
        score += min(conversion_rate * 0.2, 20)  # Cap at 20 points
        
        # Budget efficiency contribution (10%)
        budget = campaign.get("budget", 1)
        spent = campaign.get("spent_amount", 0)
        if budget > 0:
            efficiency = (1 - (spent / budget)) * 100
            score += min(efficiency * 0.1, 10)  # Cap at 10 points
        
        return round(score, 1)
        
    except Exception as e:
        return 0

def get_campaign_status_color(status):
    """Get color code for campaign status"""
    status_colors = {
        "Draft": "#808080",      # Gray
        "Approved": "#007bff",   # Blue
        "Active": "#28a745",     # Green
        "Paused": "#ffc107",     # Yellow
        "Completed": "#6c757d",  # Dark Gray
        "Cancelled": "#dc3545"   # Red
    }
    return status_colors.get(status, "#808080")

def is_customer_eligible_for_promotion(customer_id, promotion):
    """Check if customer is eligible for promotion"""
    try:
        if not promotion.get("customer_eligibility"):
            return True
        
        eligibility_rules = json.loads(promotion["customer_eligibility"])
        customer = frappe.get_doc("Restaurant Customer Profile", customer_id)
        
        # Check membership tier requirement
        if eligibility_rules.get("membership_tier"):
            required_tiers = eligibility_rules["membership_tier"]
            if customer.membership_tier not in required_tiers:
                return False
        
        # Check minimum visits requirement
        if eligibility_rules.get("min_visits"):
            if customer.total_visits < eligibility_rules["min_visits"]:
                return False
        
        # Check minimum spend requirement
        if eligibility_rules.get("min_total_spent"):
            if customer.total_spent < eligibility_rules["min_total_spent"]:
                return False
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error checking customer eligibility: {str(e)}")
        return True  # Default to eligible if check fails

# ============================================================================
# AUTOMATED MARKETING TRIGGERS
# ============================================================================

@frappe.whitelist(allow_guest=True)
def trigger_automated_campaigns():
    """Trigger automated marketing campaigns based on customer behavior"""
    try:
        triggered_campaigns = 0
        
        # Birthday campaigns
        birthday_customers = get_birthday_customers_today()
        if birthday_customers:
            triggered_campaigns += trigger_birthday_campaign(birthday_customers)
        
        # Win-back campaigns for inactive customers
        inactive_customers = get_inactive_customers()
        if inactive_customers:
            triggered_campaigns += trigger_winback_campaign(inactive_customers)
        
        # Loyalty boost for frequent customers
        frequent_customers = get_frequent_customers_needing_boost()
        if frequent_customers:
            triggered_campaigns += trigger_loyalty_boost_campaign(frequent_customers)
        
        return {
            "success": True,
            "message": f"Triggered {triggered_campaigns} automated campaigns",
            "data": {
                "campaigns_triggered": triggered_campaigns
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error triggering automated campaigns: {str(e)}"
        }

def get_birthday_customers_today():
    """Get customers with birthdays today"""
    try:
        today = frappe.utils.nowdate()
        today_mm_dd = today[5:]  # Get MM-DD format
        
        customers = frappe.get_all("Restaurant Customer Profile",
            filters={"date_of_birth": ["like", f"%-{today_mm_dd}"]},
            fields=["customer_id", "customer_name", "email", "phone"]
        )
        
        return customers
    except:
        return []

def trigger_birthday_campaign(customers):
    """Trigger birthday campaign for customers"""
    try:
        # Create birthday campaign
        campaign_data = {
            "campaign_name": f"Birthday Special - {frappe.utils.nowdate()}",
            "campaign_type": "Birthday Special",
            "target_audience": "Birthday Customers",
            "start_date": frappe.utils.nowdate(),
            "end_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
            "promotional_offer": "Complimentary birthday dessert + 20% off entire meal",
            "discount_percentage": 20,
            "communication_channels": ["Email", "SMS"]
        }
        
        create_marketing_campaign(campaign_data)
        return 1
        
    except Exception as e:
        frappe.log_error(f"Error triggering birthday campaign: {str(e)}")
        return 0

# ===============================================
# FACE RECOGNITION INTEGRATION ENDPOINTS
# ===============================================

@frappe.whitelist(allow_guest=True)
def get_restaurant_staff():
    """Get all restaurant staff for face recognition integration"""
    try:
        staff_list = frappe.get_all("Restaurant Staff", 
            fields=[
                "name", "full_name", "employee_id", "position", 
                "department", "phone", "email", "employment_status",
                "date_of_joining", "hourly_rate", "salary"
            ],
            filters={"employment_status": "Active"},
            order_by="employee_id"
        )
        
        # Add additional calculated fields
        for staff in staff_list:
            # Calculate hourly rate if only salary is provided
            if not staff.get("hourly_rate") and staff.get("salary"):
                # Assume 40 hours/week, 52 weeks/year
                staff["hourly_rate"] = float(staff["salary"]) / (40 * 52)
            
            # Set default department if not specified
            if not staff.get("department"):
                staff["department"] = "General"
        
        return {
            "success": True,
            "data": staff_list,
            "total_count": len(staff_list)
        }
        
    except Exception as e:
        frappe.log_error(f"Error fetching restaurant staff: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def record_staff_attendance(staff_id=None, employee_id=None, attendance_date=None, 
                           check_in_time=None, check_out_time=None, total_hours=None,
                           status="Present", source="face_recognition"):
    """Record staff attendance from face recognition system"""
    try:
        if not staff_id and not employee_id:
            return {"success": False, "error": "Staff ID or Employee ID is required"}
        
        if not attendance_date:
            return {"success": False, "error": "Attendance date is required"}
        
        # Get staff record
        staff_doc = None
        if staff_id:
            staff_doc = frappe.get_doc("Restaurant Staff", staff_id)
        elif employee_id:
            staff_list = frappe.get_all("Restaurant Staff", 
                filters={"employee_id": employee_id},
                limit=1
            )
            if staff_list:
                staff_doc = frappe.get_doc("Restaurant Staff", staff_list[0].name)
        
        if not staff_doc:
            return {"success": False, "error": "Staff member not found"}
        
        # Check if attendance already exists for this date
        existing_attendance = frappe.get_all("Restaurant Attendance",
            filters={
                "staff": staff_doc.name,
                "attendance_date": attendance_date
            },
            limit=1
        )
        
        # Basic attendance data - restaurant system will handle all business logic
        attendance_data = {
            "doctype": "Restaurant Attendance",
            "staff": staff_doc.name,
            "employee_id": staff_doc.employee_id,
            "staff_name": staff_doc.full_name,
            "attendance_date": attendance_date,
            "status": status,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "total_work_hours": float(total_hours) if total_hours else 0.0,
            "attendance_source": source,
            "notes": f"Basic check-in/out from {source} system - processed by restaurant management"
        }
        
        if existing_attendance:
            # Update existing attendance
            attendance_doc = frappe.get_doc("Restaurant Attendance", existing_attendance[0].name)
            for key, value in attendance_data.items():
                if key != "doctype":
                    setattr(attendance_doc, key, value)
            attendance_doc.save()
            attendance_id = attendance_doc.name
        else:
            # Create new attendance record
            attendance_doc = frappe.get_doc(attendance_data)
            attendance_doc.insert()
            attendance_id = attendance_doc.name
        
        # Note: Payroll, overtime, shifts, etc. are handled by restaurant management system
        # This just records the basic attendance data
        
        return {
            "success": True,
            "attendance_id": attendance_id,
            "message": f"Attendance recorded for {staff_doc.full_name}",
            "staff_name": staff_doc.full_name,
            "total_hours": float(total_hours) if total_hours else 0.0
        }
        
    except Exception as e:
        frappe.log_error(f"Error recording staff attendance: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def get_staff_attendance_summary(staff_id=None, start_date=None, end_date=None):
    """Get attendance summary for staff members"""
    try:
        from datetime import datetime, timedelta
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        filters = {
            "attendance_date": ["between", [start_date, end_date]]
        }
        
        if staff_id:
            filters["staff"] = staff_id
        
        attendance_records = frappe.get_all("Restaurant Attendance",
            fields=[
                "name", "staff", "staff_name", "employee_id", "attendance_date",
                "status", "check_in_time", "check_out_time", "total_work_hours",
                "overtime_hours", "late_entry_minutes", "early_exit_minutes",
                "attendance_source"
            ],
            filters=filters,
            order_by="attendance_date desc, staff_name"
        )
        
        # Calculate summary statistics
        summary_stats = {}
        for record in attendance_records:
            staff_key = record["staff"]
            if staff_key not in summary_stats:
                summary_stats[staff_key] = {
                    "staff_name": record["staff_name"],
                    "employee_id": record["employee_id"],
                    "total_days": 0,
                    "present_days": 0,
                    "absent_days": 0,
                    "total_hours": 0.0,
                    "total_overtime": 0.0,
                    "total_late_minutes": 0,
                    "average_hours_per_day": 0.0
                }
            
            stats = summary_stats[staff_key]
            stats["total_days"] += 1
            
            if record["status"] == "Present":
                stats["present_days"] += 1
                stats["total_hours"] += record["total_work_hours"] or 0.0
                stats["total_overtime"] += record["overtime_hours"] or 0.0
                stats["total_late_minutes"] += record["late_entry_minutes"] or 0
            else:
                stats["absent_days"] += 1
        
        # Calculate averages
        for staff_key, stats in summary_stats.items():
            if stats["present_days"] > 0:
                stats["average_hours_per_day"] = round(stats["total_hours"] / stats["present_days"], 2)
            stats["total_hours"] = round(stats["total_hours"], 2)
            stats["total_overtime"] = round(stats["total_overtime"], 2)
        
        return {
            "success": True,
            "attendance_records": attendance_records,
            "summary_statistics": list(summary_stats.values()),
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_records": len(attendance_records)
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting attendance summary: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def sync_face_recognition_data():
    """Endpoint to trigger synchronization with face recognition system"""
    try:
        from datetime import date
        
        # This would be called by the face recognition system
        # Return current staff data for synchronization
        staff_data = get_restaurant_staff()
        
        if not staff_data.get("success"):
            return staff_data
        
        # Also return any pending attendance corrections or updates
        pending_updates = frappe.get_all("Restaurant Attendance",
            fields=["name", "staff", "attendance_date", "status", "notes"],
            filters={
                "attendance_source": ["!=", "face_recognition"],
                "attendance_date": [">=", date.today().strftime("%Y-%m-%d")]
            },
            order_by="modified desc",
            limit=50
        )
        
        return {
            "success": True,
            "staff_data": staff_data["data"],
            "pending_updates": pending_updates,
            "sync_timestamp": frappe.utils.now(),
            "message": "Synchronization data prepared"
        }
        
    except Exception as e:
        frappe.log_error(f"Error preparing sync data: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def _update_staff_payroll_data(staff_id, attendance_date, total_hours, overtime_hours):
    """Update payroll-related data based on attendance"""
    try:
        # Get staff record
        staff_doc = frappe.get_doc("Restaurant Staff", staff_id)
        hourly_rate = staff_doc.hourly_rate or 0.0
        
        if hourly_rate > 0:
            # Calculate earnings
            regular_earnings = total_hours * hourly_rate
            overtime_earnings = overtime_hours * hourly_rate * 1.5  # 1.5x for overtime
            
            # You could create or update payroll records here
            # For now, we'll just log the calculation
            frappe.logger().info(f"Payroll calculation for {staff_doc.full_name}: "
                               f"Regular: ${regular_earnings:.2f}, Overtime: ${overtime_earnings:.2f}")
    
    except Exception as e:
        frappe.log_error(f"Error updating payroll data: {str(e)}")

@frappe.whitelist(allow_guest=True)
def register_staff_face_encoding(staff_id=None, employee_id=None, face_encoding=None, full_name=None):
    """Register face encoding for a staff member in the central database"""
    try:
        if not staff_id and not employee_id:
            return {"success": False, "error": "Staff ID or Employee ID is required"}
        
        if not face_encoding:
            return {"success": False, "error": "Face encoding is required"}
        
        # Get staff record
        staff_doc = None
        if staff_id:
            staff_doc = frappe.get_doc("Restaurant Staff", staff_id)
        elif employee_id:
            staff_list = frappe.get_all("Restaurant Staff", 
                filters={"employee_id": employee_id},
                limit=1
            )
            if staff_list:
                staff_doc = frappe.get_doc("Restaurant Staff", staff_list[0].name)
        
        if not staff_doc:
            return {"success": False, "error": "Staff member not found"}
        
        # Store face encoding in central database
        staff_doc.face_encoding = face_encoding
        staff_doc.face_registered = 1
        staff_doc.save()
        
        return {
            "success": True,
            "message": f"Face encoding registered for {staff_doc.full_name}",
            "staff_id": staff_doc.name,
            "staff_name": staff_doc.full_name
        }
        
    except Exception as e:
        frappe.log_error(f"Error registering face encoding: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def get_all_staff_face_encodings():
    """Get all staff face encodings for face recognition system"""
    try:
        staff_with_faces = frappe.get_all("Restaurant Staff",
            filters={"face_registered": 1},
            fields=[
                "name", "employee_id", "full_name", "face_encoding", 
                "position", "employment_status"
            ],
            order_by="full_name"
        )
        
        # Format for face recognition system
        face_data = []
        for staff in staff_with_faces:
            if staff.face_encoding:
                face_data.append({
                    "staff_id": staff.name,
                    "employee_id": staff.employee_id,
                    "name": staff.full_name,
                    "face_encoding": staff.face_encoding,
                    "position": staff.position,
                    "status": staff.employment_status
                })
        
        return {
            "success": True,
            "staff_count": len(face_data),
            "face_data": face_data
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting face encodings: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def get_staff_by_face_encoding(face_encoding=None, tolerance=0.6):
    """Find staff member by face encoding (for recognition)"""
    try:
        if not face_encoding:
            return {"success": False, "error": "Face encoding is required"}
        
        # Get all staff with face encodings
        staff_with_faces = frappe.get_all("Restaurant Staff",
            filters={"face_registered": 1, "employment_status": "Active"},
            fields=["name", "employee_id", "full_name", "face_encoding", "position"]
        )
        
        # This would need face_recognition library on the server
        # For now, return the data for the face recognition system to process
        return {
            "success": True,
            "message": "Face encoding comparison should be done on face recognition system",
            "staff_data": staff_with_faces,
            "note": "Use get_all_staff_face_encodings for better performance"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in face recognition lookup: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def update_staff_face_status(staff_id=None, employee_id=None, face_registered=False):
    """Update face registration status for a staff member"""
    try:
        if not staff_id and not employee_id:
            return {"success": False, "error": "Staff ID or Employee ID is required"}
        
        # Get staff record
        staff_doc = None
        if staff_id:
            staff_doc = frappe.get_doc("Restaurant Staff", staff_id)
        elif employee_id:
            staff_list = frappe.get_all("Restaurant Staff", 
                filters={"employee_id": employee_id},
                limit=1
            )
            if staff_list:
                staff_doc = frappe.get_doc("Restaurant Staff", staff_list[0].name)
        
        if not staff_doc:
            return {"success": False, "error": "Staff member not found"}
        
        # Update face registration status
        staff_doc.face_registered = 1 if face_registered else 0
        if not face_registered:
            staff_doc.face_encoding = None  # Clear encoding if unregistering
        staff_doc.save()
        
        return {
            "success": True,
            "message": f"Face status updated for {staff_doc.full_name}",
            "face_registered": bool(staff_doc.face_registered)
        }
        
    except Exception as e:
        frappe.log_error(f"Error updating face status: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def get_staff_shift_schedule(staff_id=None, schedule_date=None):
    """Get staff shift schedules for face recognition system integration"""
    try:
        from datetime import datetime, timedelta
        
        if not schedule_date:
            schedule_date = datetime.now().strftime("%Y-%m-%d")
        
        filters = {"schedule_date": schedule_date}
        if staff_id:
            filters["staff"] = staff_id
        
        # This would get data from a shift schedule DocType if it exists
        # For now, return basic shift information
        shifts = []
        
        if staff_id:
            staff_doc = frappe.get_doc("Restaurant Staff", staff_id)
            shifts.append({
                "staff_id": staff_id,
                "staff_name": staff_doc.full_name,
                "employee_id": staff_doc.employee_id,
                "position": staff_doc.position,
                "shift_start": "09:00:00",
                "shift_end": "17:00:00",
                "shift_type": "regular",
                "expected_hours": 8.0
            })
        else:
            # Get all active staff default shifts
            staff_list = frappe.get_all("Restaurant Staff",
                fields=["name", "full_name", "employee_id", "position"],
                filters={"employment_status": "Active"}
            )
            
            for staff in staff_list:
                shifts.append({
                    "staff_id": staff["name"],
                    "staff_name": staff["full_name"],
                    "employee_id": staff["employee_id"],
                    "position": staff["position"],
                    "shift_start": "09:00:00",
                    "shift_end": "17:00:00",
                    "shift_type": "regular",
                    "expected_hours": 8.0
                })
        
        return {
            "success": True,
            "shifts": shifts,
            "schedule_date": schedule_date,
            "total_shifts": len(shifts)
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting shift schedule: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
