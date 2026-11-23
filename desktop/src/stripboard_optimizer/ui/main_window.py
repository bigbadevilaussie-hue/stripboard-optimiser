import tkinter as tk
from tkinter import ttk, filedialog
import os, zipfile
import time
from datetime import datetime
import json, queue, shutil, subprocess, tempfile, threading
from pathlib import Path
from stripboard_optimizer.ui.project_panel import ProjectPanel
from stripboard_optimizer.ui.validation_panel import ValidationPanel
from stripboard_optimizer.ui.board_viewer import BoardViewer
from stripboard_optimizer.controllers.project_controller import ProjectController
from stripboard_optimizer.filters import split_parts, part_size, def_id_of
from stripboard_optimizer.board_estimator import estimate_board
from stripboard_optimizer.utils.system_info import detect as detect_system
from stripboard_optimizer.solver.probe import run_speed_probe
from stripboard_optimizer.solver.estimator import estimate as estimate_runtime
from stripboard_optimizer.solver.worker import SolveWorker

BG_ROOT      = "#f3f4f6"
BG_TOP_BAR   = "#ffffff"
BG_PANEL     = "#ffffff"
FG_TEXT      = "#374151"
GREEN_BTN    = "#10b981"
RED_BTN      = "#ef4444"
AMBER_BTN    = "#f59e0b"

FONT_SANS = ("Helvetica Neue", 12)
FONT_SANS_BOLD = ("Helvetica Neue", 13, "bold")
FONT_MONO = ("Menlo", 11)

