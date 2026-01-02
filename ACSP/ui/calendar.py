import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import calendar
from datetime import datetime, timedelta
from ..database import get_connection, add_maintenance_history, update_maintenance_history, delete_maintenance_history
from .styles import COLORS, FONTS  # Re-use styles if possible or just use defaults

class CanvasCalendar(tk.Frame):
    def __init__(self, master, year, month, equipment_map=None, select_callback=None):
        super().__init__(master)
        self.year = year
        self.month = month
        self.equipment_map = equipment_map if equipment_map else {}
        self.select_callback = select_callback
        self.selected_day = None
        self.cell_width = 80
        self.cell_height = 75
        self.header_height = 100
        
        self.canvas = tk.Canvas(
            self,
            width=self.cell_width*7,
            height=self.header_height + self.cell_height*6 + 10,
            bg='white'
        )
        self.canvas.pack()
        self.draw_calendar()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.tag_bind("prev_month", "<Button-1>", self.on_prev_month)
        self.canvas.tag_bind("next_month", "<Button-1>", self.on_next_month)

    def draw_calendar(self):
        self.canvas.delete("all")
        # Icons
        icon_y = 36
        icon_size = 22
        self.prev_icon = self.canvas.create_text(32, icon_y, text="◀", font=("Segoe UI", icon_size, "bold"), fill="#2667c9", activefill="#114488", tags="prev_month")
        self.next_icon = self.canvas.create_text(self.cell_width*7-32, icon_y, text="▶", font=("Segoe UI", icon_size, "bold"), fill="#2667c9", activefill="#114488", tags="next_month")
        
        # Header
        month_year_str = f"{self.year}년 {self.month:02d}월"
        self.canvas.create_text(
            self.cell_width*3.5, 30,
            text=month_year_str,
            font=("Segoe UI", 24, "bold"),
            fill="#222",
            anchor="n"
        )
        
        # Days Header
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        for i, day in enumerate(days):
            self.canvas.create_rectangle(i*self.cell_width, self.header_height-30, (i+1)*self.cell_width, self.header_height-10, fill="#f0f4fa", outline="#e0e6ef")
            self.canvas.create_text(i*self.cell_width + self.cell_width//2, self.header_height-20, text=day, font=("Segoe UI", 14, "bold"), fill="#2667c9")
            
        # Days cells
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.year, self.month)
        
        for week_idx, week in enumerate(month_days):
            for day_idx, day in enumerate(week):
                x = day_idx * self.cell_width
                y = self.header_height + week_idx * self.cell_height
                
                # Background
                self.canvas.create_rectangle(x, y, x+self.cell_width, y+self.cell_height, fill="#fbfcfd", outline="#e0e6ef", width=2)
                
                if day != 0:
                    date_str = f"{self.year}-{self.month:02d}-{day:02d}"
                    eq_data = self.equipment_map.get(date_str, {})
                    
                    today = datetime.now().date()
                    this_day = datetime(self.year, self.month, day).date()
                    
                    if self.selected_day == day:
                        self.canvas.create_rectangle(x+4, y+4, x+self.cell_width-4, y+self.cell_height-4, fill="#e3f0ff", outline="#2667c9", width=3)
                    elif this_day == today:
                        self.canvas.create_oval(x+7, y+7, x+self.cell_width-7, y+self.cell_height-32, outline="#ffb347", width=2)
                        
                    self.canvas.create_text(x+14, y+12, text=str(day), anchor='nw', font=("Segoe UI", 13, "bold"), fill="#222")
                    
                    # Draw QC (Top)
                    qc_ids = eq_data.get('QC', [])
                    if qc_ids:
                        qc_text = ",".join(qc_ids)
                        # Truncate if too long?
                        self.canvas.create_text(
                            x+self.cell_width//2, y+30,
                            text=qc_text,
                            fill="#FF0000", # Red for QC
                            font=("Segoe UI", 8, "bold"),
                            anchor='n'
                        )

                    # Draw ARMGC (Bottom)
                    armgc_ids = eq_data.get('ARMGC', [])
                    if armgc_ids:
                        armgc_text = ",".join(armgc_ids)
                        self.canvas.create_text(
                            x+self.cell_width//2, y+50,
                            text=armgc_text,
                            fill="#4a90e2", # Blue for ARMGC
                            font=("Segoe UI", 8, "bold"),
                            anchor='n'
                        )
        
        # Outer border
        self.canvas.create_rectangle(0, 0, self.cell_width*7, self.header_height+self.cell_height*6, outline="#b7c7e0", width=2)

    def on_prev_month(self, event=None):
        if hasattr(self.master.master, 'prev_month'):
            self.master.master.prev_month()

    def on_next_month(self, event=None):
        if hasattr(self.master.master, 'next_month'):
            self.master.master.next_month()

    def on_click(self, event):
        col = event.x // self.cell_width
        row = (event.y - self.header_height) // self.cell_height
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.year, self.month)
        
        if 0 <= row < len(month_days) and 0 <= col < 7:
            day = month_days[row][col]
            if day != 0:
                self.selected_day = day
                self.draw_calendar()
                if self.select_callback:
                    date_str = f"{self.year}-{self.month:02d}-{day:02d}"
                    self.select_callback(date_str)


