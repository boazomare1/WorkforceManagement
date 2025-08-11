import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate
import json

class RestaurantStaff(Document):
    
    def validate(self):
        """Validate staff data"""
        self.validate_email()
        self.validate_phone()
        self.calculate_overtime_rate()
        self.validate_hire_date()
    
    def validate_email(self):
        """Validate email format and uniqueness"""
        if self.email:
            # Check if email already exists for another staff
            existing_staff = frappe.get_all("Restaurant Staff", 
                filters={"email": self.email, "name": ["!=", self.name]})
            if existing_staff:
                frappe.throw("Email address already exists for another staff member")
    
    def validate_phone(self):
        """Validate phone number format"""
        if self.phone and len(self.phone) < 10:
            frappe.throw("Phone number must be at least 10 digits")
    
    def calculate_overtime_rate(self):
        """Calculate overtime rate (1.5x base rate)"""
        if self.base_hourly_rate:
            self.overtime_rate = self.base_hourly_rate * 1.5
    
    def validate_hire_date(self):
        """Validate hire date is not in the future"""
        if self.hire_date and getdate(self.hire_date) > getdate():
            frappe.throw("Hire date cannot be in the future")
    
    def on_update(self):
        """Actions after staff is updated"""
        self.update_face_recognition_status()
        self.create_user_account()
    
    def update_face_recognition_status(self):
        """Update face recognition status based on face encoding"""
        if self.face_encoding:
            self.face_registered = 1
        else:
            self.face_registered = 0
    
    def create_user_account(self):
        """Create user account for staff member"""
        if not frappe.db.exists("User", self.email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": self.email,
                "first_name": self.full_name.split()[0] if self.full_name else "",
                "last_name": " ".join(self.full_name.split()[1:]) if self.full_name and len(self.full_name.split()) > 1 else "",
                "send_welcome_email": 0,
                "user_type": "Website User"
            })
            user.insert(ignore_permissions=True)
            
            # Assign role based on position
            role = self.get_role_for_position()
            if role:
                user.add_roles(role)
    
    def get_role_for_position(self):
        """Get Frappe role based on staff position"""
        role_mapping = {
            "Manager": "Restaurant Manager",
            "Waiter": "Restaurant Staff",
            "Chef": "Restaurant Staff",
            "Kitchen Staff": "Restaurant Staff",
            "Cashier": "Restaurant Staff",
            "Host/Hostess": "Restaurant Staff",
            "Bartender": "Restaurant Staff",
            "Dishwasher": "Restaurant Staff"
        }
        return role_mapping.get(self.position, "Restaurant Staff")
    
    def get_attendance_records(self, start_date=None, end_date=None):
        """Get attendance records for this staff member"""
        filters = {"name": self.name}
        
        if start_date:
            filters["date"] = [">=", start_date]
        if end_date:
            filters["date"] = ["<=", end_date]
        
        return frappe.get_all("Restaurant Attendance", 
            filters=filters, 
            fields=["*"], 
            order_by="date desc, check_in_time desc")
    
    def calculate_hours_worked(self, start_date=None, end_date=None):
        """Calculate total hours worked in a period"""
        attendance_records = self.get_attendance_records(start_date, end_date)
        total_hours = 0
        
        for record in attendance_records:
            if record.check_in_time and record.check_out_time:
                # Calculate hours between check-in and check-out
                check_in = frappe.utils.get_datetime(record.check_in_time)
                check_out = frappe.utils.get_datetime(record.check_out_time)
                hours = (check_out - check_in).total_seconds() / 3600
                total_hours += hours
        
        return round(total_hours, 2)
    
    def calculate_payroll(self, start_date, end_date):
        """Calculate payroll for a specific period"""
        total_hours = self.calculate_hours_worked(start_date, end_date)
        
        # Basic calculation - can be enhanced with overtime, weekend rates, etc.
        base_pay = total_hours * self.base_hourly_rate
        
        return {
            "staff_id": self.name,
            "staff_name": self.full_name,
            "period": f"{start_date} to {end_date}",
            "total_hours": total_hours,
            "base_rate": self.base_hourly_rate,
            "base_pay": base_pay,
            "overtime_hours": 0,  # To be implemented
            "overtime_pay": 0,    # To be implemented
            "total_pay": base_pay
        }

@frappe.whitelist()
def get_staff_by_face_encoding(face_encoding):
    """Get staff member by face encoding"""
    staff = frappe.get_all("Restaurant Staff", 
        filters={"face_encoding": face_encoding, "employment_status": "Active"},
        fields=["name", "full_name", "position"])
    
    if staff:
        return staff[0]
    return None

@frappe.whitelist()
def register_face_for_staff(staff_id, face_encoding):
    """Register face encoding for a staff member"""
    try:
        staff = frappe.get_doc("Restaurant Staff", staff_id)
        staff.face_encoding = face_encoding
        staff.face_registered = 1
        staff.save()
        
        return {
            "success": True,
            "message": f"Face registered successfully for {staff.full_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error registering face: {str(e)}"
        }

@frappe.whitelist()
def get_staff_list(filters=None):
    """Get list of staff members with optional filters"""
    if filters:
        filters = json.loads(filters)
    else:
        filters = {}
    
    # Add default filter for active staff
    if "employment_status" not in filters:
        filters["employment_status"] = "Active"
    
    staff_list = frappe.get_all("Restaurant Staff", 
        filters=filters,
        fields=["name", "full_name", "email", "phone", "position", 
                "department", "base_hourly_rate", "employment_status", "face_registered"])
    
    return staff_list 