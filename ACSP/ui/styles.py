import tkinter as tk
from tkinter import ttk

# Color Palette
COLORS = {
    'primary': '#2c3e50',      # Dark Blue-Gray (Sidebar)
    'secondary': '#34495e',    # Slightly lighter sidebar
    'accent': '#3498db',       # Bright Blue (Buttons, Highlights)
    'accent_hover': '#2980b9',
    'bg': '#ecf0f1',           # Light Gray (Main Background)
    'card_bg': '#ffffff',      # White (Cards)
    'text': '#2c3e50',
    'text_light': '#ecf0f1',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'success': '#27ae60'
}

FONTS = {
    'h1': ('Segoe UI', 20, 'bold'),
    'h2': ('Segoe UI', 16, 'bold'),
    'h3': ('Segoe UI', 12, 'bold'),
    'body': ('Segoe UI', 10),
    'body_b': ('Segoe UI', 10, 'bold'),
    'small': ('Segoe UI', 9)
}

def apply_styles(root):
    style = ttk.Style(root)
    style.theme_use('clam')  # 'clam' offers better customizability than 'vista'
    
    # General Window
    root.configure(bg=COLORS['bg'])
    
    # ---------------------------------------------------------
    # TFrame
    # ---------------------------------------------------------
    style.configure('Main.TFrame', background=COLORS['bg'])
    style.configure('Sidebar.TFrame', background=COLORS['primary'])
    style.configure('Card.TFrame', background=COLORS['card_bg'], relief='flat')
    
    # ---------------------------------------------------------
    # TLabel
    # ---------------------------------------------------------
    style.configure('TLabel', background=COLORS['bg'], foreground=COLORS['text'], font=FONTS['body'])
    
    # Sidebar Labels
    style.configure('Sidebar.TLabel', background=COLORS['primary'], foreground=COLORS['text_light'])
    style.configure('SidebarTitle.TLabel', background=COLORS['primary'], foreground=COLORS['text_light'], font=FONTS['h1'])
    style.configure('SidebarStat.TLabel', background=COLORS['primary'], foreground=COLORS['text_light'], font=FONTS['h3'])
    style.configure('SidebarStatValue.TLabel', background=COLORS['primary'], foreground=COLORS['accent'], font=FONTS['h2'])

    # Card Labels
    style.configure('Card.TLabel', background=COLORS['card_bg'], foreground=COLORS['text'])
    style.configure('CardHeader.TLabel', background=COLORS['card_bg'], foreground=COLORS['text'], font=FONTS['h2'])
    
    # ---------------------------------------------------------
    # TButton
    # ---------------------------------------------------------
    style.configure('TButton', 
                   font=FONTS['body_b'], 
                   padding=6, 
                   borderwidth=0,
                   background=COLORS['accent'], 
                   foreground='white')
    style.map('TButton',
              background=[('active', COLORS['accent_hover']), ('pressed', COLORS['secondary'])],
              foreground=[('active', 'white')])

    # Sidebar Buttons (Simulated with standard buttons for now, customized)
    style.configure('Sidebar.TButton',
                    background=COLORS['primary'],
                    foreground=COLORS['text_light'],
                    borderwidth=0,
                    anchor='w',
                    padding=10)
    style.map('Sidebar.TButton',
              background=[('active', COLORS['secondary'])],
              foreground=[('active', 'white')])
              
    # Action Button
    style.configure('Action.TButton', font=FONTS['h3'], background=COLORS['success'])
    style.map('Action.TButton', background=[('active', '#219150')])

    # ---------------------------------------------------------
    # Treeview
    # ---------------------------------------------------------
    style.configure("Treeview",
                    background="white",
                    foreground=COLORS['text'],
                    rowheight=30,
                    fieldbackground="white",
                    font=FONTS['body'])
    style.configure("Treeview.Heading",
                    background="#bdc3c7",
                    foreground=COLORS['text'],
                    font=FONTS['body_b'],
                    relief="flat")
    style.map("Treeview",
              background=[('selected', COLORS['accent'])],
              foreground=[('selected', 'white')])
              
    # ---------------------------------------------------------
    # Input Widgets
    # ---------------------------------------------------------
    style.configure('TEntry', padding=5)
    style.configure('TCombobox', padding=5)

    return style
