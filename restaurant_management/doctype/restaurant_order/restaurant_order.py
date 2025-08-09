import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, now_datetime, add_to_date
import json

class RestaurantOrder(Document):
    def autoname(self):
        """Generate automatic order ID"""
        if not self.order_id:
            # Generate order ID: ORD-YYYY-XXXX
            year = getdate().year
            last_order = frappe.get_last_doc("Restaurant Order", filters={"order_id": ["like", f"ORD-{year}-%"]})
            
            if last_order:
                last_number = int(last_order.order_id.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.order_id = f"ORD-{year}-{new_number:04d}"
    
    def validate(self):
        """Validate order data"""
        self.validate_order_items()
        self.calculate_totals()
        self.validate_payment()
        self.set_delivery_info()
    
    def validate_order_items(self):
        """Validate order items"""
        if not self.items:
            frappe.throw("Order must have at least one item")
        
        for item in self.items:
            if not item.menu_item:
                frappe.throw("All order items must have a menu item selected")
            
            if not item.quantity or item.quantity <= 0:
                frappe.throw("All items must have a quantity greater than 0")
    
    def calculate_totals(self):
        """Calculate order totals"""
        subtotal = 0
        tax_amount = 0
        
        for item in self.items:
            # Calculate item subtotal
            item.subtotal = item.quantity * item.unit_price
            
            # Calculate item tax
            item.tax_amount = item.subtotal * (item.tax_rate / 100)
            
            # Calculate item total
            item.total_amount = item.subtotal + item.tax_amount - item.discount_amount
            
            # Add to order totals
            subtotal += item.subtotal
            tax_amount += item.tax_amount
        
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        
        # Calculate discount
        if self.discount_type == "Percentage":
            self.discount_amount = subtotal * (self.discount_percentage / 100)
        
        # Calculate total amount
        self.total_amount = subtotal + self.tax_amount - self.discount_amount + self.delivery_fee
        
        # Calculate change amount
        if self.amount_paid:
            self.change_amount = self.amount_paid - self.total_amount
    
    def validate_payment(self):
        """Validate payment information"""
        if self.payment_status == "Paid" and self.amount_paid < self.total_amount:
            frappe.throw("Amount paid must be equal to or greater than total amount")
        
        if self.amount_paid and self.amount_paid < 0:
            frappe.throw("Amount paid cannot be negative")
    
    def set_delivery_info(self):
        """Set delivery information for delivery orders"""
        if self.order_type == "Delivery":
            if not self.delivery_fee:
                self.delivery_fee = 5.00  # Default delivery fee
            
            if not self.estimated_delivery_time:
                # Set estimated delivery time to 45 minutes from now
                self.estimated_delivery_time = add_to_date(now_datetime(), minutes=45)
    
    def on_update(self):
        """Actions after order is updated"""
        self.update_payment_status()
        self.send_notifications()
    
    def update_payment_status(self):
        """Update payment status based on amount paid"""
        if self.amount_paid >= self.total_amount:
            self.payment_status = "Paid"
        elif self.amount_paid > 0:
            self.payment_status = "Partially Paid"
        else:
            self.payment_status = "Pending"
    
    def send_notifications(self):
        """Send notifications based on order status"""
        if self.order_status == "Confirmed":
            # Send notification to kitchen
            self.send_kitchen_notification()
        
        elif self.order_status == "Ready":
            # Send notification to waiter/customer
            self.send_ready_notification()
    
    def send_kitchen_notification(self):
        """Send notification to kitchen staff"""
        # This would integrate with Frappe's notification system
        pass
    
    def send_ready_notification(self):
        """Send notification when order is ready"""
        # This would integrate with Frappe's notification system
        pass
    
    def get_order_summary(self):
        """Get order summary for reports"""
        return {
            "order_id": self.order_id,
            "order_type": self.order_type,
            "customer_name": self.customer_name,
            "order_date": self.order_date,
            "order_time": self.order_time,
            "total_amount": self.total_amount,
            "payment_status": self.payment_status,
            "order_status": self.order_status,
            "item_count": len(self.items)
        }

@frappe.whitelist()
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

@frappe.whitelist()
def get_orders(filters=None):
    """Get orders with optional filters"""
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

@frappe.whitelist()
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

@frappe.whitelist()
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