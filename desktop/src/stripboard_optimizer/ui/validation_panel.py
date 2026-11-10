from tkinter import ttk
import tkinter as tk

class ValidationPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style='TFrame')
        self.report = tk.Text(self, bg='#ffffff', fg='#1a1a1a', font=('Menlo', 11),
                              bd=0, highlightthickness=1, highlightbackground='#D4A853', padx=8, pady=8)
        self.report.pack(fill='both', expand=True)

    def log(self, msg):
        self.report.insert('end', msg + '\n')
        self.report.see('end')
        
    def log_findings(self, findings):
        for f in findings:
            self.log(f'[{f.severity}] {f.message}')
