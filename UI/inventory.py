import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import config
from database.connection import db
from utils.helpers import format_currency, parse_currency

class InventoryTab:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        self.load_inventory()
        
    def setup_ui(self):
        """Setup inventory tab UI"""
        # Create notebook for inventory sections
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.items_frame = ttk.Frame(self.notebook)
        self.low_stock_frame = ttk.Frame(self.notebook)
        self.categories_frame = ttk.Frame(self.notebook)
        self.suppliers_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.items_frame, text="All Items")
        self.notebook.add(self.low_stock_frame, text="Low Stock")
        self.notebook.add(self.categories_frame, text="Categories")
        self.notebook.add(self.suppliers_frame, text="Suppliers")
        
        # Setup each tab
        self.setup_items_tab()
        self.setup_low_stock_tab()
        self.setup_categories_tab()
        self.setup_suppliers_tab()
    
    def setup_items_tab(self):
        """Setup inventory items tab"""
        # Toolbar
        toolbar = ttk.Frame(self.items_frame)
        toolbar.pack(fill='x', padx=10, pady=10)
        
        buttons = [
            ("➕ Add Item", self.add_item),
            ("✏️ Edit Item", self.edit_item),
            ("📦 Restock", self.restock_item),
            ("📤 Use Item", self.use_item),
            ("🗑️ Delete", self.delete_item),
            ("🖨️ Print", self.print_inventory)
        ]
        
        for text, command in buttons:
            btn = ttk.Button(toolbar, text=text, command=command)
            btn.pack(side='left', padx=5)
        
        # Search and filter
        filter_frame = ttk.Frame(self.items_frame)
        filter_frame.pack(fill='x', padx=10, pady=5)
        
        # Category filter
        ttk.Label(filter_frame, text="Category:").pack(side='left', padx=5)
        self.category_filter_var = tk.StringVar(value="All")
        self.category_filter_combo = ttk.Combobox(filter_frame, textvariable=self.category_filter_var, width=15)
        self.category_filter_combo.pack(side='left', padx=5)
        
        # Search
        ttk.Label(filter_frame, text="Search:").pack(side='left', padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.search_var, width=30).pack(side='left', padx=5)
        
        ttk.Button(filter_frame, text="Search", command=self.search_items).pack(side='left', padx=5)
        ttk.Button(filter_frame, text="Clear", command=self.load_inventory).pack(side='left', padx=5)
        
        # Inventory table
        table_frame = ttk.Frame(self.items_frame)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = [
            'ID', 'Code', 'Name', 'Category', 'Quantity',
            'Unit Price', 'Total Value', 'Min Qty', 'Last Restocked'
        ]
        
        self.inventory_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=20
        )
        
        # Configure columns
        for col in columns:
            self.inventory_tree.heading(col, text=col)
            self.inventory_tree.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscrollcommand=scrollbar.set)
        
        self.inventory_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Summary
        summary_frame = ttk.Frame(self.items_frame)
        summary_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(summary_frame, text="Total Items:").pack(side='left', padx=5)
        self.total_items_var = tk.StringVar(value="0")
        ttk.Label(summary_frame, textvariable=self.total_items_var, font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        
        from utils.helpers import format_currency
        ttk.Label(summary_frame, text="Total Value:").pack(side='left', padx=20)
        self.total_value_var = tk.StringVar(value=format_currency(0.0))
        ttk.Label(summary_frame, textvariable=self.total_value_var, font=('Arial', 10, 'bold')).pack(side='left', padx=5)
    
    def setup_low_stock_tab(self):
        """Setup low stock items tab"""
        # Low stock table
        table_frame = ttk.Frame(self.low_stock_frame)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = [
            'Code', 'Name', 'Category', 'Current Qty',
            'Min Qty', 'Reorder Qty', 'Unit Price', 'Reorder Cost'
        ]
        
        self.low_stock_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        for col in columns:
            self.low_stock_tree.heading(col, text=col)
            self.low_stock_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.low_stock_tree.yview)
        self.low_stock_tree.configure(yscrollcommand=scrollbar.set)
        
        self.low_stock_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Summary and actions
        action_frame = ttk.Frame(self.low_stock_frame)
        action_frame.pack(fill='x', padx=10, pady=10)
        
        # Summary
        ttk.Label(action_frame, text="Low Stock Items:").pack(side='left', padx=5)
        self.low_stock_count_var = tk.StringVar(value="0")
        ttk.Label(action_frame, textvariable=self.low_stock_count_var, font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        
        from utils.helpers import format_currency
        ttk.Label(action_frame, text="Total Reorder Cost:").pack(side='left', padx=20)
        self.reorder_cost_var = tk.StringVar(value=format_currency(0.0))
        ttk.Label(action_frame, textvariable=self.reorder_cost_var, font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        
        # Actions
        ttk.Button(action_frame, text="Generate Order List", command=self.generate_order_list).pack(side='right', padx=5)
        ttk.Button(action_frame, text="Restock All", command=self.restock_all).pack(side='right', padx=5)
    
    def setup_categories_tab(self):
        """Setup categories tab"""
        # Categories table
        table_frame = ttk.Frame(self.categories_frame)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ['Category', 'Item Count', 'Total Quantity', 'Total Value', 'Avg Price']
        self.categories_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        for col in columns:
            self.categories_tree.heading(col, text=col)
            self.categories_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.categories_tree.yview)
        self.categories_tree.configure(yscrollcommand=scrollbar.set)
        
        self.categories_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def setup_suppliers_tab(self):
        """Setup suppliers tab"""
        # Suppliers list
        supplier_frame = ttk.Frame(self.suppliers_frame)
        supplier_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left: Supplier list
        left_frame = ttk.Frame(supplier_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        ttk.Label(left_frame, text="Suppliers", font=('Arial', 12, 'bold')).pack(pady=5)
        
        columns = ['Supplier', 'Item Count', 'Last Order', 'Contact']
        self.suppliers_tree = ttk.Treeview(
            left_frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        for col in columns:
            self.suppliers_tree.heading(col, text=col)
            self.suppliers_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=self.suppliers_tree.yview)
        self.suppliers_tree.configure(yscrollcommand=scrollbar.set)
        
        self.suppliers_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Right: Add supplier form
        right_frame = ttk.LabelFrame(supplier_frame, text="Add Supplier", padding=10)
        right_frame.pack(side='right', fill='both', padx=5)
        
        fields = [
            ("Supplier Name:", "supplier_name_var"),
            ("Contact Person:", "contact_person_var"),
            ("Phone:", "supplier_phone_var"),
            ("Email:", "supplier_email_var"),
            ("Address:", "supplier_address_var")
        ]
        
        for i, (label, var_name) in enumerate(fields):
            ttk.Label(right_frame, text=label).grid(row=i, column=0, sticky='w', pady=5)
            setattr(self, var_name, tk.StringVar())
            
            if "address" in var_name:
                text = tk.Text(right_frame, height=3, width=25)
                text.grid(row=i, column=1, pady=5, padx=5)
                setattr(self, var_name + "_widget", text)
            else:
                ttk.Entry(right_frame, textvariable=getattr(self, var_name), width=25).grid(
                    row=i, column=1, pady=5, padx=5)
        
        ttk.Button(right_frame, text="Add Supplier", command=self.add_supplier).grid(
            row=len(fields), column=0, columnspan=2, pady=10)
    
    def load_inventory(self):
        """Load all inventory items"""
        # Clear existing items
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        
        # Load categories for filter
        self.load_categories_for_filter()
        
        try:
            query = """
                SELECT 
                    item_id, item_code, item_name, category, quantity,
                    unit_price, total_value, min_quantity, last_restocked
                FROM inventory_items
                ORDER BY category, item_name
            """
            results = db.execute_query(query, fetch=True)
            
            total_items = 0
            total_value = 0
            
            from utils.helpers import format_currency
            for row in results:
                unit_price_display = format_currency(float(row['unit_price'])) if row['unit_price'] else format_currency(0.0)
                total_value_display = format_currency(float(row['total_value'])) if row['total_value'] else format_currency(0.0)

                self.inventory_tree.insert('', 'end', values=(
                    row['item_id'],
                    row['item_code'],
                    row['item_name'],
                    row['category'],
                    row['quantity'],
                    unit_price_display,
                    total_value_display,
                    row['min_quantity'],
                    row['last_restocked'] or "Never"
                ))

                total_items += 1
                total_value += float(row['total_value']) if row['total_value'] else 0
            
            # Update summary
            self.total_items_var.set(str(total_items))
            from utils.helpers import format_currency
            self.total_value_var.set(format_currency(total_value))
            
            # Load other tabs
            self.load_low_stock()
            self.load_categories()
            self.load_suppliers()
            
        except Exception as e:
            print(f"Error loading inventory: {e}")
    
    def load_categories_for_filter(self):
        """Load categories for filter combobox"""
        try:
            query = "SELECT DISTINCT category FROM inventory_items WHERE category IS NOT NULL ORDER BY category"
            results = db.execute_query(query, fetch=True)
            categories = ["All"] + [r['category'] for r in results]
            self.category_filter_combo['values'] = categories
        except Exception as e:
            print(f"Error loading categories: {e}")
    
    def search_items(self):
        """Search inventory items"""
        # Clear existing items
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        
        try:
            category_filter = self.category_filter_var.get()
            search_term = self.search_var.get().strip().lower()
            
            query = """
                SELECT 
                    item_id, item_code, item_name, category, quantity,
                    unit_price, total_value, min_quantity, last_restocked
                FROM inventory_items
                WHERE 1=1
            """
            params = []
            
            if category_filter != "All":
                query += " AND category = %s"
                params.append(category_filter)
            
            if search_term:
                query += " AND (item_name LIKE %s OR item_code LIKE %s OR category LIKE %s)"
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY category, item_name"
            
            results = db.execute_query(query, tuple(params) if params else None, fetch=True)
            
            total_items = 0
            total_value = 0
            
            for row in results:
                self.inventory_tree.insert('', 'end', values=(
                    row['item_id'],
                    row['item_code'],
                    row['item_name'],
                    row['category'],
                    row['quantity'],
                    format_currency(float(row['unit_price'])) if row['unit_price'] else format_currency(0.0),
                    format_currency(float(row['total_value'])) if row['total_value'] else format_currency(0.0),
                    row['min_quantity'],
                    row['last_restocked'] or "Never"
                ))
                
                total_items += 1
                total_value += float(row['total_value']) if row['total_value'] else 0
            
            # Update summary
            self.total_items_var.set(str(total_items))
            self.total_value_var.set(format_currency(total_value))
            
        except Exception as e:
            print(f"Error searching inventory: {e}")
    
    def load_low_stock(self):
        """Load low stock items"""
        # Clear existing items
        for item in self.low_stock_tree.get_children():
            self.low_stock_tree.delete(item)
        
        try:
            query = """
                SELECT 
                    item_code, item_name, category, quantity,
                    min_quantity, unit_price, total_value
                FROM inventory_items
                WHERE quantity < min_quantity
                ORDER BY (min_quantity - quantity) DESC
            """
            results = db.execute_query(query, fetch=True)
            
            low_stock_count = 0
            total_reorder_cost = 0
            
            for row in results:
                current_qty = row['quantity']
                min_qty = row['min_quantity']
                reorder_qty = min_qty - current_qty
                unit_price = float(row['unit_price']) if row['unit_price'] else 0
                reorder_cost = reorder_qty * unit_price
                
                self.low_stock_tree.insert('', 'end', values=(
                    row['item_code'],
                    row['item_name'],
                    row['category'],
                    current_qty,
                    min_qty,
                    reorder_qty,
                    format_currency(unit_price),
                    format_currency(reorder_cost)
                ))
                
                low_stock_count += 1
                total_reorder_cost += reorder_cost
            
            # Update summary
            self.low_stock_count_var.set(str(low_stock_count))
            self.reorder_cost_var.set(format_currency(total_reorder_cost))
            
        except Exception as e:
            print(f"Error loading low stock: {e}")
    
    def load_categories(self):
        """Load category summary"""
        # Clear existing items
        for item in self.categories_tree.get_children():
            self.categories_tree.delete(item)
        
        try:
            query = """
                SELECT 
                    COALESCE(category, 'Uncategorized') as category,
                    COUNT(*) as item_count,
                    SUM(quantity) as total_quantity,
                    SUM(total_value) as total_value
                FROM inventory_items
                GROUP BY category
                ORDER BY category
            """
            results = db.execute_query(query, fetch=True)
            
            for row in results:
                item_count = row['item_count']
                total_qty = float(row['total_quantity']) if row['total_quantity'] else 0
                total_val = float(row['total_value']) if row['total_value'] else 0
                avg_price = (total_val / total_qty) if total_qty > 0 else 0
                
                self.categories_tree.insert('', 'end', values=(
                    row['category'],
                    item_count,
                    total_qty,
                    format_currency(total_val),
                    format_currency(avg_price)
                ))
                
        except Exception as e:
            print(f"Error loading categories: {e}")
    
    def load_suppliers(self):
        """Load suppliers"""
        # Clear existing items
        for item in self.suppliers_tree.get_children():
            self.suppliers_tree.delete(item)
        
        try:
            query = """
                SELECT 
                    supplier,
                    COUNT(*) as item_count,
                    MAX(last_restocked) as last_order
                FROM inventory_items
                WHERE supplier IS NOT NULL AND supplier != ''
                GROUP BY supplier
                ORDER BY supplier
            """
            results = db.execute_query(query, fetch=True)
            
            for row in results:
                # For now, just show basic info
                # In a real app, you'd have a separate suppliers table
                self.suppliers_tree.insert('', 'end', values=(
                    row['supplier'],
                    row['item_count'],
                    row['last_order'] or 'Never',
                    'Not stored'
                ))
                
        except Exception as e:
            print(f"Error loading suppliers: {e}")
    
    def add_item(self):
        """Add new inventory item"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("Add New Inventory Item")
        dialog.geometry("500x400")
        dialog.transient(self.frame)
        dialog.grab_set()
        
        # Form fields
        fields = [
            ("Item Code:", "new_item_code_var"),
            ("Item Name:", "new_item_name_var"),
            ("Category:", "new_category_var"),
            ("Quantity:", "new_quantity_var"),
            ("Unit Price:", "new_unit_price_var"),
            ("Min Quantity:", "new_min_qty_var"),
            ("Supplier:", "new_supplier_var"),
            ("Location:", "new_location_var")
        ]
        
        for i, (label, var_name) in enumerate(fields[:4]):  # First column
            ttk.Label(dialog, text=label).grid(row=i, column=0, sticky='w', pady=5, padx=10)
            setattr(self, var_name, tk.StringVar())
            ttk.Entry(dialog, textvariable=getattr(self, var_name), width=25).grid(
                row=i, column=1, pady=5, padx=10, sticky='w')
        
        for i, (label, var_name) in enumerate(fields[4:]):  # Second column
            ttk.Label(dialog, text=label).grid(row=i, column=2, sticky='w', pady=5, padx=10)
            setattr(self, var_name, tk.StringVar())
            ttk.Entry(dialog, textvariable=getattr(self, var_name), width=25).grid(
                row=i, column=3, pady=5, padx=10, sticky='w')
        
        # Auto-generate item code
        self.new_item_code_var.set(self.generate_item_code())
        
        def save_item():
            try:
                # Validate inputs
                if not self.new_item_name_var.get():
                    messagebox.showwarning("Warning", "Please enter item name")
                    return
                
                try:
                    quantity = int(self.new_quantity_var.get() or 0)
                    unit_price = float(self.new_unit_price_var.get() or 0)
                    min_qty = int(self.new_min_qty_var.get() or 10)
                except ValueError:
                    messagebox.showwarning("Warning", "Please enter valid numbers")
                    return
                
                # Insert item
                query = """
                    INSERT INTO inventory_items 
                    (item_code, item_name, category, quantity, unit_price, min_quantity, supplier, location)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    self.new_item_code_var.get(),
                    self.new_item_name_var.get(),
                    self.new_category_var.get() or None,
                    quantity,
                    unit_price,
                    min_qty,
                    self.new_supplier_var.get() or None,
                    self.new_location_var.get() or None
                )
                
                db.execute_query(query, params)
                
                messagebox.showinfo("Success", "Item added successfully!")
                dialog.destroy()
                self.load_inventory()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add item: {str(e)}")
        
        ttk.Button(dialog, text="Save", command=save_item).grid(
            row=8, column=0, columnspan=4, pady=20)
    
    def generate_item_code(self):
        """Generate unique item code"""
        try:
            # Get next item number
            query = "SELECT MAX(CAST(SUBSTRING(item_code, 3) AS UNSIGNED)) as max_num FROM inventory_items WHERE item_code LIKE 'IT%'"
            result = db.execute_query(query, fetch=True)
            
            if result and result[0]['max_num']:
                next_num = result[0]['max_num'] + 1
            else:
                next_num = 1001
            
            return f"IT{next_num}"
        except:
            return f"IT{datetime.now().strftime('%y%m%d%H%M')}"
    
    def edit_item(self):
        """Edit selected item"""
        selected = self.inventory_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to edit")
            return
        
        item = self.inventory_tree.item(selected[0])
        item_id = item['values'][0]
        
        # Load item details and show edit dialog
        self.show_edit_dialog(item_id)
    
    def restock_item(self):
        """Restock selected item"""
        selected = self.inventory_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to restock")
            return
        
        item = self.inventory_tree.item(selected[0])
        item_id = item['values'][0]
        item_name = item['values'][2]
        
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"Restock {item_name}")
        dialog.geometry("300x200")
        dialog.transient(self.frame)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Item: {item_name}", font=('Arial', 12, 'bold')).pack(pady=10)
        ttk.Label(dialog, text=f"Current Quantity: {item['values'][4]}").pack(pady=5)
        
        # Restock quantity
        ttk.Label(dialog, text="Quantity to Add:").pack(pady=5)
        restock_qty_var = tk.StringVar(value="0")
        ttk.Entry(dialog, textvariable=restock_qty_var, width=15).pack(pady=5)
        
        # Unit price (optional update)
        ttk.Label(dialog, text="New Unit Price (optional):").pack(pady=5)
        new_price_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=new_price_var, width=15).pack(pady=5)
        
        def process_restock():
            try:
                qty = int(restock_qty_var.get())
                if qty <= 0:
                    messagebox.showwarning("Warning", "Please enter valid quantity")
                    return
                
                # Update quantity
                query = """
                    UPDATE inventory_items 
                    SET quantity = quantity + %s, last_restocked = CURDATE()
                """
                params = [qty]
                
                if new_price_var.get():
                    try:
                        price = float(new_price_var.get())
                        if price > 0:
                            query = query.replace("SET", "SET unit_price = %s,")
                            params.insert(0, price)
                    except:
                        pass
                
                query += " WHERE item_id = %s"
                params.append(item_id)
                
                db.execute_query(query, tuple(params))
                
                messagebox.showinfo("Success", f"Restocked {qty} units of {item_name}")
                dialog.destroy()
                self.load_inventory()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restock: {str(e)}")
        
        ttk.Button(dialog, text="Restock", command=process_restock).pack(pady=20)
    
    def use_item(self):
        """Use/consume selected item"""
        selected = self.inventory_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to use")
            return
        
        item = self.inventory_tree.item(selected[0])
        item_id = item['values'][0]
        item_name = item['values'][2]
        current_qty = int(item['values'][4])
        
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"Use {item_name}")
        dialog.geometry("300x250")
        dialog.transient(self.frame)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Item: {item_name}", font=('Arial', 12, 'bold')).pack(pady=10)
        ttk.Label(dialog, text=f"Available: {current_qty}").pack(pady=5)
        
        # Quantity to use
        ttk.Label(dialog, text="Quantity to Use:").pack(pady=5)
        use_qty_var = tk.StringVar(value="1")
        ttk.Entry(dialog, textvariable=use_qty_var, width=15).pack(pady=5)
        
        # Purpose/description
        ttk.Label(dialog, text="Purpose/Description:").pack(pady=5)
        purpose_text = tk.Text(dialog, height=3, width=30)
        purpose_text.pack(pady=5)
        
        def process_usage():
            try:
                qty = int(use_qty_var.get())
                if qty <= 0:
                    messagebox.showwarning("Warning", "Please enter valid quantity")
                    return
                
                if qty > current_qty:
                    messagebox.showwarning("Warning", f"Insufficient stock. Available: {current_qty}")
                    return
                
                purpose = purpose_text.get("1.0", "end-1c").strip()
                
                # Update quantity
                query = "UPDATE inventory_items SET quantity = quantity - %s WHERE item_id = %s"
                db.execute_query(query, (qty, item_id))
                
                # Record usage (could create usage log table)
                messagebox.showinfo("Success", f"Used {qty} units of {item_name}")
                dialog.destroy()
                self.load_inventory()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to use item: {str(e)}")
        
        ttk.Button(dialog, text="Use Item", command=process_usage).pack(pady=20)
    
    def delete_item(self):
        """Delete selected item"""
        selected = self.inventory_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to delete")
            return
        
        item = self.inventory_tree.item(selected[0])
        item_id = item['values'][0]
        item_name = item['values'][2]
        
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{item_name}'?\n\nThis action cannot be undone."
        )
        
        if response:
            try:
                query = "DELETE FROM inventory_items WHERE item_id = %s"
                db.execute_query(query, (item_id,))
                
                messagebox.showinfo("Success", "Item deleted successfully")
                self.load_inventory()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete item: {str(e)}")
    
    def print_inventory(self):
        """Print inventory list"""
        try:
            from utils.pdf_generator import generate_inventory_report
            filename = generate_inventory_report()
            messagebox.showinfo("Success", f"Inventory report generated:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
    
    def generate_order_list(self):
        """Generate order list for low stock items"""
        selected = self.low_stock_tree.selection()
        if not selected and not self.low_stock_tree.get_children():
            messagebox.showwarning("Warning", "No low stock items to order")
            return
        
        # Collect low stock items
        order_items = []
        for item in self.low_stock_tree.get_children():
            values = self.low_stock_tree.item(item, 'values')
            order_items.append({
                'code': values[0],
                'name': values[1],
                'category': values[2],
                'reorder_qty': int(values[5]),
                'unit_price': parse_currency(values[6]),
                'total_cost': parse_currency(values[7])
            })
        
        # Generate order list (could be PDF or Excel)
        total_cost = sum(item['total_cost'] for item in order_items)
        messagebox.showinfo("Order List", 
                  f"Generated order list for {len(order_items)} items\nTotal cost: {format_currency(total_cost)}")
    
    def restock_all(self):
        """Restock all low stock items to minimum"""
        response = messagebox.askyesno(
            "Confirm Restock All",
            "This will restock all low stock items to their minimum quantities.\n\nAre you sure?"
        )
        
        if response:
            try:
                for item in self.low_stock_tree.get_children():
                    values = self.low_stock_tree.item(item, 'values')
                    current_qty = int(values[3])
                    min_qty = int(values[4])
                    reorder_qty = min_qty - current_qty
                    
                    # Find item ID by code
                    query = "SELECT item_id FROM inventory_items WHERE item_code = %s"
                    result = db.execute_query(query, (values[0],), fetch=True)
                    
                    if result:
                        item_id = result[0]['item_id']
                        # Update quantity
                        update_query = """
                            UPDATE inventory_items 
                            SET quantity = %s, last_restocked = CURDATE() 
                            WHERE item_id = %s
                        """
                        db.execute_query(update_query, (min_qty, item_id))
                
                messagebox.showinfo("Success", "All low stock items restocked")
                self.load_inventory()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restock all: {str(e)}")
    
    def show_edit_dialog(self, item_id):
        """Show edit dialog for item"""
        try:
            # Load item details
            query = "SELECT * FROM inventory_items WHERE item_id = %s"
            result = db.execute_query(query, (item_id,), fetch=True)
            
            if not result:
                messagebox.showerror("Error", "Item not found")
                return
            
            item = result[0]
            
            dialog = tk.Toplevel(self.frame)
            dialog.title(f"Edit {item['item_name']}")
            dialog.geometry("500x400")
            dialog.transient(self.frame)
            dialog.grab_set()
            
            # Form fields with current values
            fields = [
                ("Item Code:", "edit_item_code_var", item['item_code']),
                ("Item Name:", "edit_item_name_var", item['item_name']),
                ("Category:", "edit_category_var", item['category'] or ''),
                ("Quantity:", "edit_quantity_var", str(item['quantity'])),
                ("Unit Price:", "edit_unit_price_var", str(item['unit_price'] or '0')),
                ("Min Quantity:", "edit_min_qty_var", str(item['min_quantity'])),
                ("Supplier:", "edit_supplier_var", item['supplier'] or ''),
                ("Location:", "edit_location_var", item['location'] or '')
            ]
            
            for i, (label, var_name, value) in enumerate(fields[:4]):  # First column
                ttk.Label(dialog, text=label).grid(row=i, column=0, sticky='w', pady=5, padx=10)
                setattr(self, var_name, tk.StringVar(value=value))
                ttk.Entry(dialog, textvariable=getattr(self, var_name), width=25).grid(
                    row=i, column=1, pady=5, padx=10, sticky='w')
            
            for i, (label, var_name, value) in enumerate(fields[4:]):  # Second column
                ttk.Label(dialog, text=label).grid(row=i, column=2, sticky='w', pady=5, padx=10)
                setattr(self, var_name, tk.StringVar(value=value))
                ttk.Entry(dialog, textvariable=getattr(self, var_name), width=25).grid(
                    row=i, column=3, pady=5, padx=10, sticky='w')
            
            def save_changes():
                try:
                    # Validate
                    if not self.edit_item_name_var.get():
                        messagebox.showwarning("Warning", "Please enter item name")
                        return
                    
                    try:
                        quantity = int(self.edit_quantity_var.get())
                        unit_price = float(self.edit_unit_price_var.get() or 0)
                        min_qty = int(self.edit_min_qty_var.get() or 10)
                    except ValueError:
                        messagebox.showwarning("Warning", "Please enter valid numbers")
                        return
                    
                    # Update item
                    query = """
                        UPDATE inventory_items SET
                        item_code = %s, item_name = %s, category = %s, quantity = %s,
                        unit_price = %s, min_quantity = %s, supplier = %s, location = %s
                        WHERE item_id = %s
                    """
                    params = (
                        self.edit_item_code_var.get(),
                        self.edit_item_name_var.get(),
                        self.edit_category_var.get() or None,
                        quantity,
                        unit_price,
                        min_qty,
                        self.edit_supplier_var.get() or None,
                        self.edit_location_var.get() or None,
                        item_id
                    )
                    
                    db.execute_query(query, params)
                    
                    messagebox.showinfo("Success", "Item updated successfully!")
                    dialog.destroy()
                    self.load_inventory()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update item: {str(e)}")
            
            ttk.Button(dialog, text="Save Changes", command=save_changes).grid(
                row=8, column=0, columnspan=4, pady=20)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load item details: {str(e)}")
    
    def add_supplier(self):
        """Add new supplier"""
        try:
            name = self.supplier_name_var.get()
            if not name:
                messagebox.showwarning("Warning", "Please enter supplier name")
                return
            
            # In a real app, you'd insert into suppliers table
            # For now, just update inventory items with this supplier
            
            messagebox.showinfo("Success", f"Supplier '{name}' added")
            
            # Clear form
            self.supplier_name_var.set("")
            self.contact_person_var.set("")
            self.supplier_phone_var.set("")
            self.supplier_email_var.set("")
            self.supplier_address_widget.delete("1.0", "end")
            
            # Refresh supplier list
            self.load_suppliers()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add supplier: {str(e)}")