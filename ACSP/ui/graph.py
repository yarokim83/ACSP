import tkinter as tk
from tkinter import ttk
from datetime import datetime
from ..database import get_connection
from .styles import COLORS, FONTS

class OverdueGraph(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Overdue Graph")
        self.geometry("1400x600")
        
        self.current_filter = 'ARMGC' # Default
        
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Legend / Header
        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(self.header_frame, text="Overdue Analysis", font=FONTS['h2']).pack(side='left')
        
        # Filter Buttons in Header
        filter_frame = ttk.Frame(self.header_frame)
        filter_frame.pack(side='left', padx=20)
        
        self.btn_armgc = ttk.Button(filter_frame, text="ARMGC", command=lambda: self.switch_filter('ARMGC'))
        self.btn_armgc.pack(side='left', padx=2)
        self.btn_qc = ttk.Button(filter_frame, text="QC", command=lambda: self.switch_filter('QC'))
        self.btn_qc.pack(side='left', padx=2)
        
        
        legend_frame = ttk.Frame(self.header_frame)
        legend_frame.pack(side='right')
        
        self._create_legend_item(legend_frame, "Normal (< 45 days)", "#87CEEB") # SkyBlue
        ttk.Label(legend_frame, text="  ").pack(side='left')
        self._create_legend_item(legend_frame, "Overdue (> 45 days)", "#FF0000") # Red
        
        # Canvas Container
        self.canvas_container = ttk.Frame(self.main_frame)
        self.canvas_container.pack(fill='both', expand=True)
        
        self.canvas = tk.Canvas(self.canvas_container, bg='white')
        self.canvas.pack(fill='both', expand=True)
        
        # Bind resize event
        self.canvas.bind('<Configure>', self.on_resize)
        
        # Initial draw
        self.update_buttons()
        
    def _create_legend_item(self, parent, text, color):
        f = ttk.Frame(parent)
        f.pack(side='left')
        tk.Frame(f, width=15, height=15, bg=color).pack(side='left', padx=(0, 5))
        ttk.Label(f, text=text).pack(side='left')

    def switch_filter(self, filter_val):
        self.current_filter = filter_val
        self.update_buttons()
        self.draw_graph()
        
    def update_buttons(self):
        if self.current_filter == 'ARMGC':
            self.btn_armgc.state(['pressed'])
            self.btn_qc.state(['!pressed'])
        else:
            self.btn_armgc.state(['!pressed'])
            self.btn_qc.state(['pressed'])

    def on_resize(self, event):
        self.draw_graph()

    def draw_graph(self):
        self.canvas.delete('all')
        
        # Get Current Dimensions
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 100 or height < 100:
            return  # Wait for valid size
            
        # Fetch Data
        data = []
        with get_connection() as conn:
            cursor = conn.cursor()
            # We need to handle potential schema mismatch if 'type' wasn't there before commit/restart, 
            # but previous step ensured column exists.
            cursor.execute('SELECT id, last_maintenance_date, type FROM equipment ORDER BY id')
            rows = cursor.fetchall()
            
        today = datetime.now()
        for row in rows:
            eq_id = row[0]
            last_date_str = row[1]
            eq_type = row[2] if len(row) > 2 else 'ARMGC'
            
            # Filter
            if eq_type != self.current_filter:
                continue
                
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
            days_passed = (today - last_date).days
            data.append((eq_id, days_passed))
            
        if not data:
            self.canvas.create_text(width/2, height/2, text=f"No {self.current_filter} Data Available")
            return
            
        # Layout Calculations
        left_margin = 50
        right_margin = 20
        top_margin = 40
        bottom_margin = 50
        
        graph_width = width - left_margin - right_margin
        graph_height = height - top_margin - bottom_margin
        base_y = height - bottom_margin
        
        # Determine bar width dynamically
        num_items = len(data)
        item_width = graph_width / num_items
        bar_width = item_width * 0.6  # 60% bar, 40% gap
        gap = item_width * 0.4
        
        # Determine logical max Y for scaling
        max_days = max([d[1] for d in data]) if data else 50
        max_days = max(max_days, 60) # Minimum scale to 60 days
        
        scale_factor = graph_height / max_days
        
        # Draw Axes
        self.canvas.create_line(left_margin, top_margin, left_margin, base_y, fill='black', width=2) # Y-Axis
        self.canvas.create_line(left_margin, base_y, width - right_margin, base_y, fill='black', width=2) # X-Axis
        
        # Draw Grid lines (every 10 days)
        for d in range(0, max_days + 1, 10):
            y = base_y - (d * scale_factor)
            self.canvas.create_line(left_margin - 5, y, width - right_margin, y, fill='#eee', dash=(2, 2))
            self.canvas.create_text(left_margin - 10, y, text=str(d), anchor='e', font=('Arial', 8))
            
        # Draw Threshold Line (45 days)
        y_45 = base_y - (45 * scale_factor)
        self.canvas.create_line(left_margin, y_45, width - right_margin, y_45, fill='#FFA500', dash=(4, 4), width=1)
        self.canvas.create_text(width - right_margin - 10, y_45 - 20, text="45 Days Limit", fill='#FFA500', anchor='e', font=('Arial', 9, 'bold'))

        # Draw Bars
        current_x = left_margin + (gap / 2)
        
        for eq_id, days in data:
            blue_h = min(days, 45) * scale_factor
            red_h = max(0, days - 45) * scale_factor
            
            x0 = current_x
            x1 = current_x + bar_width
            
            # Blue Bar
            self.canvas.create_rectangle(x0, base_y - blue_h, x1, base_y, fill='#87CEEB', outline='')
            
            # Red Bar
            if red_h > 0:
                y_red_base = base_y - blue_h
                self.canvas.create_rectangle(x0, y_red_base - red_h, x1, y_red_base, fill='#FF0000', outline='')
                
            # X-Axis Labels
            font_size = 8 if bar_width < 15 else 9
            self.canvas.create_text((x0 + x1)/2, base_y + 15, text=str(eq_id), font=('Arial', font_size))
            
            # Value Label
            total_h = blue_h + red_h
            if bar_width > 12:
                self.canvas.create_text((x0 + x1)/2, base_y - total_h - 10, text=str(days), font=('Arial', font_size, 'bold'))
            
            current_x += item_width