class MaintenanceCalendar(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Maintenance History Calendar")
        self.geometry("900x650") # Slightly taller for buttons
        
        # Toggle Buttons (Top of info frame or top of window?)
        # Let's put a header frame at top
        # Toggle Buttons (Removed)
        # header_frame = ttk.Frame(self)
        # header_frame.pack(side='top', fill='x', padx=10, pady=5)
        
        calendar_frame = ttk.Frame(self)
        calendar_frame.pack(side='left', padx=10, pady=10, fill='both', expand=True)
        
        self.maintenance_equipment_map = {}
        self.year = datetime.now().year
        self.month = datetime.now().month
        self.current_selected_date_str = None
        
        self.load_maintenance_dates()
        
        self.cal = CanvasCalendar(calendar_frame, self.year, self.month, self.maintenance_equipment_map, self.show_maintenance_info)
        self.cal.pack(fill='both', expand=True)
        
        info_frame = ttk.Frame(self)
        info_frame.pack(side='right', padx=10, pady=10, fill='both')
        
        ttk.Label(info_frame, text="History", font=('Helvetica', 12, 'bold')).pack(pady=5)
        
        columns = ('Type', 'Equipment ID', 'Date')
        self.tree = ttk.Treeview(info_frame, columns=columns, show='headings', height=15)
        self.tree.heading('Type', text='Type')
        self.tree.column('Type', width=60)
        self.tree.heading('Equipment ID', text='ID')
        self.tree.column('Equipment ID', width=60)
        self.tree.heading('Date', text='Date')
        self.tree.column('Date', width=90)
            
        scrollbar = ttk.Scrollbar(info_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Action Buttons
        btn_frame = ttk.Frame(info_frame)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="Add", command=self.add_record).pack(side='left', padx=5, expand=True, fill='x')
        ttk.Button(btn_frame, text="Edit", command=self.edit_record).pack(side='left', padx=5, expand=True, fill='x')
        ttk.Button(btn_frame, text="Delete", command=self.delete_record).pack(side='left', padx=5, expand=True, fill='x')

    def load_maintenance_dates(self):
        two_months_ago = datetime.now() - timedelta(days=60)
        two_months_ago_str = two_months_ago.strftime('%Y-%m-%d')
        self.maintenance_equipment_map.clear()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.maintenance_date, e.type, GROUP_CONCAT(e.id)
                FROM maintenance_history m
                JOIN equipment e ON m.equipment_id = e.id
                WHERE m.maintenance_date >= ?
                GROUP BY m.maintenance_date, e.type
            ''', (two_months_ago_str,))
            
            for date, eq_type, equipment_ids in cursor.fetchall():
                if date not in self.maintenance_equipment_map:
                    self.maintenance_equipment_map[date] = {'QC': [], 'ARMGC': []}
                
                if equipment_ids:
                    # Filter out any lingering None or empty strings if specific DB implementations do something weird
                    ids = [x for x in equipment_ids.replace(' ', '').split(',') if x]
                    # Map to the correct list
                    if eq_type in self.maintenance_equipment_map[date]:
                        self.maintenance_equipment_map[date][eq_type].extend(ids)
                
        if hasattr(self, 'cal'):
            self.cal.equipment_map = self.maintenance_equipment_map
            self.cal.draw_calendar()

    def show_maintenance_info(self, date_str):
        self.current_selected_date_str = date_str
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.type, m.equipment_id, m.maintenance_date
                FROM maintenance_history m
                JOIN equipment e ON m.equipment_id = e.id
                WHERE m.maintenance_date = ?
                ORDER BY e.type DESC, m.equipment_id
            ''', (date_str,))
            
            for row in cursor.fetchall():
                self.tree.insert('', 'end', values=row)

    def prev_month(self):
        if self.month == 1:
            self.year -= 1
            self.month = 12
        else:
            self.month -= 1
        self.refresh_calendar()

    def next_month(self):
        if self.month == 12:
            self.year += 1
            self.month = 1
        else:
            self.month += 1
        self.refresh_calendar()

    def refresh_calendar(self):
        self.load_maintenance_dates()
        self.cal.year = self.year
        self.cal.month = self.month
        self.cal.selected_day = None
        self.cal.draw_calendar()
        
        # Clear selection and tree
        self.current_selected_date_str = None
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def add_record(self):
        if not self.current_selected_date_str:
            messagebox.showwarning("Select Date", "Please select a date on the calendar first.")
            return

        eq_id = simpledialog.askinteger("Add Maintenance", "Enter Equipment ID (e.g., 211):", parent=self)
        if eq_id:
            try:
                add_maintenance_history(eq_id, self.current_selected_date_str)
                self.refresh_calendar()
                self.show_maintenance_info(self.current_selected_date_str) # Refresh list
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def edit_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Record", "Please select a record from the list to edit.")
            return
            
        item = self.tree.item(selected[0])
        # values = (Type, ID, Date)
        old_id = item['values'][1]
        date_str = item['values'][2]
        
        new_id = simpledialog.askinteger("Edit Maintenance", f"Enter new Equipment ID (Current: {old_id}):", parent=self, initialvalue=old_id)
        if new_id and new_id != old_id:
            try:
                update_maintenance_history(old_id, new_id, date_str)
                self.refresh_calendar()
                self.show_maintenance_info(date_str)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def delete_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Record", "Please select a record from the list to delete.")
            return
            
        item = self.tree.item(selected[0])
        eq_id = item['values'][1]
        date_str = item['values'][2]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete maintenance record for Unit {eq_id}?"):
            try:
                delete_maintenance_history(eq_id, date_str)
                self.refresh_calendar()
                self.show_maintenance_info(date_str)
            except Exception as e:
                messagebox.showerror("Error", str(e))