APP_VERSION = "v1.56"

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stripboard Optimiser")
        self.geometry("1360x860")
        self.minsize(1100, 700)
        self.configure(bg=BG_ROOT)
        self.controller = ProjectController()
        self.estimated_tight = (0, 0)
        self.lock_vars = {}
        self.project_path = None
        self.solver = None
        self.solver_q = queue.Queue()
        self.best = None
        self.sys_info = None
        self.probe_result = None
        self.solve_started_at = None
        self.solve_started_monotonic = None
        self.setup_style()
        self.build_ui()

    def setup_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background=BG_ROOT)
        s.configure("TopBar.TFrame", background=BG_TOP_BAR)
        s.configure("Panel.TFrame", background=BG_PANEL, bordercolor="#e5e7eb", relief="solid", borderwidth=1)
        s.configure("TLabel", background=BG_ROOT, foreground=FG_TEXT, font=FONT_SANS)
        s.configure("TopBarBold.TLabel", background=BG_TOP_BAR, foreground=FG_TEXT, font=FONT_SANS_BOLD)
        s.configure("Copper.TLabel", background=BG_PANEL, foreground=FG_TEXT, font=FONT_SANS_BOLD)
        s.configure("Green.TButton", background=GREEN_BTN, foreground="#ffffff", font=FONT_SANS_BOLD, borderwidth=0, padding=(16, 8), lightcolor=GREEN_BTN, darkcolor=GREEN_BTN)
        s.map("Green.TButton", background=[('active', "#059669"), ('pressed', "#059669")])
        s.configure("Red.TButton", background=RED_BTN, foreground="#ffffff", font=FONT_SANS_BOLD, borderwidth=0, padding=(16, 8), lightcolor=RED_BTN, darkcolor=RED_BTN)
        s.map("Red.TButton", background=[('active', "#dc2626"), ('pressed', "#dc2626")])
        s.configure("Amber.TButton", background=AMBER_BTN, foreground="#ffffff", font=FONT_SANS_BOLD, borderwidth=0, padding=(16, 8), lightcolor=AMBER_BTN, darkcolor=AMBER_BTN)
        s.map("Amber.TButton", background=[('active', "#d97706"), ('pressed', "#d97706")])
        s.configure("Reset.TButton", background="#e5e7eb", foreground="#374151", font=FONT_SANS_BOLD, borderwidth=0, padding=(16, 8))

    def build_ui(self):
        self.top = ttk.Frame(self, style="TopBar.TFrame", padding=(16, 12))
        self.top.pack(fill="x")
        ttk.Label(self.top, text="stripboard_optimiser", style="TopBarBold.TLabel").pack(side="left")
        ttk.Label(self.top, text=APP_VERSION, background=BG_TOP_BAR,
                  foreground="#9ca3af", font=("Helvetica Neue", 10)).pack(side="right", padx=(12, 4))
        self.btn_restart = ttk.Button(self.top, text="Restart", style="Reset.TButton", command=self.reset_app)
        self.btn_restart.pack(side="right", padx=(8, 0))
        self.btn_load = ttk.Button(self.top, text="1. Open Project JSON", style="Green.TButton", command=self.load_project)
        self.btn_load.pack(side="left", padx=(24, 8))
        self.btn_net = ttk.Button(self.top, text="2. Load .net File", style="Green.TButton", command=self.load_netlist)
        self.btn_zip = ttk.Button(self.top, text="3. Load KiCAD ZIP", style="Green.TButton", command=self.load_zip)
        self.btn_preflight = ttk.Button(self.top, text="4. Run Preflight", style="Green.TButton", command=self.run_preflight)

        self.btn_mode = ttk.Button(self.top, text="5. Mode Select", style="Amber.TButton", command=self.show_mode_select)
        self.btn_optimise = ttk.Button(self.top, text="6. Optimize", style="Green.TButton", command=self.start_optimisation)
        self.btn_cancel = ttk.Button(self.top, text="Cancel", style="TButton", command=self.show_log)
        self.btn_stop = ttk.Button(self.top, text="Stop", style="Red.TButton", command=self.cancel_solve)
        self.btn_preview = ttk.Button(self.top, text="Preview board", style="Green.TButton", command=self.preview_best)
        self.btn_render_save = ttk.Button(self.top, text="Render JSON...", style="Green.TButton", command=self.render_from_file)
        self.btn_render_save.pack(side="right", padx=(8, 0))

        tk.Frame(self, bg="#e5e7eb", height=1).pack(fill="x")
        # Retain the project panel object for existing project metadata updates,
        # but do not display the redundant left-hand sidebar.
        self.project_panel = ProjectPanel(self)

        self.right_frame = ttk.Frame(self, style="TFrame")
        self.right_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Persistent workflow area and board preview.
        self.content_split = ttk.PanedWindow(self.right_frame, orient="horizontal")
        self.content_split.pack(fill="both", expand=True)
        self.workflow_frame = ttk.Frame(self.content_split, style="TFrame")
        self.preview_frame = ttk.Frame(self.content_split, style="Panel.TFrame", padding=8)
        self.content_split.add(self.workflow_frame, weight=1)
        self.content_split.add(self.preview_frame, weight=1)

        self.stage_var = tk.StringVar(value="PROJECT")
        self.stage_labels = {}
        stage_bar = ttk.Frame(self.workflow_frame, style="TFrame", padding=(4, 0, 4, 10))
        stage_bar.pack(fill="x")
        for stage in ("PROJECT", "BOARD", "OPTIMISE", "PRE-FLIGHT", "RESULTS"):
            label = ttk.Label(stage_bar, text=stage, font=("Helvetica Neue", 10, "bold"),
                              foreground="#9ca3af", background=BG_ROOT, padding=(8, 6))
            label.pack(side="left", padx=(0, 4))
            self.stage_labels[stage] = label
        self._set_stage("PROJECT")
        ttk.Label(self.preview_frame, text="BOARD PREVIEW", style="Copper.TLabel").pack(anchor="w", pady=(0, 8))

        self.log_frame = ttk.Frame(self.workflow_frame, style="Panel.TFrame", padding=1)
        self.validation_panel = ValidationPanel(self.log_frame)
        self.validation_panel.pack(fill="both", expand=True)

        self.board_view_frame = ttk.Frame(self.preview_frame, style="Panel.TFrame")
        self.board_viewer = BoardViewer(self.board_view_frame, on_close=self.show_log)
        self.board_view_frame.pack(fill="both", expand=True)
        self.board_viewer.pack(fill="both", expand=True)
        self.board_viewer.update_image()

        # PANEL 1: MODE SELECT
        self.mode_frame = ttk.Frame(self.workflow_frame, style="Panel.TFrame", padding=24)
        ttk.Label(self.mode_frame, text="Select Optimisation Mode", font=FONT_SANS_BOLD, background=BG_PANEL).pack(pady=(0, 20))
        self.mode_var = tk.StringVar(value="2pass")
        modes = [
            ("manual", "Manual (Expert Mode)", "Control every seed and weight manually."),
            ("full_auto", "Auto (Cross your fingers and pray)", "The solver picks the settings and runs a massive sweep."),
            ("2pass", "2-Pass Tournament (Preferred)", "Pass 1: 1,000 seeds at 15k moves. Pass 2: Audit all qualifiers from 25k to 100k, keep top 10.")
        ]
        for val, label, desc in modes:
            rb = tk.Radiobutton(self.mode_frame, text=label, variable=self.mode_var, value=val,
                                bg=BG_PANEL, fg=FG_TEXT, selectcolor=BG_PANEL,
                                activebackground=BG_PANEL, activeforeground=FG_TEXT,
                                font=FONT_SANS_BOLD, anchor="w", highlightthickness=0, bd=0)
            rb.pack(fill="x", pady=(10, 0))
            tk.Label(self.mode_frame, text=desc, bg=BG_PANEL, fg="#737373", font=FONT_SANS, anchor="w").pack(fill="x", padx=25, pady=(0, 10))

        ttk.Button(self.mode_frame, text="CONFIRM MODE", style="Green.TButton", command=self.confirm_mode).pack(pady=(30, 0), ipadx=20, ipady=10)

        # PANEL 2: QUESTIONS (Auto / 2-Pass)
        self.questions_frame = ttk.Frame(self.workflow_frame, style="Panel.TFrame", padding=24)
        self.canvas = tk.Canvas(self.questions_frame, bg=BG_PANEL, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.questions_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style="Panel.TFrame")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas.find_all()[0], width=e.width))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.q_btn_frame = ttk.Frame(self.questions_frame, style="Panel.TFrame")
        self.q_btn_frame.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(self.q_btn_frame, text="START OPTIMISATION", style="Green.TButton", command=self.start_optimisation).pack(side="right", ipadx=20, ipady=10)

        # PANEL 3: MANUAL SETTINGS
        self.manual_frame = ttk.Frame(self.workflow_frame, style="Panel.TFrame", padding=16)
        ttk.Label(self.manual_frame, text="Manual optimisation settings", font=FONT_SANS_BOLD, background=BG_PANEL).pack(anchor="w", pady=(0, 12))

        board_settings = ttk.LabelFrame(self.manual_frame, text="Board dimensions", padding=10)
        board_settings.pack(fill="x", pady=(0, 10))
        self.manual_rows_var = tk.IntVar(value=24)
        self.manual_cols_var = tk.IntVar(value=56)
        self.manual_lock_rows_var = tk.BooleanVar(value=False)
        self.manual_lock_cols_var = tk.BooleanVar(value=False)
        ttk.Label(board_settings, text="Rows").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Spinbox(board_settings, from_=1, to=500, width=7, textvariable=self.manual_rows_var).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(board_settings, text="Lock rows", variable=self.manual_lock_rows_var).grid(row=0, column=2, sticky="w", padx=(12, 20))
        ttk.Label(board_settings, text="Columns").grid(row=0, column=3, sticky="w", padx=(0, 6))
        ttk.Spinbox(board_settings, from_=1, to=500, width=7, textvariable=self.manual_cols_var).grid(row=0, column=4, sticky="w")
        ttk.Checkbutton(board_settings, text="Lock columns", variable=self.manual_lock_cols_var).grid(row=0, column=5, sticky="w", padx=(12, 0))

        # Tournament-only switches, placed above the scrollable component inventory.
        self.tournament_options_frame = ttk.LabelFrame(self.manual_frame, text="Routing rules", padding=10)
        self.tournament_drilled_var = tk.BooleanVar(value=True)
        self.tournament_stack_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.tournament_options_frame, text="Drilled cuts only (OFF = allow knife cuts)", variable=self.tournament_drilled_var).pack(anchor="w")
        ttk.Checkbutton(self.tournament_options_frame, text="Allow stacked wires (OFF = no stacking)", variable=self.tournament_stack_var).pack(anchor="w", pady=(5, 0))

        self.solver_settings_frame = ttk.LabelFrame(self.manual_frame, text="Routing and solver", padding=10)
        self.solver_settings_frame.pack(fill="x", pady=(0, 10))
        solver_settings = self.solver_settings_frame
        self.manual_cut_var = tk.StringVar(value="knife")
        ttk.Label(solver_settings, text="Cuts").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(solver_settings, text="Drilled only", variable=self.manual_cut_var, value="drilled").grid(row=0, column=1, sticky="w", padx=(8, 12))
        ttk.Radiobutton(solver_settings, text="Allow knife cuts", variable=self.manual_cut_var, value="knife").grid(row=0, column=2, sticky="w")
        self.manual_routing_preference_var = tk.StringVar(value="wires")
        ttk.Label(solver_settings, text="Routing priority").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Radiobutton(solver_settings, text="Fewer wires", variable=self.manual_routing_preference_var, value="wires").grid(row=2, column=1, sticky="w", pady=(8, 0))
        ttk.Radiobutton(solver_settings, text="Fewer cuts (disabled)", variable=self.manual_routing_preference_var, value="cuts", state="disabled").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.manual_no_stack_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(solver_settings, text="No stacked wires", variable=self.manual_no_stack_var).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        tk.Label(solver_settings, text="Rotation and diagonal routing are solver-managed; this solver build has no separate on/off switches for them.", bg=BG_PANEL, fg="#737373", font=("Helvetica Neue", 10), anchor="w").grid(row=1, column=3, columnspan=3, sticky="w", padx=(8, 0), pady=(6, 0))
        self.manual_seeds_var = tk.IntVar(value=12)
        self.manual_seed_base_var = tk.IntVar(value=0)
        self.manual_effort_var = tk.DoubleVar(value=1.0)
        self.manual_threads_var = tk.IntVar(value=max(1, min(4, (os.cpu_count() or 2) - 1)))
        ttk.Label(solver_settings, text="Seeds").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(solver_settings, from_=1, to=256, width=7, textvariable=self.manual_seeds_var).grid(row=3, column=1, sticky="w", pady=(8, 0))
        ttk.Label(solver_settings, text="Starting seed").grid(row=3, column=2, sticky="w", padx=(12, 6), pady=(8, 0))
        ttk.Spinbox(solver_settings, from_=0, to=2147483647, width=10, textvariable=self.manual_seed_base_var).grid(row=3, column=3, sticky="w", pady=(8, 0))
        ttk.Label(solver_settings, text="Effort").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(solver_settings, from_=0.1, to=10.0, increment=0.1, width=7, textvariable=self.manual_effort_var).grid(row=4, column=1, sticky="w", pady=(8, 0))
        ttk.Label(solver_settings, text="Threads").grid(row=4, column=2, sticky="w", padx=(12, 6), pady=(8, 0))
        ttk.Spinbox(solver_settings, from_=1, to=max(1, os.cpu_count() or 1), width=7, textvariable=self.manual_threads_var).grid(row=4, column=3, sticky="w", pady=(8, 0))

        parts_box = ttk.LabelFrame(self.manual_frame, text="Component placement locks", padding=8)
        parts_box.pack(fill="both", expand=True, pady=(0, 10))
        tk.Label(parts_box, text="Tick Lock to keep a component at its current position and rotation. Unticked parts may be repositioned and rotated by the solver.", bg=BG_PANEL, fg="#737373", font=FONT_SANS, anchor="w").pack(fill="x", pady=(0, 6))
        parts_canvas = tk.Canvas(parts_box, bg=BG_PANEL, highlightthickness=0, height=190)
        parts_scroll = ttk.Scrollbar(parts_box, orient="vertical", command=parts_canvas.yview)
        self.manual_parts_frame = ttk.Frame(parts_canvas, style="Panel.TFrame")
        self.manual_parts_frame.bind("<Configure>", lambda e: parts_canvas.configure(scrollregion=parts_canvas.bbox("all")))
        parts_canvas.create_window((0, 0), window=self.manual_parts_frame, anchor="nw")
        parts_canvas.configure(yscrollcommand=parts_scroll.set)
        parts_canvas.pack(side="left", fill="both", expand=True)
        parts_scroll.pack(side="right", fill="y")
        self.manual_part_vars = {}
        self.manual_locks_confirmed_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.manual_frame, text="I have reviewed the component list and confirmed every locked placement.", variable=self.manual_locks_confirmed_var).pack(anchor="w", pady=(0, 8))
        ttk.Button(self.manual_frame, text="START OPTIMISATION", style="Green.TButton", command=self.start_optimisation).pack(anchor="e", ipadx=20, ipady=8)

        self.log_frame.pack(fill="both", expand=True)
        self.log("Ready. Open a project JSON to begin.")
        self.after(200, self._poll_solver)

    def _set_stage(self, stage):
        """Update the persistent workflow progress indicator."""
        self.stage_var.set(stage)
        order = ("PROJECT", "BOARD", "OPTIMISE", "PRE-FLIGHT", "RESULTS")
        active = order.index(stage) if stage in order else 0
        for index, name in enumerate(order):
            colour = "#047857" if index < active else ("#111827" if index == active else "#9ca3af")
            self.stage_labels[name].configure(foreground=colour)

    def log(self, msg):
        self.validation_panel.log(msg)

    def reset_app(self):
        self.controller = ProjectController()
        self.project_path = None
        self.best = None
        self._set_stage("PROJECT")
        self.board_viewer.clear()
        self.validation_panel.report.delete(1.0, tk.END)
        self.log("Ready. Open a project JSON to begin.")
        for frame in [self.log_frame, self.mode_frame, self.questions_frame, self.manual_frame]:
            frame.pack_forget()
        self.log_frame.pack(fill="both", expand=True)
        for btn in [self.btn_net, self.btn_zip, self.btn_preflight, self.btn_mode, self.btn_optimise, self.btn_cancel, self.btn_stop, self.btn_preview, self.btn_render_save]:
            btn.pack_forget()
        self.btn_load.pack(side="left", padx=(24, 8))
        self.project_panel.lbl_board.configure(text="No board loaded")

    def load_project(self):
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if not path: return
        try:
            project = self.controller.load_project(path)
            self.project_path = path
            self.btn_load.pack_forget()
            self.project_panel.update_info(project)
            self.log(f"\n--- 1. PROJECT JSON: {os.path.basename(path)} ---")
            self.log(f"[BOARD] {project.rows} Rows x {project.cols} Cols ({project.rows * project.cols} total holes)")
            self.log(f"[INFO] JSON Pin Assignments: {project.pin_count}")
            comps = project.components
            on_board_parts, off_board_parts = split_parts(comps)
            self.log(f"[INFO] OFF-BOARD PARTS: {len(off_board_parts)}")
            self.log(f"[INFO] ON-BOARD PARTS: {len(on_board_parts)}")
            missing = project.missing_footprints
            if missing:
                self.log(f"[WARN] {len(missing)} footprints are missing. Waiting to see the Pretty KiCad ZIP.")
            self.btn_net.pack(side="left", padx=8)
        except Exception as e:
            self.log(f"\n[ERROR] Could not load JSON: {e}")

    def load_netlist(self):
        path = filedialog.askopenfilename(filetypes=[("Netlist", "*.net")])
        if not path: return
        try:
            net_nodes = self.controller.load_netlist(path)
            self.btn_net.configure(style="Green.TButton")
            self.btn_net.pack_forget()
            self.log(f"\n--- 2. NETLIST: {os.path.basename(path)} ---")
            self.log(f"[INFO] Netlist Pins: {net_nodes}")
            self.log("[OK] JSON and Netlist pin counts match.")
            self.btn_zip.pack(side="left", padx=8)
        except ValueError as e:
            self.log(f"\n[FAIL] {e}")
            self.btn_net.configure(style="Red.TButton")

    def load_zip(self):
        path = filedialog.askopenfilename(filetypes=[("KiCad Footprints", "*.zip")])
        if not path: return
        self.controller.load_zip(path)
        self._set_stage("BOARD")
        self.btn_zip.pack_forget()
        self.log(f"\n--- 3. KICAD FOOTPRINTS: {os.path.basename(path)} ---")
        for name, (pads, w, h) in self.controller.zip_footprints.items():
            self.log(f"  [FILE] {name} ({pads} pads, {w}x{h} = {w*h} holes)")
        project = self.controller.project
        on_board_parts, _ = split_parts(project.components)
        self.log("\n--- MERGED ON-BOARD INVENTORY ---")
        total_holes = 0
        missing_custom_count = 0
        zip_names_lower = [n.lower() for n in self.controller.zip_footprints.keys()]
        for c in on_board_parts:
            label = c.get("label") or c.get("name") or "Unknown"
            c_def = project.component_defs.get(def_id_of(c), {})
            c_name = c_def.get("name", label)
            w, h, src = part_size(c, project.component_defs)
            holes = w * h
            total_holes += holes
            is_custom = src == "FALLBACK" or "SuperMini" in c_name or "MP1584" in c_name or "GPS" in c_name
            zip_match = False
            if is_custom:
                for zip_name in zip_names_lower:
                    clean_cname = c_name.lower().replace(" ", "").replace("-", "").replace("_", "")
                    clean_zip = zip_name.replace(" ", "").replace("-", "").replace("_", "")
                    if clean_cname in clean_zip or clean_zip in clean_cname:
                        zip_match = True
                        break
                if not zip_match:
                    missing_custom_count += 1
            status = "[OK]" if (not is_custom or zip_match) else "[MISSING]"
            self.log(f"  {status} {label:<15} | {c_name:<25} | {w}x{h} = {holes} holes")
        board_holes = project.rows * project.cols
        self.log(f"\n[INFO] --- FINAL BOARD SUMMARY ---")
        self.log(f"[INFO] Total On-Board Parts: {len(on_board_parts)}")
        self.log(f"[INFO] Estimated Total Holes Needed: {total_holes}")
        self.log(f"[INFO] Board Total Holes: {board_holes}")
        if missing_custom_count > 0:
            self.log(f"[WARN] {missing_custom_count} custom parts have no matching footprint in the ZIP.")
        if total_holes > board_holes:
            self.log(f"[WARN] Board seems too small! Parts need {total_holes} holes, board is {board_holes}.")
        else:
            self.log(f"[OK] Board size is reasonable for {total_holes} holes.")
        est = estimate_board(project.components, project.component_defs)
        self.estimated_tight = est['tight']
        self.log(f"\n[ESTIMATE] Tight fit: {est['tight'][0]}x{est['tight'][1]} ({est['tight'][0]*est['tight'][1]} holes)")
        self.btn_preflight.pack(side="left", padx=8)

    def run_preflight(self):
        self._set_stage("PRE-FLIGHT")
        self.log("\n--- 4. PREFLIGHT ---")
        findings = self.controller.run_preflight()
        self.validation_panel.log_findings(findings)
        has_errors = any(f.severity == "ERROR" for f in findings)
        if not has_errors:
            try:
                merged_path = Path(self.project_path).parent / (Path(self.project_path).stem + "_merged.json")
                merged_path.write_text(json.dumps(self.controller.project.raw_data, indent=2))
                self.log(f"[MERGE] Saved updated project to {merged_path}")
            except Exception as exc:
                self.log(f"[MERGE ERROR] {exc}")
            self.btn_preflight.pack_forget()
            self.btn_mode.pack(side="left", padx=8)
            
            # --- INJECT MISSING BUILT-IN DEFS ---
            try:
                raw = self.controller.project.raw_data
                defs = raw.setdefault("componentDefs", [])
                existing = {d["id"] for d in defs}
                
                builtins = [
                    {"id":"def-connector-2","name":"2-Pin Connector","width":2,"height":1,"pins":[{"id":"1","name":"1","offsetRow":0,"offsetCol":0},{"id":"2","name":"2","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-switch","name":"Kill Switch","width":3,"height":2,"pins":[{"id":"1","name":"1","offsetRow":0,"offsetCol":0},{"id":"2","name":"2","offsetRow":0,"offsetCol":2}]},
                    {"id":"def-fuse","name":"Fuse","width":2,"height":1,"pins":[{"id":"1","name":"1","offsetRow":0,"offsetCol":0},{"id":"2","name":"2","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-diode","name":"Diode","width":2,"height":1,"pins":[{"id":"a","name":"A","offsetRow":0,"offsetCol":0},{"id":"k","name":"K","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-cap-polarized","name":"Polarized Capacitor","width":2,"height":1,"pins":[{"id":"+","name":"+","offsetRow":0,"offsetCol":0},{"id":"-","name":"-","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-capacitor","name":"Capacitor","width":2,"height":1,"pins":[{"id":"1","name":"1","offsetRow":0,"offsetCol":0},{"id":"2","name":"2","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-resistor","name":"Resistor","width":2,"height":1,"pins":[{"id":"1","name":"1","offsetRow":0,"offsetCol":0},{"id":"2","name":"2","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-inductor","name":"Inductor","width":2,"height":1,"pins":[{"id":"1","name":"1","offsetRow":0,"offsetCol":0},{"id":"2","name":"2","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-npn","name":"NPN Transistor","width":2,"height":2,"pins":[{"id":"b","name":"B","offsetRow":0,"offsetCol":0},{"id":"c","name":"C","offsetRow":1,"offsetCol":0},{"id":"e","name":"E","offsetRow":1,"offsetCol":1}]},
                    {"id":"def-pmos","name":"P-Channel MOSFET","width":2,"height":2,"pins":[{"id":"g","name":"G","offsetRow":0,"offsetCol":0},{"id":"d","name":"D","offsetRow":1,"offsetCol":0},{"id":"s","name":"S","offsetRow":1,"offsetCol":1}]},
                    {"id":"def-zener","name":"Zener Diode","width":2,"height":1,"pins":[{"id":"a","name":"A","offsetRow":0,"offsetCol":0},{"id":"k","name":"K","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-led","name":"LED","width":2,"height":1,"pins":[{"id":"a","name":"A","offsetRow":0,"offsetCol":0},{"id":"k","name":"K","offsetRow":0,"offsetCol":1}]},
                    {"id":"def-pushbutton","name":"Pushbutton","width":2,"height":2,"pins":[{"id":"1","name":"1","offsetRow":0,"offsetCol":0},{"id":"2","name":"2","offsetRow":0,"offsetCol":1},{"id":"3","name":"3","offsetRow":1,"offsetCol":0},{"id":"4","name":"4","offsetRow":1,"offsetCol":1}]}
                ]
                added = 0
                for b in builtins:
                    if b["id"] not in existing:
                        defs.append(b)
                        existing.add(b["id"])
                        added += 1
                if added > 0:
                    self.log(f"[MERGE] Injected {added} built-in definitions into raw_data.")
                    # We do NOT need to save it to disk, start_optimisation uses raw_data directly.
            except Exception as e:
                self.log(f"[MERGE ERROR] Could not inject built-ins: {e}")
            # -----------------------------------
            
            if self.project_path:
                self._render_project_preview(self.project_path)

    def show_mode_select(self):
        self._set_stage("OPTIMISE")
        self.log_frame.pack_forget()
        self.mode_frame.pack(fill="both", expand=True)
        self.btn_mode.pack_forget()
        self.btn_cancel.pack(side="left", padx=8)
        self._start_system_measurement()

    def _start_system_measurement(self):
        if not self.controller.project or not self.project_path:
            return
        sys_info = detect_system()
        self.sys_info = sys_info
        cores = sys_info.physical_cores or sys_info.logical_cores or 1
        model = sys_info.cpu_model or "unknown CPU"
        ram = f"{sys_info.total_ram_gb:.0f} GB" if sys_info.total_ram_gb else "RAM unknown"
        pass

        def worker():
            result = run_speed_probe(self.project_path, decodes=10)
            self.after(0, lambda: self._on_probe_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_probe_result(self, result):
        self.probe_result = result
        if not result.ok or result.ms_per_decode is None:
            pass
            return
        threads = self.sys_info.recommended_threads if self.sys_info else 4
        pins = self.controller.project.pin_count if self.controller.project else 0
        est = estimate_runtime(result, moves_total=min(1_280_000, max(5_000, 16_000 * max(0, pins - 13))), threads=threads)
        low, high = est.seconds_low, est.seconds_high
        if high >= 60:
            est_text = f"Runtime per seed: ~{low/60:.1f}–{high/60:.1f} min"
        else:
            est_text = f"Runtime per seed: ~{low:.0f}–{high:.0f} s"
        pass

    def confirm_mode(self):
        self._set_stage("OPTIMISE")
        mode = self.mode_var.get()
        self.log(f"\n--- 5. MODE SELECT ---")
        self.log(f"[INFO] User selected: {mode.upper()}")
        self.mode_frame.pack_forget()
        if mode == "manual":
            self._build_manual_inventory()
            for widget in self.manual_frame.winfo_children():
                if isinstance(widget, ttk.Label) and widget.cget("text") == "2-Pass Tournament settings":
                    widget.configure(text="Manual optimisation settings")
            # Restore expert controls; hide the tournament-only switches.
            self.tournament_options_frame.pack_forget()
            self.solver_settings_frame.pack(fill="x", pady=(0, 10), after=self.manual_frame.winfo_children()[1])
            self.manual_frame.pack(fill="both", expand=True)
        else:
            self.show_questions()

    def _build_manual_inventory(self):
        """Show every project component and its current placement/rotation."""
        self.manual_locks_confirmed_var.set(False)
        for widget in self.manual_parts_frame.winfo_children():
            widget.destroy()
        self.manual_part_vars = {}
        project = self.controller.project
        self.manual_rows_var.set(project.rows)
        self.manual_cols_var.set(project.cols)
        self.manual_lock_rows_var.set(bool(project.locked_rows))
        self.manual_lock_cols_var.set(bool(project.locked_cols))
        for index, component in enumerate(project.components):
            label = component.get("label") or component.get("name") or component.get("id") or f"Component {index + 1}"
            component_id = component.get("id")
            pos = component.get("boardPos")
            if isinstance(pos, dict):
                row_number = pos.get("row")
                col_number = pos.get("col")
                row_text = row_number + 1 if isinstance(row_number, int) else "?"
                col_text = col_number + 1 if isinstance(col_number, int) else "?"
                location = f"R{row_text} C{col_text}"
            else:
                location = "not placed"
            rotation = component.get("rotation", 0)
            excluded = bool(component.get("boardExcluded"))
            status = "excluded" if excluded else f"{location} · {rotation}°"
            var = tk.BooleanVar(value=bool(component.get("locked")))
            self.manual_part_vars[component_id] = var
            row = ttk.Frame(self.manual_parts_frame, style="Panel.TFrame")
            row.pack(fill="x", pady=1)
            check = ttk.Checkbutton(row, text=f"{label}  [{status}]", variable=var)
            check.pack(side="left", anchor="w")
            if not pos or excluded:
                check.configure(state="disabled")

    def show_questions(self):
        # We reuse the manual_frame UI entirely, since it has the exact layout we want.
        # It will just populate the widgets and display them.
        self._build_manual_inventory()
        
        # Change the label to say 2-Pass
        for widget in self.manual_frame.winfo_children():
            if isinstance(widget, ttk.Label) and "Manual optimisation settings" in widget.cget("text"):
                widget.configure(text="2-Pass Tournament settings")
        
        # Keep tournament-specific routing controls visible without exposing manual seed fields.
        self.solver_settings_frame.pack_forget()
        self.tournament_options_frame.pack(fill="x", pady=(0, 10), after=self.manual_frame.winfo_children()[1])
        
        self.manual_frame.pack(fill="both", expand=True)
    def start_optimisation(self):
        mode = self.mode_var.get()
        project = self.controller.project
        drilled = False
        no_wire_stacking = False
        routing_preference = "wires"
        parallel = None
        tournament_candidates = 1000
        tournament_finalists = 10000

        if mode == "manual":
            self._set_stage("PRE-FLIGHT")
            if not self.manual_locks_confirmed_var.get():
                self.log("[BLOCKED] Review the component list and confirm the locked placements before starting.")
                return
            try:
                rows = int(self.manual_rows_var.get())
                cols = int(self.manual_cols_var.get())
                seeds = int(self.manual_seeds_var.get())
                seed_base = int(self.manual_seed_base_var.get())
                effort = float(self.manual_effort_var.get())
                parallel = int(self.manual_threads_var.get())
            except (ValueError, tk.TclError):
                self.log("[ERROR] Manual settings must contain valid numbers.")
                return
            if min(rows, cols, seeds, parallel) < 1 or rows > 500 or cols > 500 or seeds > 256 or seed_base < 0 or parallel > (os.cpu_count() or 1) or not (0.1 <= effort <= 10.0):
                self.log("[ERROR] Rows, columns, seeds and threads must be positive; effort must be 0.1–10.0.")
                return

            try:
                raw = json.loads(json.dumps(self.controller.project.raw_data))
                board = raw.setdefault("board", {})
                board["rows"], board["cols"] = rows, cols
                board["lockedRows"] = bool(self.manual_lock_rows_var.get())
                board["lockedCols"] = bool(self.manual_lock_cols_var.get())
                drilled = self.manual_cut_var.get() == "drilled"
                no_wire_stacking = bool(self.manual_no_stack_var.get())
                routing_preference = self.manual_routing_preference_var.get()
                for component in raw.get("components", []):
                    component_id = component.get("id")
                    if component_id in self.manual_part_vars:
                        locked = bool(self.manual_part_vars[component_id].get())
                        if locked and (not component.get("boardPos") or component.get("boardExcluded")):
                            self.log(f"[BLOCKED] {component.get('label') or component.get('name') or component_id} is marked locked but has no placeable board position.")
                            return
                        component["locked"] = locked
                job = Path(tempfile.mkdtemp(prefix="sbjob_")) / "project.json"
                job.write_text(json.dumps(raw))
            except Exception as exc:
                self.log(f"[ERROR] Could not prepare manual solver input: {exc}")
                return

            self.log("\n--- MANUAL SETTINGS CONFIRMED ---")
            self.log(f"[INFO] Board: {rows}x{cols} | lock rows={self.manual_lock_rows_var.get()} | lock columns={self.manual_lock_cols_var.get()}")
            self.log(f"[INFO] Solver constraints: drilled cuts {'ON' if drilled else 'OFF'} | wire stacking {'BLOCKED' if no_wire_stacking else 'ALLOWED'}")
            self.log(f"[INFO] Seeds: {seeds} starting at {seed_base} | effort={effort:g} | threads={parallel}")
            self.log("[INFO] Effort 1.0 is the normal search depth; higher values increase moves per seed.")
            if self.probe_result and self.probe_result.ok and self.probe_result.ms_per_decode is not None:
                pins = project.pin_count if project else 0
                moves_per_seed = min(1_280_000, max(5_000, 16_000 * max(0, pins - 13)))
                per_seed = estimate_runtime(self.probe_result, moves_total=moves_per_seed, threads=1)
                batches = (seeds + parallel - 1) // parallel
                scale = batches * effort
                low, high = per_seed.seconds_low * scale, per_seed.seconds_high * scale
                point = per_seed.seconds_point * scale
                def fmt_time(seconds):
                    seconds = int(round(seconds))
                    return f"{seconds // 60}m {seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s"
                self.log(
                    f"[TIME] Estimated runtime {fmt_time(low)}–{fmt_time(high)} "
                    f"(midpoint {fmt_time(point)}; {batches} batches × up to {parallel} seeds)."
                )
                self.log(
                    f"[TIME] Based on empirical throughput calibration, "
                    f"{moves_per_seed:,} estimated moves/seed and effort {effort:g}; actual routing/locks may vary."
                )
            else:
                self.log("[TIME] Runtime estimate unavailable: speed probe has not completed or failed.")
            for component in raw.get("components", []):
                if component.get("locked") is True:
                    pos = component.get("boardPos") or {}
                    self.log(f"[LOCKED] {component.get('label') or component.get('name') or component.get('id')} · id={component.get('id')} · row={pos.get('row')} col={pos.get('col')} rotation={component.get('rotation', 0)}°")
        else:
            self._set_stage("PRE-FLIGHT")
            if not self.manual_locks_confirmed_var.get():
                self.log("[BLOCKED] Review the component list and confirm the locked placements before starting.")
                return
            try:
                rows = int(self.manual_rows_var.get())
                cols = int(self.manual_cols_var.get())
            except (ValueError, tk.TclError):
                self.log("[ERROR] Board settings must contain valid numbers.")
                return
                
            drilled = bool(self.tournament_drilled_var.get())
            no_wire_stacking = not bool(self.tournament_stack_var.get())
            self.log("--- 5. PLACEMENT STRATEGY ---")
            self.log(f"[INFO] Board dimensions set to {rows}x{cols} (Lock Rows: {self.manual_lock_rows_var.get()}, Lock Cols: {self.manual_lock_cols_var.get()})")
            
            try:
                raw = json.loads(Path(self.project_path).read_text())
                board = raw.setdefault("board", {})
                board["rows"], board["cols"] = rows, cols
                board["lockedRows"] = bool(self.manual_lock_rows_var.get())
                board["lockedCols"] = bool(self.manual_lock_cols_var.get())
                
                for component in raw.get("components", []):
                    component_id = component.get("id")
                    if component_id in self.manual_part_vars:
                        locked = bool(self.manual_part_vars[component_id].get())
                        if locked and (not component.get("boardPos") or component.get("boardExcluded")):
                            self.log(f"[BLOCKED] {component.get('label') or component.get('name') or component_id} is marked locked but has no placeable board position.")
                            return
                        component["locked"] = locked
                job = Path(tempfile.mkdtemp(prefix="sbjob_")) / "project.json"
                job.write_text(json.dumps(raw))
            except Exception as exc:
                self.log(f"[ERROR] Could not prepare the solver input: {exc}")
                return

        self.board_viewer.select_schematic()
        self.questions_frame.pack_forget()
        self.manual_frame.pack_forget()
        self.log_frame.pack(fill="both", expand=True)
        self.log(f"\n[OPTIMISE] Starting mode: {mode.upper()}")
        if mode == "2pass":
            self.log("[TOURNAMENT] Pass 1: 1,000 seeds × 15,000 moves. Pass 2: Audit all qualifiers at 25k–100k in 5k steps; save top 10 overall.")
            self.log("[TOURNAMENT] Finalists are re-run strictly (no diagonals) from the original project JSON.")
        self.log(f"[SOLVER] Native=ON | drilled cuts={'ON' if drilled else 'OFF'} | wire stacking={'BLOCKED' if no_wire_stacking else 'ALLOWED'} | routing priority={routing_preference}")
        self.log("[SOLVE] Each seed is an independent starting arrangement; the best fully valid result wins.")
        self.best = None
        self.btn_preview.pack_forget()
        self.btn_cancel.pack_forget()
        self.btn_stop.pack(side="left", padx=8)
        self.solver = SolveWorker(
            str(job), mode, self.solver_q,
            parallel=parallel, native=True, drilled=drilled,
            no_wire_stacking=no_wire_stacking,
            routing_preference=routing_preference,
            manual_seeds=seeds if mode == "manual" else None,
            manual_seed_base=seed_base if mode == "manual" else 0,
            manual_effort=effort if mode == "manual" else None,
            tournament_candidates=tournament_candidates,
            tournament_finalists=tournament_finalists,
            output_dir=(
                Path(self.project_path).with_name(Path(self.project_path).stem + "_work")
                if mode == "2pass" else None
            ),
        )
        self.solve_started_at = datetime.now().astimezone()
        self.solve_started_monotonic = time.monotonic()
        self.log(f"[TIME] Started: {self.solve_started_at.strftime('%Y-%m-%d %H:%M:%S %Z (%z)')}")
        self.solver.start()

    def cancel_solve(self):
        if self.solver: self.solver.cancel()
        self.log("[SOLVE] Stopping...")

    def _poll_solver(self):
        try:
            while True:
                m = self.solver_q.get_nowait()
                if m[0] == "log":
                    self.log(m[1])
                elif m[0] == "candidate":
                    # Round standings are printed once, after all contestants finish.
                    pass
                elif m[0] == "round_results":
                    _, stage, total, valid_count, standings = m
                    self.log(f"🏁 Round {stage}: {valid_count}/{total} valid")
                    if not standings:
                        self.log("⚠️ No valid boards")
                    else:
                        self.log("🏆 Top 5:")
                        for item in standings[:5]:
                            medal = ("🥇", "🥈", "🥉")[item["rank"] - 1] if item["rank"] <= 3 else " "
                            self.log(
                                f"  {medal} {item['name']} · {item['wires']}W / "
                                f"{item['cuts']}C · {item['points']} pts"
                            )
                        if stage == 1:
                            qualifiers = ", ".join(x["name"] for x in standings[:self.solver.tournament_finalists])
                            self.log(f"➡️ Finalists: {qualifiers}")
                elif m[0] == "rendered":
                    _, top_png, copper_png, schematic_png = m
                    self.board_viewer.load(top_png, copper_png, schematic_png)
                    self._set_stage("RESULTS")
                elif m[0] == "done":
                    _, best, cancelled = m
                    stopped_at = datetime.now().astimezone()
                    elapsed = (time.monotonic() - self.solve_started_monotonic
                               if self.solve_started_monotonic is not None else 0.0)
                    hours, remainder = divmod(int(round(elapsed)), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    self.log(f"[TIME] Stopped: {stopped_at.strftime('%Y-%m-%d %H:%M:%S %Z (%z)')}")
                    self.log(f"[TIME] Actual runtime: {hours:02d}:{minutes:02d}:{seconds:02d}")
                    self.solve_started_at = None
                    self.solve_started_monotonic = None
                    self.btn_stop.pack_forget()
                    self.btn_cancel.pack_forget()
                    if cancelled:
                        self.log("[SOLVE] Stopped.")
                    elif best:
                        self._set_stage("RESULTS")
                        s, path, seed, contestant_name = best
                        if self.solver and self.solver.mode == "2pass":
                            out = Path(path)
                        else:
                            out = Path(self.project_path).with_name(Path(self.project_path).stem + "_solved.json")
                            out.write_text(Path(path).read_text())
                        self.best = (s, str(out))
                        winner = f"{contestant_name} (seed {seed})" if contestant_name else f"seed {seed}"
                        self.log(f"\n🥇 FINAL RESULT: {winner} · {s['rows']}×{s['cols']} · "
                                 f"{s['wires']}W / {s['cuts']}C · "
                                 f"${float(s.get('price', s.get('rate', 0))):,.2f} · VALID")
                        self.log(f"[BEST] Saved to {out}")
                        if self.solver and self.solver.mode == "2pass":
                            self.log("[BEST] Winner is saved in the retained finalist JSON files.")
                        self.btn_preview.pack(side="left", padx=8)
                        self.log("[PREVIEW] Automatically rendering the best valid solution...")
                        self.preview_best()
                    else:
                        self.log("[SOLVE] No valid board found.")
        except queue.Empty:
            pass
        self.after(200, self._poll_solver)

    def preview_best(self):
        if not self.best: return
        path = self.best[1]
        def job():
            try:
                tmp = Path(tempfile.mkdtemp(prefix="sbpreview_"))
                cli = Path(__file__).parent.parent / "resources" / "standalone-renderer" / "standalone-renderer" / "cli.js"
                if not cli.exists():
                    self.solver_q.put(("log", f"[ERROR] Standalone renderer not found at {cli}"))
                    return
                node = shutil.which("node") or "/usr/local/bin/node"
                r = subprocess.run([node, str(cli), path, "--output", str(tmp)], capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    self.solver_q.put(("log", f"[ERROR] Renderer failed: {(r.stderr or r.stdout).strip()}"))
                    return
                top_svg = tmp / "board-top.svg"
                copper_svg = tmp / "board-copper.svg"
                top_png = tmp / "place.png"
                copper_png = tmp / "cut.png"
                for src, dst in [(top_svg, top_png), (copper_svg, copper_png)]:
                    if not src.exists():
                        self.solver_q.put(("log", f"[ERROR] Renderer did not write {src.name}"))
                        return
                    subprocess.run(["rsvg-convert", "-o", str(dst), str(src)], check=True, timeout=60)
                self.solver_q.put(("rendered", str(top_png), str(copper_png), None))
                self.solver_q.put(("log", f"[PREVIEW] Board preview updated from {Path(path).name}."))
            except subprocess.TimeoutExpired:
                self.solver_q.put(("log", "[ERROR] Preview timed out"))
            except Exception as e:
                self.solver_q.put(("log", f"[ERROR] Preview failed: {e}"))
        threading.Thread(target=job, daemon=True).start()

    def _render_project_preview(self, path):
        """Render all three views of the loaded project into the docked preview."""
        self.log("[PREVIEW] Rendering Front, Back and Schematic...")
        def job():
            try:
                tmp = Path(tempfile.mkdtemp(prefix="sbpreflight_"))
                cli = Path(__file__).parent.parent / "resources" / "standalone-renderer" / "standalone-renderer" / "cli.js"
                schematic_cli = Path(__file__).parent.parent / "resources" / "standalone-renderer" / "standalone-renderer" / "schematic" / "cli.js"
                if not cli.exists() or not schematic_cli.exists():
                    missing = cli if not cli.exists() else schematic_cli
                    self.solver_q.put(("log", f"[ERROR] Renderer not found at {missing}"))
                    return
                node = shutil.which("node") or "/usr/local/bin/node"
                r = subprocess.run([node, str(cli), path, "--output", str(tmp)],
                                   capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    self.solver_q.put(("log", f"[ERROR] Board renderer failed: {(r.stderr or r.stdout).strip()}"))
                    return
                schematic_svg = tmp / "schematic.svg"
                rs = subprocess.run([node, str(schematic_cli), path, "--output", str(tmp)],
                                    capture_output=True, text=True, timeout=120)
                if rs.returncode != 0 or not schematic_svg.exists():
                    self.solver_q.put(("log", f"[ERROR] Schematic renderer failed: {(rs.stderr or rs.stdout).strip()[:300]}"))
                    return
                top_png, copper_png, schematic_png = tmp / "front.png", tmp / "back.png", tmp / "schematic.png"
                for src, dst in ((tmp / "board-top.svg", top_png),
                                 (tmp / "board-copper.svg", copper_png),
                                 (schematic_svg, schematic_png)):
                    if not src.exists():
                        raise FileNotFoundError(f"Renderer did not write {src.name}")
                    subprocess.run(["rsvg-convert", "-w", "2400", "-b", "white",
                                    "-o", str(dst), str(src)], check=True, timeout=60)
                self.solver_q.put(("rendered", str(top_png), str(copper_png), str(schematic_png)))
                self.solver_q.put(("log", "[PREVIEW] Front, Back and Schematic ready. Use the preview controls to switch views."))
            except subprocess.TimeoutExpired:
                self.solver_q.put(("log", "[ERROR] Pre-flight preview rendering timed out."))
            except Exception as exc:
                self.solver_q.put(("log", f"[ERROR] Pre-flight preview failed: {exc}"))
        threading.Thread(target=job, daemon=True).start()

    def render_from_file(self):
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if not path: return
        self.log(f"\n[RENDER] {os.path.basename(path)}")
        def job():
            try:
                out_dir = Path(path).parent
                stem = Path(path).stem
                cli = Path(__file__).parent.parent / "resources" / "standalone-renderer" / "standalone-renderer" / "cli.js"
                if not cli.exists():
                    self.solver_q.put(("log", f"[ERROR] Renderer not found at {cli}"))
                    return
                node = shutil.which("node") or "/usr/local/bin/node"
                svg_dir = out_dir / f"{stem}-svg"
                svg_dir.mkdir(exist_ok=True)
                r = subprocess.run([node, str(cli), path, "--output", str(svg_dir)], capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    self.solver_q.put(("log", f"[ERROR] Renderer failed: {(r.stderr or r.stdout).strip()}"))
                    return
                top_svg = svg_dir / "board-top.svg"
                copper_svg = svg_dir / "board-copper.svg"
                top_png = out_dir / f"{stem}-top.png"
                copper_png = out_dir / f"{stem}-copper.png"
                schematic_png = out_dir / f"{stem}-schematic.png"

                # Schematic renderer — separate CLI
                schematic_cli = Path(__file__).parent.parent / "resources" / "standalone-renderer" / "standalone-renderer" / "schematic" / "cli.js"
                schematic_svg = svg_dir / "schematic.svg"
                have_schematic = False
                if schematic_cli.exists():
                    rs = subprocess.run([node, str(schematic_cli), path, "--output", str(svg_dir)], capture_output=True, text=True, timeout=120)
                    if rs.returncode == 0 and schematic_svg.exists():
                        have_schematic = True
                    else:
                        self.solver_q.put(("log", f"[RENDER] Schematic skipped: {(rs.stderr or rs.stdout).strip()[:200]}"))
                else:
                    self.solver_q.put(("log", f"[RENDER] Schematic CLI not found at {schematic_cli}"))
                to_convert = [(top_svg, top_png), (copper_svg, copper_png)]
                if have_schematic:
                    to_convert.append((schematic_svg, schematic_png))
                for src, dst in to_convert:
                    if not src.exists():
                        self.solver_q.put(("log", f"[ERROR] Missing {src.name}"))
                        return
                    subprocess.run(["rsvg-convert", "-w", "2400", "-b", "white", "-o", str(dst), str(src)], check=True, timeout=60)
                saved = f"{top_png.name}, {copper_png.name}"
                if have_schematic:
                    saved += f", {schematic_png.name}"
                self.solver_q.put(("log", f"[RENDER] Saved {saved}"))
                self.solver_q.put(("rendered", str(top_png), str(copper_png),
                                    str(schematic_png) if have_schematic else None))
                self.solver_q.put(("log", "[RESULTS] Board preview refreshed."))
            except Exception as e:
                self.solver_q.put(("log", f"[ERROR] Render failed: {e}"))
        threading.Thread(target=job, daemon=True).start()

    def show_board_view(self):
        # Keep the preview docked beside the active workflow stage.
        self._set_stage("RESULTS")
        self.mode_frame.pack_forget()
        self.questions_frame.pack_forget()
        self.manual_frame.pack_forget()
        self.log_frame.pack(fill="both", expand=True)

    def show_log(self):
        self.mode_frame.pack_forget()
        self.questions_frame.pack_forget()
        self.manual_frame.pack_forget()
        self.log_frame.pack(fill="both", expand=True)
        self.btn_cancel.pack_forget()
        if not self.controller.project: pass
        elif not self.controller.zip_path: self.btn_zip.pack(side="left", padx=8)
        elif not self.controller.net_path: self.btn_net.pack(side="left", padx=8)
        else: self.btn_mode.pack(side="left", padx=8)
