import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import config
from database.connection import db

class DashboardTab:
    def __init__(self, parent, role: str = 'Administrator'):
        self.parent = parent
        self.role = role
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        self.refresh_data()
        
    def setup_ui(self):
        """Setup dashboard UI"""
        # Main container with scrollbar
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient='vertical', command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create window and ensure it always matches canvas width so cards fill available space
        self._dashboard_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # When canvas resizes, update inner window width to match so content stretches
        def _on_canvas_config(event):
            try:
                canvas.itemconfigure(self._dashboard_window, width=event.width)
            except Exception:
                pass

        canvas.bind('<Configure>', _on_canvas_config)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Title
        title_frame = ttk.Frame(self.scrollable_frame)
        title_frame.pack(fill='x', pady=20)
        
        ttk.Label(
            title_frame,
            text=f"{config.Config.SCHOOL_NAME} Dashboard",
            font=('Arial', 20, 'bold')
        ).pack()
        
        ttk.Label(
            title_frame,
            text=f"{date.today().strftime('%A, %B %d, %Y')}",
            font=('Arial', 12)
        ).pack(pady=5)
        
        # Stats cards
        # Prepare stats vars container used by stat cards
        self.stats_vars = {}
        self.setup_stats_cards()
        
        # Recent activities
        self.setup_recent_activities()
        
        # Quick actions
        self.setup_quick_actions()
        
        # Calendar
        self.setup_calendar()
        
    def setup_stats_cards(self):
        """Setup statistics cards"""
        stats_frame = ttk.LabelFrame(self.scrollable_frame, text="Statistics", padding=15)
        stats_frame.pack(fill='x', padx=20, pady=10)
        
        # Create 6 stat cards
        self.stat_cards = []
        stats_info = [
            ('👨‍🎓', 'Total Students', 'students', '#4CAF50'),
            ('👨‍🏫', 'Total Teachers', 'teachers', '#2196F3'),
            ('📊', 'Today\'s Attendance', 'today_attendance', '#9C27B0'),
        ]

        # Finance-related cards (only for Administrator and Finance roles)
        if self.role in ('Administrator', 'Finance'):
            stats_info.append(('💰', 'Today\'s Income', 'today_income', '#FF9800'))
            stats_info.append(('📦', 'Low Stock Items', 'low_stock', '#F44336'))
            stats_info.append(('📋', 'Pending Fees', 'pending_fees', '#607D8B'))
        
        for i in range(0, len(stats_info), 3):
            row_frame = ttk.Frame(stats_frame)
            row_frame.pack(fill='x', pady=5)
            
            for j in range(3):
                if i + j < len(stats_info):
                    icon, title, key, color = stats_info[i + j]
                    card = self.create_stat_card(row_frame, icon, title, key, color)
                    card.pack(side='left', fill='both', expand=True, padx=5)
                    self.stat_cards.append(card)
    
    def create_stat_card(self, parent, icon, title, key, color):
        """Create a single stat card"""
        card = ttk.Frame(parent, relief='solid', borderwidth=1)
        
        # Icon and title
        icon_frame = ttk.Frame(card)
        icon_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        ttk.Label(icon_frame, text=icon, font=('Arial', 20)).pack(side='left')
        ttk.Label(icon_frame, text=title, font=('Arial', 10)).pack(side='left', padx=10)
        
        # Value
        self.stats_vars[key] = tk.StringVar(value="0")
        value_label = ttk.Label(
            card,
            textvariable=self.stats_vars[key],
            font=('Arial', 18, 'bold')
        )
        value_label.pack(pady=(0, 10))
        
        # Store card info
        card.key = key
        card.color = color
        
        return card
    
    def setup_recent_activities(self):
        """Setup recent activities section"""
        activities_frame = ttk.LabelFrame(self.scrollable_frame, text="Recent Activities", padding=10)
        activities_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Treeview for activities
        columns = ('Time', 'Activity', 'Details', 'User')
        self.activities_tree = ttk.Treeview(
            activities_frame,
            columns=columns,
            show='headings',
            height=8
        )
        
        # Configure columns
        self.activities_tree.heading('Time', text='Time')
        self.activities_tree.heading('Activity', text='Activity')
        self.activities_tree.heading('Details', text='Details')
        self.activities_tree.heading('User', text='User')
        
        self.activities_tree.column('Time', width=120)
        self.activities_tree.column('Activity', width=150)
        self.activities_tree.column('Details', width=250)
        self.activities_tree.column('User', width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(activities_frame, orient='vertical', command=self.activities_tree.yview)
        self.activities_tree.configure(yscrollcommand=scrollbar.set)
        
        self.activities_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Load activities
        self.load_recent_activities()
    
    def setup_quick_actions(self):
        """Setup quick action buttons"""
        actions_frame = ttk.LabelFrame(self.scrollable_frame, text="Quick Actions", padding=10)
        actions_frame.pack(fill='x', padx=20, pady=10)
        
        actions = [
            ('📝 Take Attendance', self.take_attendance),
            ('➕ Add Student', self.add_student),
            ('📊 Generate Report', self.generate_report),
            ('📨 Send Notifications', self.send_notifications)
        ]

        # Add finance actions only for Administrator and Finance
        if self.role in ('Administrator', 'Finance'):
            actions.insert(1, ('💰 Record Payment', self.record_payment))
            actions.append(('📦 Check Inventory', self.check_inventory))
        
        for i in range(0, len(actions), 3):
            row_frame = ttk.Frame(actions_frame)
            row_frame.pack(fill='x', pady=5)
            
            for j in range(3):
                if i + j < len(actions):
                    text, command = actions[i + j]
                    btn = ttk.Button(
                        row_frame,
                        text=text,
                        command=command,
                        width=20
                    )
                    btn.pack(side='left', padx=5, expand=True, fill='x')
    
    def setup_calendar(self):
        """Setup calendar view"""
        calendar_frame = ttk.LabelFrame(self.scrollable_frame, text="Upcoming Events", padding=10)
        calendar_frame.pack(fill='x', padx=20, pady=(10, 20))
        
        # Get current month and year
        today = date.today()
        current_month = today.strftime('%B %Y')
        
        ttk.Label(calendar_frame, text=current_month, font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Calendar grid
        self.calendar_frame = ttk.Frame(calendar_frame)
        self.calendar_frame.pack(fill='x')
        
        # Day headers
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day in enumerate(days):
            ttk.Label(self.calendar_frame, text=day, width=10, anchor='center').grid(
                row=0, column=i, padx=2, pady=2
            )
        
        # Calendar cells will be populated in refresh_data
    
    def refresh_data(self):
        """Refresh all dashboard data"""
        self.load_statistics()
        self.load_recent_activities()
        self.load_calendar()
    
    def load_statistics(self):
        """Load statistics from database"""
        try:
            # Total students
            query = "SELECT COUNT(*) as count FROM students WHERE is_active = 1"
            result = db.execute_query(query, fetch=True)
            if result:
                self.stats_vars['students'].set(str(result[0]['count']))
            
            # Total teachers
            query = "SELECT COUNT(*) as count FROM teachers WHERE is_active = 1"
            result = db.execute_query(query, fetch=True)
            if result:
                self.stats_vars['teachers'].set(str(result[0]['count']))
            
            # Today's income (only for Administrator and Finance)
            if self.role in ('Administrator', 'Finance'):
                query = """
                    SELECT COALESCE(SUM(amount_paid), 0) as total 
                    FROM student_fees 
                    WHERE DATE(payment_date) = CURDATE()
                """
                result = db.execute_query(query, fetch=True)
                if result:
                    from utils.helpers import format_currency
                    self.stats_vars['today_income'].set(format_currency(float(result[0]['total'])))
            
            # Today's attendance
            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present
                FROM attendance 
                WHERE attendance_date = CURDATE()
            """
            result = db.execute_query(query, fetch=True)
            if result and result[0]['total'] > 0:
                percentage = (result[0]['present'] / result[0]['total']) * 100
                self.stats_vars['today_attendance'].set(f"{percentage:.1f}%")
            else:
                self.stats_vars['today_attendance'].set("No data")
            
            # Low stock items (only for Administrator and Finance)
            if self.role in ('Administrator', 'Finance'):
                query = """
                    SELECT COUNT(*) as count 
                    FROM inventory_items 
                    WHERE quantity < min_quantity
                """
                result = db.execute_query(query, fetch=True)
                if result:
                    self.stats_vars['low_stock'].set(str(result[0]['count']))
            
            # Pending fees (students with balance > 0) - only for Administrator and Finance
            if self.role in ('Administrator', 'Finance'):
                acad_year = config.Config.CURRENT_ACADEMIC_YEAR
                query = f"""
                    SELECT COUNT(DISTINCT s.student_id) as count
                    FROM students s
                    JOIN (
                        SELECT 
                            s.student_id,
                            SUM(
                                CASE
                                    WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                                    WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                                    ELSE ft.amount
                                END
                            ) - COALESCE(SUM(sf.amount_paid), 0) as balance
                        FROM students s
                        CROSS JOIN fee_types ft
                        LEFT JOIN student_fees sf ON s.student_id = sf.student_id 
                            AND ft.fee_type_id = sf.fee_type_id
                        WHERE ft.academic_year = '{acad_year}'
                        GROUP BY s.student_id
                        HAVING balance > 0
                    ) balances ON s.student_id = balances.student_id
                    WHERE s.is_active = 1
                """
                result = db.execute_query(query, fetch=True)
                if result:
                    self.stats_vars['pending_fees'].set(str(result[0]['count']))
                
        except Exception as e:
            print(f"Error loading statistics: {e}")
    
    def load_recent_activities(self):
        """Load recent activities"""
        # Clear existing items
        for item in self.activities_tree.get_children():
            self.activities_tree.delete(item)
        
        try:
            # Get recent fee payments
            query = """
                SELECT 
                    sf.payment_date as time,
                    CONCAT('Fee Payment - ', s.first_name, ' ', s.last_name) as activity,
                    CONCAT(%s, sf.amount_paid, ' (', ft.fee_name, ')') as details,
                    'System' as user
                FROM student_fees sf
                JOIN students s ON sf.student_id = s.student_id
                JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
                ORDER BY sf.payment_date DESC, sf.created_at DESC
                LIMIT 10
            """

            results = db.execute_query(query, (config.Config.CURRENCY_SYMBOL,), fetch=True)
            for row in results:
                self.activities_tree.insert('', 'end', values=(
                    row['time'],
                    row['activity'],
                    row['details'],
                    row['user']
                ))
                
        except Exception as e:
            print(f"Error loading activities: {e}")
    
    def load_calendar(self):
        """Load calendar events"""
        try:
            # Clear existing calendar (except headers)
            for widget in self.calendar_frame.winfo_children():
                if widget.grid_info()['row'] > 0:
                    widget.destroy()
            
            today = date.today()
            first_day = today.replace(day=1)
            
            # Get events for current month
            query = """
                SELECT 
                    attendance_date as event_date,
                    'Attendance Day' as event_type,
                    COUNT(*) as student_count
                FROM attendance
                WHERE MONTH(attendance_date) = MONTH(CURDATE())
                    AND YEAR(attendance_date) = YEAR(CURDATE())
                GROUP BY attendance_date
                ORDER BY attendance_date
            """
            
            events = {}
            results = db.execute_query(query, fetch=True)
            for row in results:
                event_date = row['event_date']
                if isinstance(event_date, str):
                    event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
                events[event_date] = {
                    'type': row['event_type'],
                    'count': row['student_count']
                }
            
            # Fill calendar
            current_row = 1
            current_col = (first_day.weekday() + 1) % 7  # Adjust for Monday start
            
            for day in range(1, 32):  # Max 31 days
                try:
                    current_date = today.replace(day=day)
                    day_frame = ttk.Frame(self.calendar_frame, relief='solid', borderwidth=1, width=100, height=80)
                    day_frame.grid(row=current_row, column=current_col, padx=2, pady=2, sticky='nsew')
                    day_frame.grid_propagate(False)
                    
                    # Day number
                    day_label = ttk.Label(day_frame, text=str(day))
                    day_label.pack(anchor='nw', padx=5, pady=5)
                    
                    # Highlight today
                    if day == today.day:
                        day_frame.configure(relief='raised', borderwidth=2)
                        day_label.configure(foreground='red')
                    
                    # Add event indicator
                    if current_date in events:
                        event = events[current_date]
                        event_label = ttk.Label(
                            day_frame,
                            text=f"📋 {event['count']}",
                            font=('Arial', 8)
                        )
                        event_label.pack(side='bottom', fill='x')
                    
                    current_col += 1
                    if current_col >= 7:
                        current_col = 0
                        current_row += 1
                        
                except ValueError:
                    # Day out of range for this month
                    break
            
        except Exception as e:
            print(f"Error loading calendar: {e}")
    
    def take_attendance(self):
        """Open attendance tab"""
        # Switch to Attendance tab in the main notebook (if present)
        if self.select_tab_by_name('Attendance'):
            return
        messagebox.showinfo("Quick Action", "Attendance tab not available")
    
    def record_payment(self):
        """Record a payment"""
        # Open fee payment dialog if Students tab exists (user can select student there)
        # Otherwise show informational message.
        if self.select_tab_by_name('Students'):
            # Selecting Students tab will allow recording payments from there
            return
        messagebox.showinfo("Quick Action", "Opening fee payment dialog...")
    
    def add_student(self):
        """Add new student"""
        # Select the Students tab and let the user click Add, or open Students tab directly
        if self.select_tab_by_name('Students'):
            return
        messagebox.showinfo("Quick Action", "Students tab not available")
    
    def generate_report(self):
        """Generate report"""
        # Select Reports tab if available
        if self.select_tab_by_name('Reports'):
            return
        messagebox.showinfo("Quick Action", "Reports tab not available")
    
    def check_inventory(self):
        """Check inventory"""
        if self.select_tab_by_name('Inventory'):
            return
        messagebox.showinfo("Quick Action", "Inventory tab not available")
    
    def send_notifications(self):
        """Send notifications"""
        messagebox.showinfo("Quick Action", "Opening notification system...")

    def select_tab_by_name(self, name: str) -> bool:
        """Select a notebook tab by its displayed text. Returns True if selected."""
        try:
            for tab_id in self.parent.tabs():
                if self.parent.tab(tab_id, 'text') == name:
                    self.parent.select(tab_id)
                    return True
        except Exception:
            pass
        return False