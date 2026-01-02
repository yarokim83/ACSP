import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from ..database import get_connection
from .calendar import MaintenanceCalendar
from .graph import OverdueGraph
from .styles import apply_styles, COLORS, FONTS

class ACSPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ACSP - Ai Crane Scheduler Program")
        self.root.geometry("1200x800")
        
        self.style = apply_styles(root)
        
        # Main Layout Container
        self.main_container = ttk.Frame(self.root, style='Main.TFrame')
        self.main_container.pack(fill='both', expand=True)
        
        # Sidebar
        self.create_sidebar()
        
        # Content Area
        self.content_area = ttk.Frame(self.main_container, style='Main.TFrame')
        self.content_area.pack(side='left', fill='both', expand=True, padx=20, pady=20)
        
        self.create_dashboard()
        
        # Initial Data Load
        self.current_type_filter = 'ARMGC' # Default
        self.current_status_filter = 'all'
        self.load_data()

    def create_sidebar(self):
        sidebar = ttk.Frame(self.main_container, style='Sidebar.TFrame', width=250)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False) # Force width
        
        # Logo / Title
        title_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        title_frame.pack(fill='x', pady=(30, 40), padx=20)
        ttk.Label(title_frame, text="ACSP", style='SidebarTitle.TLabel').pack(anchor='w')
        ttk.Label(title_frame, text="Crane Scheduler", style='Sidebar.TLabel').pack(anchor='w')
        
        # Stats Widget
        self.stats_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        self.stats_frame.pack(fill='x', padx=20, pady=20)
        
        self._create_stat_item(self.stats_frame, "Total Equipment", "total_val")
        self._create_stat_item(self.stats_frame, "Overdue", "overdue_val")
        self._create_stat_item(self.stats_frame, "Warning", "warning_val")

        # Navigation Buttons (Spacer)
        ttk.Frame(sidebar, style='Sidebar.TFrame', height=40).pack()
        
        ttk.Button(sidebar, text=" 📅  Calendar View", style='Sidebar.TButton', command=self.show_calendar).pack(fill='x', padx=10, pady=5)
        ttk.Button(sidebar, text=" 📊  Overdue Graph", style='Sidebar.TButton', command=self.show_graph).pack(fill='x', padx=10, pady=5)

        
        # Bottom info
        bottom_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        bottom_frame.pack(side='bottom', fill='x', pady=20, padx=20)
        ttk.Label(bottom_frame, text="v1.0.1", style='Sidebar.TLabel', font=FONTS['small']).pack(anchor='w')

    def _create_stat_item(self, parent, label, var_name):
        f = ttk.Frame(parent, style='Sidebar.TFrame')
        f.pack(fill='x', pady=10)
        ttk.Label(f, text=label, style='SidebarStat.TLabel').pack(anchor='w')
        lbl = ttk.Label(f, text="0", style='SidebarStatValue.TLabel')
        lbl.pack(anchor='w')
        setattr(self, var_name, lbl)

    def create_dashboard(self):
        # 1. Input / Action Card
        action_card = ttk.Frame(self.content_area, style='Card.TFrame', padding=20)
        action_card.pack(fill='x', pady=(0, 20))
        
        ttk.Label(action_card, text="Record Maintenance", style='CardHeader.TLabel').pack(anchor='w', pady=(0, 15))
        
        input_container = ttk.Frame(action_card, style='Card.TFrame')
        input_container.pack(fill='x')
        
        # Selected Equipment Label (Dynamic Feedback)
        self.selected_eq_label = ttk.Label(input_container, text="No Equipment Selected", style='Card.TLabel', foreground=COLORS['warning'])
        self.selected_eq_label.pack(side='left', padx=(0, 20))

        # Date
        date_frame = ttk.Frame(input_container, style='Card.TFrame')
        date_frame.pack(side='left', padx=(0, 15))
        ttk.Label(date_frame, text="Maintenance Date", style='Card.TLabel').pack(anchor='w', pady=(0,5))
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.date_entry = ttk.Entry(date_frame, textvariable=self.date_var, width=15)
        self.date_entry.pack()
        
        # Button
        btn_frame = ttk.Frame(input_container, style='Card.TFrame')
        btn_frame.pack(side='left', padx=(0, 15), fill='y') # Vertical align bottom
        
        # Spacer to push button down to align with inputs
        ttk.Label(btn_frame, text="", style='Card.TLabel').pack() 
        ttk.Button(btn_frame, text="COMPLETE MAINTENANCE", style='Action.TButton', command=self.complete_maintenance).pack(pady=(2,0))

        # 2. Main List Card
        list_card = ttk.Frame(self.content_area, style='Card.TFrame', padding=20)
        list_card.pack(fill='both', expand=True)

        # List Header & Filters
        header_frame = ttk.Frame(list_card, style='Card.TFrame')
        header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(header_frame, text="Equipment Status", style='CardHeader.TLabel').pack(side='left')
        
        # Type Filters (Left side of header or separate?)
        # Let's put them on the left of filters or simply add them
        
        type_frame = ttk.Frame(header_frame, style='Card.TFrame')
        type_frame.pack(side='right', padx=(0, 20))
        
        self.btn_armgc = ttk.Button(type_frame, text="ARMGC", command=lambda: self.switch_type('ARMGC'))
        self.btn_armgc.pack(side='left', padx=2)
        
        self.btn_qc = ttk.Button(type_frame, text="QC", command=lambda: self.switch_type('QC'))
        self.btn_qc.pack(side='left', padx=2)
        
        separ = ttk.Separator(header_frame, orient='vertical')
        separ.pack(side='right', fill='y', padx=10)

        # Status Filter Buttons
        filter_frame = ttk.Frame(header_frame, style='Card.TFrame')
        filter_frame.pack(side='right')
        
        ttk.Button(filter_frame, text="All", command=lambda: self.switch_status('all')).pack(side='left', padx=2)
        ttk.Button(filter_frame, text="Overdue", command=lambda: self.switch_status('overdue')).pack(side='left', padx=2)
        ttk.Button(filter_frame, text="Warning", command=lambda: self.switch_status('warning')).pack(side='left', padx=2)

        # Treeview
        columns = ('ID', 'Last Maintenance', 'Status', 'Days Passed', 'Remaining')
        self.tree = ttk.Treeview(list_card, columns=columns, show='headings', height=15)
        
        widths = [100, 150, 120, 100, 100]
        aligns = ['center', 'center', 'center', 'center', 'center']
        for col, width, align in zip(columns, widths, aligns):
            self.tree.heading(col, text=col.upper(), command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=width, anchor=align)
        
        self.sort_column = None
        self.sort_reverse = False
        
        scrollbar = ttk.Scrollbar(list_card, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # Tags for colored text
        self.tree.tag_configure('overdue', foreground=COLORS['danger'])
        self.tree.tag_configure('warning', foreground=COLORS['warning'])
        self.tree.tag_configure('good', foreground=COLORS['success'])

    # -------------------------------------------------------------------------
    # Logic
    # -------------------------------------------------------------------------
    def on_select(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            self.selected_eq_label.config(text="No Equipment Selected", foreground=COLORS['text'])
            return
            
        item = self.tree.item(selected_item[0])
        equipment_id = str(item['values'][0])
        self.selected_eq_label.config(text=f"Selected: Unit {equipment_id}", foreground=COLORS['accent'])

    def sort_treeview(self, column):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
        self.sort_column = column
        
        items = [(self.tree.set(item, column), item) for item in self.tree.get_children('')]
        
        def sort_key(val):
            try:
                # Handle "X days" format
                if isinstance(val, str) and ' days' in val:
                    return int(val.replace(' days', ''))
                # Handle pure numbers
                return int(val)
            except ValueError:
                # Fallback to string
                return val
        
        items.sort(key=lambda x: sort_key(x[0]), reverse=self.sort_reverse)
            
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)

    def switch_type(self, type_val):
        self.current_type_filter = type_val
        self.load_data()

    def switch_status(self, status):
        self.current_status_filter = status
        self.load_data()

    def load_data(self, filter_mode=None):
        if filter_mode:
            self.current_status_filter = filter_mode
            
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # UI Feedback for active filter (Optional but good)
        if self.current_type_filter == 'ARMGC':
            self.btn_armgc.state(['pressed'])
            self.btn_qc.state(['!pressed'])
        else:
            self.btn_armgc.state(['!pressed'])
            self.btn_qc.state(['pressed'])
            
        total_cnt = 0
        overdue_cnt = 0
        warning_cnt = 0
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM equipment')
            rows = cursor.fetchall()
            
        for row in rows:
            # Row structure: id, last_date, next_date, type (if using index access, be careful with new column)
            # Safe unpacking if column count varies?
            # Creating dict or just using index
            id_val = row[0]
            last_date = row[1]
            eq_type = row[3] if len(row) > 3 else 'ARMGC' # Default fallback
            
            # Type Filter
            if eq_type != self.current_type_filter:
                continue
                
            total_cnt += 1
            
            last_maintenance = datetime.strptime(last_date, '%Y-%m-%d')
            today_date = datetime.now()
            days_passed = (today_date - last_maintenance).days
            days_remaining = 45 - days_passed
            
            status_text = "Good"
            tag = 'good'
            
            if days_remaining < 0:
                tag = 'overdue'
                status_text = "OVERDUE"
                overdue_cnt += 1
            elif days_remaining < 10:
                tag = 'warning'
                status_text = "Warning"
                warning_cnt += 1
            
            # Status Filter
            if self.current_status_filter == 'overdue' and tag != 'overdue':
                continue
            if self.current_status_filter == 'warning' and tag != 'warning':
                continue
            
            self.tree.insert('', 'end', values=(
                id_val,
                last_date,
                status_text,
                f"{days_passed} days",
                f"{days_remaining} days"
            ), tags=(tag,))
            
        # Update Stats
        self.total_val.config(text=str(total_cnt))
        self.overdue_val.config(text=str(overdue_cnt))
        self.warning_val.config(text=str(warning_cnt))

    def complete_maintenance(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Select Equipment", "Please select equipment from the list below.")
            return
            
        item = self.tree.item(selected_item[0])
        equipment_id = str(item['values'][0])
        
        try:
            selected_date = datetime.strptime(self.date_var.get(), '%Y-%m-%d')
        except Exception:
            messagebox.showerror("Date Error", "Invalid date format. Use YYYY-MM-DD.")
            return
            
        maintenance_date = selected_date.strftime('%Y-%m-%d')
        next_date = (selected_date + timedelta(days=45)).strftime('%Y-%m-%d')
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE equipment 
                SET last_maintenance_date = ?, 
                    next_maintenance_date = ?
                WHERE id = ?
            ''', (maintenance_date, next_date, equipment_id))
            
            cursor.execute('''
                INSERT INTO maintenance_history (equipment_id, maintenance_date)
                VALUES (?, ?)
            ''', (equipment_id, maintenance_date))
            
            conn.commit()
        
        self.load_data()
        messagebox.showinfo("Success", f"Maintenance recorded for Unit {equipment_id}")

    def show_calendar(self):
        cal_win = MaintenanceCalendar(self.root)
        cal_win.transient(self.root)
        cal_win.grab_set()

    def show_graph(self):
        graph_win = OverdueGraph(self.root)
        graph_win.transient(self.root)
        # graph_win.grab_set() # Optional: Modal or not? Let's keep it non-modal so they can compare

