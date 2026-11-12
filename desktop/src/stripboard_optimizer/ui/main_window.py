import tkinter as tk
from tkinter import ttk, filedialog
import os, zipfile
import json, queue, shutil, subprocess, tempfile, threading
from pathlib import Path
from stripboard_optimizer.ui.project_panel import ProjectPanel
from stripboard_optimizer.ui.validation_panel import ValidationPanel
from stripboard_optimizer.ui.board_viewer import BoardViewer
from stripboard_optimizer.controllers.project_controller import ProjectController
from stripboard_optimizer.filters import split_parts, part_size, def_id_of
from stripboard_optimizer.board_estimator import estimate_board
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

APP_VERSION = "v1.10"

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stripboard Optimiser")
        self.geometry("1100x750")
        self.configure(bg=BG_ROOT)
        self.controller = ProjectController()
        self.estimated_tight = (0, 0)
        self.lock_vars = {}
        self.project_path = None
        self.solver = None
        self.solver_q = queue.Queue()
        self.best = None
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
        self.paned = ttk.PanedWindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True, padx=16, pady=16)
        left_wrapper = ttk.Frame(self.paned, style="TFrame")
        self.paned.add(left_wrapper, weight=1)
        self.project_panel = ProjectPanel(left_wrapper)
        self.project_panel.pack(fill="both", expand=True)
        version_label = tk.Label(left_wrapper, text=APP_VERSION, bg=BG_ROOT, fg="#9ca3af", font=("Helvetica Neue", 10))
        version_label.pack(side="bottom", anchor="w", pady=(8, 0), padx=4)

        self.right_frame = ttk.Frame(self.paned, style="TFrame")
        self.paned.add(self.right_frame, weight=4)

        self.log_frame = ttk.Frame(self.right_frame, style="Panel.TFrame", padding=1)
        self.validation_panel = ValidationPanel(self.log_frame)
        self.validation_panel.pack(fill="both", expand=True)

        self.board_view_frame = ttk.Frame(self.right_frame, style="Panel.TFrame")
        self.board_viewer = BoardViewer(self.board_view_frame, on_close=self.show_log)
        self.board_viewer.pack(fill="both", expand=True)

        # PANEL 1: MODE SELECT
        self.mode_frame = ttk.Frame(self.right_frame, style="Panel.TFrame", padding=40)
        ttk.Label(self.mode_frame, text="Select Optimisation Mode", font=FONT_SANS_BOLD, background=BG_PANEL).pack(pady=(0, 20))
        self.mode_var = tk.StringVar(value="2pass")
        modes = [
            ("manual", "Manual (Expert Mode)", "Control every seed and weight manually."),
            ("full_auto", "Auto (Cross your fingers and pray)", "The solver picks the settings and runs a massive sweep."),
            ("2pass", "2-Pass Tournament (Preferred)", "Run a wide qualifier, then a high-effort Grand Final.")
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
        self.questions_frame = ttk.Frame(self.right_frame, style="Panel.TFrame", padding=40)
        self.canvas = tk.Canvas(self.questions_frame, bg=BG_PANEL, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.questions_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style="Panel.TFrame")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.q_btn_frame = ttk.Frame(self.questions_frame, style="Panel.TFrame")
        self.q_btn_frame.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Button(self.q_btn_frame, text="START OPTIMISATION", style="Green.TButton", command=self.start_optimisation).pack(side="right", ipadx=20, ipady=10)

        # PANEL 3: MANUAL SETTINGS
        self.manual_frame = ttk.Frame(self.right_frame, style="Panel.TFrame", padding=40)
        ttk.Label(self.manual_frame, text="Manual Settings", font=FONT_SANS_BOLD, background=BG_PANEL).pack(pady=(0, 20))
        tk.Label(self.manual_frame, text="(Configure locks, seeds, and weights here)", bg=BG_PANEL, fg="#737373", font=FONT_SANS).pack()
        ttk.Button(self.manual_frame, text="START OPTIMISATION", style="Green.TButton", command=self.start_optimisation).pack(pady=(30, 0), ipadx=20, ipady=10)

        self.log_frame.pack(fill="both", expand=True)
        self.log("Ready. Open a project JSON to begin.")
        self.after(200, self._poll_solver)

    def log(self, msg):
        self.validation_panel.log(msg)

    def reset_app(self):
        self.controller = ProjectController()
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
        self.log("\n--- 4. PREFLIGHT ---")
        findings = self.controller.run_preflight()
        self.validation_panel.log_findings(findings)
        has_errors = any(f.severity == "ERROR" for f in findings)
        if not has_errors:
            self.btn_preflight.pack_forget()
            self.btn_mode.pack(side="left", padx=8)

    def show_mode_select(self):
        self.log_frame.pack_forget()
        self.mode_frame.pack(fill="both", expand=True)
        self.btn_mode.pack_forget()
        self.btn_cancel.pack(side="left", padx=8)

    def confirm_mode(self):
        mode = self.mode_var.get()
        self.log(f"\n--- 5. MODE SELECT ---")
        self.log(f"[INFO] User selected: {mode.upper()}")
        self.mode_frame.pack_forget()
        if mode == "manual":
            self.manual_frame.pack(fill="both", expand=True)
        else:
            self.show_questions()

    def show_questions(self):
        self.questions_frame.pack(fill="both", expand=True)
        project = self.controller.project
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.lock_vars = {}
        if project.locked_rows or project.locked_cols:
            frame = ttk.Frame(self.scrollable_frame, style="Panel.TFrame")
            frame.pack(fill="x", pady=(0, 20))
            tk.Label(frame, text=f"Keep Board Dimensions Locked ({project.rows}x{project.cols})?", bg=BG_PANEL, fg=FG_TEXT, font=FONT_SANS_BOLD).pack(anchor="w")
            keep_var = tk.StringVar(value="yes")
            tk.Radiobutton(frame, text="Yes", variable=keep_var, value="yes", bg=BG_PANEL, fg=FG_TEXT).pack(anchor="w")
            tk.Radiobutton(frame, text="No (Unlock and auto-size)", variable=keep_var, value="no", bg=BG_PANEL, fg=FG_TEXT).pack(anchor="w")
            tk.Label(frame, text="Why was it locked? (e.g., physical case limit, cosmetic)", bg=BG_PANEL, fg=FG_TEXT, font=FONT_SANS).pack(anchor="w", pady=(5,0))
            reason_entry = tk.Entry(frame, width=50)
            reason_entry.pack(anchor="w")
            self.lock_vars["BOARD"] = {"keep": keep_var, "reason": reason_entry}
        else:
            tk.Label(self.scrollable_frame, text="Board dimensions are not locked.", bg=BG_PANEL, fg=FG_TEXT, font=FONT_SANS).pack(anchor="w", pady=(0, 20))
        placed = [c for c in project.components if c.get("boardPos")]
        locked = [c for c in placed if c.get("locked") is True]
        if locked:
            tk.Label(self.scrollable_frame, text="Locked Parts:", bg=BG_PANEL, fg=FG_TEXT, font=FONT_SANS_BOLD).pack(anchor="w", pady=(10, 5))
            for c in locked:
                label = c.get("label") or c.get("name") or "Unknown"
                frame = ttk.Frame(self.scrollable_frame, style="Panel.TFrame")
                frame.pack(fill="x", pady=(5, 10))
                tk.Label(frame, text=f"Keep {label} locked?", bg=BG_PANEL, fg=FG_TEXT, font=FONT_SANS_BOLD).pack(anchor="w")
                keep_var = tk.StringVar(value="yes")
                tk.Radiobutton(frame, text="Yes", variable=keep_var, value="yes", bg=BG_PANEL, fg=FG_TEXT).pack(anchor="w")
                tk.Radiobutton(frame, text="No (Unlock and scramble)", variable=keep_var, value="no", bg=BG_PANEL, fg=FG_TEXT).pack(anchor="w")
                tk.Label(frame, text="Reason:", bg=BG_PANEL, fg=FG_TEXT, font=FONT_SANS).pack(anchor="w", pady=(5,0))
                reason_var = tk.StringVar(value="edge/case/cosmetic")
                reason_entry = ttk.Combobox(frame, textvariable=reason_var, values=["edge", "case", "cosmetic", "mistake"])
                reason_entry.pack(anchor="w")
                self.lock_vars[label] = {"keep": keep_var, "reason": reason_entry}
        else:
            tk.Label(self.scrollable_frame, text="No parts are locked.", bg=BG_PANEL, fg=FG_TEXT, font=FONT_SANS).pack(anchor="w")

    def start_optimisation(self):
        self.log(f"\n--- 5. PLACEMENT STRATEGY ---")
        project = self.controller.project
        unlocked = set()
        board_change = None
        if "BOARD" in self.lock_vars:
            data = self.lock_vars["BOARD"]
            keep, reason = data["keep"].get(), data["reason"].get()
            self.log(f"[INFO] Board Lock: Keep={keep} | Reason: {reason}")
            if keep == "no":
                self.log(f"[APPLY] Unlocking board. Auto-sizing to {self.estimated_tight[0]}x{self.estimated_tight[1]}.")
                board_change = self.estimated_tight
                project.rows, project.cols = self.estimated_tight
                project.locked_rows = project.locked_cols = False
        for c in project.components:
            label = c.get("label") or c.get("name") or "Unknown"
            if label in self.lock_vars:
                data = self.lock_vars[label]
                keep, reason = data["keep"].get(), data["reason"].get()
                self.log(f"[INFO] Part Lock '{label}': Keep={keep} | Reason: {reason}")
                if keep == "no":
                    c["locked"] = False
                    unlocked.add(label)
        self.questions_frame.pack_forget()
        self.manual_frame.pack_forget()
        self.log_frame.pack(fill="both", expand=True)
        mode = self.mode_var.get()
        self.log(f"\n[OPTIMISE] Starting mode: {mode.upper()}")
        try:
            raw = json.loads(Path(self.project_path).read_text())
            if board_change:
                raw.setdefault("board", {}).update(rows=board_change[0], cols=board_change[1], lockedRows=False, lockedCols=False)
            for c in raw.get("components", []):
                if (c.get("label") or c.get("name") or "Unknown") in unlocked:
                    c["locked"] = False
            job = Path(tempfile.mkdtemp(prefix="sbjob_")) / "project.json"
            job.write_text(json.dumps(raw))
        except Exception as e:
            self.log(f"[ERROR] Could not prepare the solver input: {e}")
            return
        self.best = None
        self.btn_preview.pack_forget()
        self.btn_cancel.pack_forget()
        self.btn_stop.pack(side="left", padx=8)
        self.solver = SolveWorker(str(job), mode, self.solver_q)
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
                    _, stage, seed, effort, s, path, ok = m
                    tag = "OK " if ok else "BAD"
                    self.log(f"[{tag}] stage {stage} seed {seed} e{effort}: {s['rows']}x{s['cols']} wires {s['wires']} cuts {s['cuts']} price {s.get('price', '?')} ({s['ms']/1000:.0f}s)")
                elif m[0] == "done":
                    _, best, cancelled = m
                    self.btn_stop.pack_forget()
                    self.btn_cancel.pack_forget()
                    if cancelled:
                        self.log("[SOLVE] Stopped.")
                    elif best:
                        s, path, seed = best
                        out = Path(self.project_path).with_name(Path(self.project_path).stem + "_solved.json")
                        out.write_text(Path(path).read_text())
                        self.best = (s, str(out))
                        self.log(f"\n[BEST] seed {seed}: {s['rows']}x{s['cols']}, wires {s['wires']}, cuts {s['cuts']} (knife {s['knife']}), price {s.get('price', '?')}")
                        self.log(f"[BEST] Saved to {out}")
                        self.btn_preview.pack(side="left", padx=8)
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
                self.solver_q.put(("log", f"[PREVIEW] Rendered {top_png} and {copper_png}"))
                subprocess.run(["open", str(top_png), str(copper_png)])
            except subprocess.TimeoutExpired:
                self.solver_q.put(("log", "[ERROR] Preview timed out"))
            except Exception as e:
                self.solver_q.put(("log", f"[ERROR] Preview failed: {e}"))
        threading.Thread(target=job, daemon=True).start()

    def render_from_file(self):
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if not path: return
        self.log(f"\n[RENDER] {os.path.basename(path)}")
        def job():
            try:
                out_dir = Path.home() / "Desktop" / "stripboard-renders"
                out_dir.mkdir(parents=True, exist_ok=True)
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
                self.board_viewer.load(str(top_png), str(copper_png), str(schematic_png) if have_schematic else None)
                self.show_board_view()
            except Exception as e:
                self.solver_q.put(("log", f"[ERROR] Render failed: {e}"))
        threading.Thread(target=job, daemon=True).start()

    def show_board_view(self):
        for f in [self.log_frame, self.mode_frame, self.questions_frame, self.manual_frame]:
            f.pack_forget()
        self.board_view_frame.pack(fill="both", expand=True)

    def show_log(self):
        self.mode_frame.pack_forget()
        self.questions_frame.pack_forget()
        self.manual_frame.pack_forget()
        self.board_view_frame.pack_forget()
        self.log_frame.pack(fill="both", expand=True)
        self.btn_cancel.pack_forget()
        if not self.controller.project: pass
        elif not self.controller.zip_path: self.btn_zip.pack(side="left", padx=8)
        elif not self.controller.net_path: self.btn_net.pack(side="left", padx=8)
        else: self.btn_mode.pack(side="left", padx=8)
