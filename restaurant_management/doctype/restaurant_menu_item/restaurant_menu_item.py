import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate
import json

class RestaurantMenuItem(Document):
    def autoname(self):
        """Generate automatic item code"""
        if not self.item_code:
            # Generate item code: ITEM-YYYY-XXXX
            year = getdate().year
            last_item = frappe.get_last_doc("Restaurant Menu Item", filters={"item_code": ["like", f"ITEM-{year}-%"]})
            
            if last_item:
                last_number = int(last_item.item_code.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.item_code = f"ITEM-{year}-{new_number:04d}"
    
    def validate(self):
        """Validate menu item data"""
        self.calculate_profit_margin()
        self.validate_pricing()
    
    def calculate_profit_margin(self):
        """Calculate profit margin based on price and cost"""
        if self.price and self.cost_price:
            if self.price > 0:
                profit = self.price - self.cost_price
                self.profit_margin = (profit / self.price) * 100
            else:
                self.profit_margin = 0
        else:
            self.profit_margin = 0
    
    def validate_pricing(self):
        """Validate pricing information"""
        if self.price and self.price < 0:
            frappe.throw("Price cannot be negative")
        
        if self.cost_price and self.cost_price < 0:
            frappe.throw("Cost price cannot be negative")
        
        if self.price and self.cost_price and self.cost_price > self.price:
            frappe.throw("Cost price cannot be greater than selling price")
    
    def on_update(self):
        """Actions after menu item is updated"""
        self.update_availability()
    
    def update_availability(self):
        """Update availability status"""
        if not self.is_available:
            # Check if there are any pending orders with this item
            pending_orders = frappe.get_all("Restaurant Order Item", 
                filters={"menu_item": self.name, "parent": ["in", 
                    frappe.get_all("Restaurant Order", 
                        filters={"order_status": ["in", ["Pending", "Confirmed", "Preparing"]]}, 
                        pluck="name")]})
            
            if pending_orders:
                frappe.msgprint(f"Warning: This item is in {len(pending_orders)} pending orders")

@frappe.whitelist()
def get_menu_items(category=None, is_available=True):
    """Get menu items with optional filters"""
    filters = {"is_available": is_available}
    
    if category:
        filters["category"] = category
    
    menu_items = frappe.get_all("Restaurant Menu Item", 
        filters=filters,
        fields=["name", "item_code", "item_name", "item_description", "price", 
                "category", "is_vegetarian", "is_vegan", "spice_level", "preparation_time"])
    
    return {
        "success": True,
        "data": menu_items
    }

@frappe.whitelist()
def get_popular_items():
    """Get popular menu items"""
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

@frappe.whitelist()
def get_chef_specials():
    """Get chef special menu items"""
    chef_specials = frappe.get_all("Restaurant Menu Item", 
        filters={"is_chef_special": 1, "is_available": 1},
        fields=["name", "item_code", "item_name", "item_description", "price", 
                "category", "item_image"],
        order_by="modified desc")
    
    return {
        "success": True,
        "data": chef_specials
    } 