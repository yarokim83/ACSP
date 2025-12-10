import tkinter as tk
from ACSP.database import init_database
from ACSP.ui.app import ACSPApp

def main():
    root = tk.Tk()
    
    # Initialize Database
    init_database()
    
    # Start Application
    app = ACSPApp(root)
    
    root.mainloop()

if __name__ == '__main__':
    main()
