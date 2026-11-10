import zipfile
import re
from stripboard_optimizer.services.import_service import ImportService
from stripboard_optimizer.validation.preflight import PreflightService

class ProjectController:
    def __init__(self):
        self.project = None
        self.net_path = None
        self.zip_path = None
        self.zip_footprints = {} # dict of {footprint_name: (pads, width, height)}

    def load_project(self, path):
        self.project = ImportService.load_project(path)
        return self.project

    def load_netlist(self, path):
        if not self.project:
            raise Exception("Load a project first.")
        net_nodes = ImportService.count_netlist_nodes(path)
        if net_nodes != self.project.pin_count:
            raise ValueError(f"CRITICAL MISMATCH: JSON has {self.project.pin_count} pins, .net has {net_nodes} pins.")
        self.net_path = path
        return net_nodes

    def load_zip(self, path):
        self.zip_path = path
        self.zip_footprints = {}
        try:
            with zipfile.ZipFile(path, 'r') as z:
                for name in z.namelist():
                    if name.endswith(".kicad_mod"):
                        content = z.read(name).decode('utf-8', errors='ignore')
                        fp_name = name.split("/")[-1].replace(".kicad_mod", "")
                        
                        # Count pads
                        pad_count = len(re.findall(r'\(pad\s', content))
                        
                        # Try to find width/height in the module definition or courtyard
                        # For simplicity, if we can't find it, we'll estimate based on pads (worst case)
                        # Real KiCad footprints have (fp_line) or (fp_rect) with start/end coordinates
                        # We will look for the bounding box of the pads for a safe estimate.
                        
                        # Default fallback
                        w, h = 1, 1
                        
                        # Find all pad positions (at x y)
                        pad_coords = re.findall(r'\(at\s+([-\d.]+)\s+([-\d.]+)\)', content)
                        if pad_coords:
                            xs = [float(p[0]) for p in pad_coords]
                            ys = [float(p[1]) for p in pad_coords]
                            
                            # Distance in mm, convert to holes (2.54mm grid)
                            width_mm = max(xs) - min(xs)
                            height_mm = max(ys) - min(ys)
                            
                            # Round up to nearest 2.54mm hole
                            w = max(1, int(round(width_mm / 2.54)) + 1)
                            h = max(1, int(round(height_mm / 2.54)) + 1)
                            
                        self.zip_footprints[fp_name] = (pad_count, w, h)
        except Exception as e:
            raise Exception(f"Could not read ZIP: {e}")
        return self.zip_footprints

    def run_preflight(self):
        if not self.project:
            raise Exception("No project loaded.")
        return PreflightService.run(self.project, self.zip_footprints)
