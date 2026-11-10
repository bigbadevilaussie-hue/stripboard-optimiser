from tkinter import ttk

class ProjectPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style='Panel.TFrame', padding=10)
        ttk.Label(self, text='BOARD INFO', style='Copper.TLabel').pack(anchor='w', pady=(0, 10))
        self.lbl_board = ttk.Label(self, text='No board loaded', style='TLabel')
        self.lbl_board.pack(anchor='w')

    def update_info(self, project):
        self.lbl_board.configure(text=f'{project.rows}x{project.cols} Stripboard\n{len(project.components)} components')
