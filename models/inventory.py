"""
Inventory management models
"""
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import config
from database.connection import db

@dataclass
class InventoryItem:
    """Inventory item model"""
    
    item_id: Optional[int] = None
    item_code: str = ""
    item_name: str = ""
    category: str = ""
    quantity: int = 0
    unit_price: float = 0.0
    total_value: float = 0.0
    min_quantity: int = 10
    max_quantity: int = 100
    location: str = ""
    supplier: str = ""
    last_restocked: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize after dataclass creation"""
        if isinstance(self.last_restocked, str):
            self.last_restocked = datetime.strptime(self.last_restocked, '%Y-%m-%d').date()
        # Calculate total value if not provided
        if not self.total_value and self.quantity and self.unit_price:
            self.total_value = self.quantity * self.unit_price
    
    def validate(self) -> tuple[bool, str]:
        """Validate inventory item data"""
        if not self.item_name.strip():
            return False, "Item name is required"
        
        if not self.category.strip():
            return False, "Category is required"
        
        if self.quantity < 0:
            return False, "Quantity cannot be negative"
        
        if self.unit_price < 0:
            return False, "Unit price cannot be negative"
        
        if self.min_quantity < 0:
            return False, "Minimum quantity cannot be negative"
        
        if self.max_quantity <= 0:
            return False, "Maximum quantity must be greater than 0"
        
        if self.min_quantity > self.max_quantity:
            return False, "Minimum quantity cannot exceed maximum quantity"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save inventory item to database"""
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
            # Generate item code if not provided
            if not self.item_code:
                self.item_code = self.generate_item_code()
            
            # Update total value
            self.total_value = self.quantity * self.unit_price
            
            inventory_data = self.to_dict()
            
            if self.item_id:  # Update existing
                # Remove timestamps
                inventory_data.pop('created_at', None)
                inventory_data.pop('updated_at', None)
                
                query = """
                    UPDATE inventory_items SET 
                    item_code = %s, item_name = %s, category = %s,
                    quantity = %s, unit_price = %s, min_quantity = %s,
                    max_quantity = %s, location = %s, supplier = %s,
                    last_restocked = %s
                    WHERE item_id = %s
                """
                params = (
                    inventory_data['item_code'],
                    inventory_data['item_name'],
                    inventory_data['category'],
                    inventory_data['quantity'],
                    inventory_data['unit_price'],
                    inventory_data['min_quantity'],
                    inventory_data['max_quantity'],
                    inventory_data['location'],
                    inventory_data['supplier'],
                    inventory_data['last_restocked'],
                    self.item_id
                )
                
                db.execute_query(query, params)
                return True, "Inventory item updated successfully"
                
            else:  # Insert new
                query = """
                    INSERT INTO inventory_items 
                    (item_code, item_name, category, quantity, unit_price,
                     min_quantity, max_quantity, location, supplier, last_restocked)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    inventory_data['item_code'],
                    inventory_data['item_name'],
                    inventory_data['category'],
                    inventory_data['quantity'],
                    inventory_data['unit_price'],
                    inventory_data['min_quantity'],
                    inventory_data['max_quantity'],
                    inventory_data['location'],
                    inventory_data['supplier'],
                    inventory_data['last_restocked']
                )
                
                item_id = db.execute_query(query, params)
                self.item_id = item_id
                return True, f"Inventory item added successfully with ID: {item_id}"
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def generate_item_code(self) -> str:
        """Generate unique item code"""
        try:
            # Get category prefix
            if self.category:
                prefix = ''.join(word[0].upper() for word in self.category.split()[:2])
                if len(prefix) < 2:
                    prefix = self.category[:2].upper()
            else:
                prefix = "IT"
            
            # Get next sequence number for category
            query = """
                SELECT MAX(CAST(SUBSTRING(item_code, 3) AS UNSIGNED)) as max_num
                FROM inventory_items 
                WHERE item_code LIKE %s
            """
            pattern = f"{prefix}%"
            result = db.execute_query(query, (pattern,), fetch=True)
            
            if result and result[0]['max_num']:
                next_num = result[0]['max_num'] + 1
            else:
                next_num = 1
            
            return f"{prefix}{next_num:03d}"
        except:
            # Fallback
            timestamp = datetime.now().strftime('%y%m%d%H%M')
            return f"IT{timestamp}"
    
    def update_quantity(self, quantity_change: int, is_restock: bool = False) -> tuple[bool, str]:
        """Update item quantity (positive for restock, negative for usage)"""
        new_quantity = self.quantity + quantity_change
        
        if new_quantity < 0:
            return False, "Insufficient stock"
        
        self.quantity = new_quantity
        
        if is_restock:
            self.last_restocked = date.today()
        
        return self.save()
    
    def check_low_stock(self) -> bool:
        """Check if item is below minimum quantity"""
        return self.quantity < self.min_quantity
    
    def check_overstock(self) -> bool:
        """Check if item is above maximum quantity"""
        return self.quantity > self.max_quantity
    
    def get_reorder_quantity(self) -> int:
        """Calculate recommended reorder quantity"""
        if self.check_low_stock():
            return self.max_quantity - self.quantity
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert inventory item to dictionary"""
        data = asdict(self)
        
        # Convert dates to strings
        if data['last_restocked'] and isinstance(data['last_restocked'], date):
            data['last_restocked'] = data['last_restocked'].isoformat()
        
        # Convert datetimes to strings
        for field in ['created_at', 'updated_at']:
            if data[field] and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'InventoryItem':
        """Create InventoryItem instance from dictionary"""
        return cls(**data)
    
    @classmethod
    def get_all(cls) -> List['InventoryItem']:
        """Get all inventory items"""
        try:
            query = Queries.GET_ALL_INVENTORY
            results = db.execute_query(query, fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_id(cls, item_id: int) -> Optional['InventoryItem']:
        """Get inventory item by ID"""
        try:
            query = "SELECT * FROM inventory_items WHERE item_id = %s"
            result = db.execute_query(query, (item_id,), fetch=True)
            if result:
                return cls.from_dict(result[0])
            return None
        except:
            return None
    
    @classmethod
    def get_low_stock_items(cls) -> List['InventoryItem']:
        """Get items below minimum quantity"""
        try:
            query = Queries.GET_LOW_STOCK_ITEMS
            results = db.execute_query(query, fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_category(cls, category: str) -> List['InventoryItem']:
        """Get inventory items by category"""
        try:
            query = "SELECT * FROM inventory_items WHERE category = %s ORDER BY item_name"
            results = db.execute_query(query, (category,), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_inventory_value_summary(cls) -> Dict:
        """Get inventory value summary by category"""
        try:
            query = Queries.GET_INVENTORY_VALUE
            results = db.execute_query(query, fetch=True)
            
            total_value = sum(r['total_value'] for r in results)
            total_items = sum(r['item_count'] for r in results)
            total_quantity = sum(r['total_quantity'] for r in results)
            
            return {
                'total_value': total_value,
                'total_items': total_items,
                'total_quantity': total_quantity,
                'category_breakdown': results
            }
        except:
            return {
                'total_value': 0,
                'total_items': 0,
                'total_quantity': 0,
                'category_breakdown': []
            }


class InventoryManager:
    """Manager for inventory operations"""
    
    @staticmethod
    def restock_item(item_id: int, quantity: int, unit_price: float = None) -> tuple[bool, str]:
        """Restock inventory item"""
        try:
            item = InventoryItem.get_by_id(item_id)
            if not item:
                return False, "Item not found"
            
            if unit_price:
                item.unit_price = unit_price
            
            return item.update_quantity(quantity, is_restock=True)
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def use_item(item_id: int, quantity: int, description: str = "") -> tuple[bool, str]:
        """Use/consume inventory item"""
        try:
            item = InventoryItem.get_by_id(item_id)
            if not item:
                return False, "Item not found"
            
            # Check stock availability
            if item.quantity < quantity:
                return False, f"Insufficient stock. Available: {item.quantity}"
            
            # Record expense for the usage
            expense = Expense(
                description=f"Inventory usage: {item.item_name} - {description}",
                amount=0,  # Could calculate cost here
                category="Inventory Usage",
                item_id=item_id
            )
            expense.save()
            
            return item.update_quantity(-quantity)
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def get_inventory_report() -> Dict:
        """Generate inventory report"""
        try:
            # Get all items
            all_items = InventoryItem.get_all()
            
            # Get low stock items
            low_stock = InventoryItem.get_low_stock_items()
            
            # Get value summary
            value_summary = InventoryItem.get_inventory_value_summary()
            
            # Calculate reorder values
            total_reorder_value = 0
            for item in low_stock:
                reorder_qty = item.get_reorder_quantity()
                reorder_cost = reorder_qty * item.unit_price
                total_reorder_value += reorder_cost
            
            return {
                'total_items': len(all_items),
                'low_stock_items': len(low_stock),
                'total_inventory_value': value_summary['total_value'],
                'total_reorder_value': total_reorder_value,
                'category_summary': value_summary['category_breakdown'],
                'low_stock_details': [
                    {
                        'item_code': item.item_code,
                        'item_name': item.item_name,
                        'current_quantity': item.quantity,
                        'min_quantity': item.min_quantity,
                        'reorder_quantity': item.get_reorder_quantity(),
                        'reorder_cost': item.get_reorder_quantity() * item.unit_price
                    }
                    for item in low_stock
                ]
            }
        except Exception as e:
            print(f"Error generating inventory report: {e}")
            return {}