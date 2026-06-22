import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from ..database import get_connection
from .styles import COLORS, FONTS

class RMListWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("RM List - Running Repair & Maintenance")
        self.geometry("950x650")
        self.configure(bg=COLORS['bg'])
        
        # Main container
        self.main_frame = ttk.Frame(self, style='Main.TFrame')
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 1. Header Frame
        self.header_frame = ttk.Frame(self.main_frame, style='Main.TFrame')
        self.header_frame.pack(fill='x', pady=(0, 15))
        ttk.Label(self.header_frame, text="🔧 Running Repair & Maintenance (RM) List", font=FONTS['h1'], background=COLORS['bg']).pack(side='left')
        
        # 2. Input Card (Add RM)
        self.create_input_card()
        
        # 3. List Card (RM Table)
        self.create_list_card()
        
        # Load Data
        self.load_data()
        
    def create_input_card(self):
        input_card = ttk.Frame(self.main_frame, style='Card.TFrame', padding=15)
        input_card.pack(fill='x', pady=(0, 15))
        
        ttk.Label(input_card, text="Add New RM Record", style='CardHeader.TLabel').grid(row=0, column=0, columnspan=5, sticky='w', pady=(0, 10))
        
        # Labels
        ttk.Label(input_card, text="고장 발생(확인)일", style='Card.TLabel').grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Label(input_card, text="고장내용", style='Card.TLabel').grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(input_card, text="RM 요청일", style='Card.TLabel').grid(row=1, column=2, sticky='w', padx=5, pady=2)
        ttk.Label(input_card, text="Remark", style='Card.TLabel').grid(row=1, column=3, sticky='w', padx=5, pady=2)
        
        # Variables and Entries
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        self.failure_date_var = tk.StringVar(value=today_str)
        self.failure_date_entry = ttk.Entry(input_card, textvariable=self.failure_date_var, width=14)
        self.failure_date_entry.grid(row=2, column=0, padx=5, pady=5, sticky='ew')
        
        self.details_var = tk.StringVar()
        self.details_entry = ttk.Entry(input_card, textvariable=self.details_var, width=30)
        self.details_entry.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        
        self.rm_request_date_var = tk.StringVar(value=today_str)
        self.rm_request_date_entry = ttk.Entry(input_card, textvariable=self.rm_request_date_var, width=14)
        self.rm_request_date_entry.grid(row=2, column=2, padx=5, pady=5, sticky='ew')
        
        self.remark_var = tk.StringVar()
        self.remark_entry = ttk.Entry(input_card, textvariable=self.remark_var, width=32)
        self.remark_entry.grid(row=2, column=3, padx=5, pady=5, sticky='ew')
        
        # Add Button
        self.add_btn = ttk.Button(input_card, text="ADD RECORD", style='Action.TButton', command=self.add_rm_record)
        self.add_btn.grid(row=2, column=4, padx=10, pady=5, sticky='ns')
        
        # Configure columns stretch
        input_card.columnconfigure(0, weight=1)
        input_card.columnconfigure(1, weight=3)
        input_card.columnconfigure(2, weight=1)
        input_card.columnconfigure(3, weight=3)
        input_card.columnconfigure(4, weight=0)

    def create_list_card(self):
        list_card = ttk.Frame(self.main_frame, style='Card.TFrame', padding=15)
        list_card.pack(fill='both', expand=True)
        
        # Header of List
        list_header = ttk.Frame(list_card, style='Card.TFrame')
        list_header.pack(fill='x', pady=(0, 10))
        ttk.Label(list_header, text="RM Status Table", style='CardHeader.TLabel').pack(side='left')
        
        # Button controls at the bottom of the card first (to guarantee visibility)
        control_frame = ttk.Frame(list_card, style='Card.TFrame')
        control_frame.pack(side='bottom', fill='x', pady=(10, 0))
        
        self.delete_btn = ttk.Button(control_frame, text="❌ DELETE SELECTED", style='TButton', command=self.delete_selected)
        self.delete_btn.pack(side='right', padx=5)
        
        # Table container frame
        table_frame = ttk.Frame(list_card, style='Card.TFrame')
        table_frame.pack(side='top', fill='both', expand=True)
        
        # Treeview (Compact width columns as requested)
        self.columns = ('ID', 'failure_date', 'failure_details', 'rm_request_date', 'elapsed_days', 'remark')
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show='headings', selectmode='browse')
        
        # Set column dimensions - COMPACT as requested
        self.tree.heading('ID', text='ID')
        self.tree.column('ID', width=0, stretch=tk.NO) # Hide ID column
        
        self.tree.heading('failure_date', text='고장 발생(확인)일', command=lambda: self.sort_column('failure_date', False))
        self.tree.column('failure_date', width=120, minwidth=100, anchor='center')
        
        self.tree.heading('failure_details', text='고장내용', command=lambda: self.sort_column('failure_details', False))
        self.tree.column('failure_details', width=280, minwidth=220, anchor='w')
        
        self.tree.heading('rm_request_date', text='RM 요청일', command=lambda: self.sort_column('rm_request_date', False))
        self.tree.column('rm_request_date', width=120, minwidth=100, anchor='center')
        
        self.tree.heading('elapsed_days', text='경과일', command=lambda: self.sort_column('elapsed_days', False))
        self.tree.column('elapsed_days', width=70, minwidth=60, anchor='center')
        
        self.tree.heading('remark', text='Remark', command=lambda: self.sort_column('remark', False))
        self.tree.column('remark', width=320, minwidth=240, anchor='w')
        
        # Scrollbars
        yscrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        xscrollbar = ttk.Scrollbar(table_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set)
        
        # Grid layout for tree and scrollbars in the table frame
        self.tree.grid(row=0, column=0, sticky='nsew')
        yscrollbar.grid(row=0, column=1, sticky='ns')
        xscrollbar.grid(row=1, column=0, sticky='ew')
        
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        
        # Binds
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.tree.bind('<Control-c>', self.copy_selection)
        
        # Tags for premium visual styling (Zebra striping + Elapsed highlighting)
        self.tree.tag_configure('even', background='#ffffff', foreground=COLORS['text'])
        self.tree.tag_configure('odd', background='#f8fafc', foreground=COLORS['text'])
        self.tree.tag_configure('elapsed_high', background='#fde8e8', foreground='#9b1c1c') # soft red
        self.tree.tag_configure('elapsed_medium', background='#fef3c7', foreground='#92400e') # soft orange
        
    def load_data(self):
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        today = datetime.now()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, failure_date, failure_details, rm_request_date, remark FROM rm_list ORDER BY rm_request_date DESC')
            rows = cursor.fetchall()
            
        for idx, row in enumerate(rows):
            rm_id, f_date, details, req_date, remark = row
            
            # Calculate elapsed days dynamically
            elapsed = 0
            try:
                req_dt = datetime.strptime(req_date, '%Y-%m-%d')
                elapsed = (today - req_dt).days
                elapsed_str = f"+{elapsed}" if elapsed >= 0 else str(elapsed)
            except Exception:
                elapsed_str = "-"
                elapsed = 0
                
            # Determine tag based on elapsed days and zebra striping
            if elapsed >= 5:
                tag = 'elapsed_high'
            elif elapsed >= 3:
                tag = 'elapsed_medium'
            else:
                tag = 'even' if idx % 2 == 0 else 'odd'
                
            self.tree.insert('', 'end', values=(
                rm_id,
                f_date,
                details,
                req_date,
                elapsed_str,
                remark
            ), tags=(tag,))
            
    def add_rm_record(self):
        f_date = self.failure_date_var.get().strip()
        details = self.details_var.get().strip()
        req_date = self.rm_request_date_var.get().strip()
        remark = self.remark_var.get().strip()
        
        if not details:
            messagebox.showwarning("입력 오류", "고장내용을 입력해 주세요.")
            return
            
        # Basic date validation
        try:
            datetime.strptime(f_date, '%Y-%m-%d')
            datetime.strptime(req_date, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("날짜 오류", "날짜 형식이 올바르지 않습니다. (YYYY-MM-DD 형식으로 입력하세요.)")
            return
            
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rm_list (failure_date, failure_details, rm_request_date, remark)
                VALUES (?, ?, ?, ?)
            ''', (f_date, details, req_date, remark))
            conn.commit()
            
        # Reset input inputs
        self.details_var.set("")
        self.remark_var.set("")
        
        self.load_data()
        messagebox.showinfo("성공", "RM 항목이 성공적으로 추가되었습니다.")
        
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("선택 오류", "삭제할 항목을 선택해 주세요.")
            return
            
        item = self.tree.item(selected[0])
        rm_id = item['values'][0]
        details = item['values'][2]
        
        confirm = messagebox.askyesno("삭제 확인", f"선택한 RM 항목을 삭제하시겠습니까?\n\n고장내용: {details}")
        if not confirm:
            return
            
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM rm_list WHERE id = ?', (rm_id,))
            conn.commit()
            
        self.load_data()
        messagebox.showinfo("성공", "선택한 항목이 삭제되었습니다.")
        
    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        
        menu = tk.Menu(self, tearoff=0)
        
        if row_id:
            if row_id not in self.tree.selection():
                self.tree.selection_set(row_id)
            values = self.tree.item(row_id)['values']
            
            # Copy cell value
            if col_id:
                col_index = int(col_id.replace('#', '')) - 1
                if 0 <= col_index < len(values):
                    cell_val = str(values[col_index])
                    menu.add_command(
                        label=f"Copy \"{cell_val}\"",
                        command=lambda v=cell_val: self.clipboard_set(v)
                    )
            
            # Copy full row
            menu.add_command(label="Copy Selected Row", command=self.copy_selection)
            menu.add_separator()
            menu.add_command(label="Delete Selected RM", command=self.delete_selected)
            
        menu.tk_popup(event.x_root, event.y_root)
        
    def clipboard_set(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        
    def copy_selection(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        values = item['values']
        # Join values (skipping ID)
        row_str = '\t'.join(str(v) for v in values[1:])
        self.clipboard_set(row_str)

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        # Custom sorting logic
        def sort_key(val):
            try:
                # If elapsed days, sort by integer
                if col == 'elapsed_days':
                    return int(val.replace('+', ''))
                return val
            except ValueError:
                return val
                
        l.sort(key=lambda t: sort_key(t[0]), reverse=reverse)
        
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
            
        # Bind header to toggle reverse sort next time
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))
