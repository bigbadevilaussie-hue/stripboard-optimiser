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
        import re
        self.zip_path = path
        self.zip_footprints = {}
        raw_mods = {}
        try:
            with zipfile.ZipFile(path, 'r') as z:
                for name in z.namelist():
                    if name.endswith(".kicad_mod") and not name.startswith("._"):
                        fp_name = name.split("/")[-1].replace(".kicad_mod", "")
                        content = z.read(name).decode('utf-8', errors='ignore')
                        raw_mods[fp_name] = content
                        pad_count = len(re.findall(r'\(pad\s', content))
                        w, h = 1, 1
                        pad_coords = re.findall(r'\(at\s+([-\d.]+)\s+([-\d.]+)\)', content)
                        if pad_coords:
                            xs = [float(p[0]) for p in pad_coords]
                            ys = [float(p[1]) for p in pad_coords]
                            w = max(1, int(round((max(xs) - min(xs)) / 2.54)) + 1)
                            h = max(1, int(round((max(ys) - min(ys)) / 2.54)) + 1)
                        self.zip_footprints[fp_name] = (pad_count, w, h)
        except Exception as e:
            raise Exception(f"Could not read ZIP: {e}")
        if not self.project: return self.zip_footprints
        def parse_mod(content):
            pads = []
            for m in re.finditer(r'\(pad\s+"([^"]+)"[^(]*\(at\s+([-\d.]+)\s+([-\d.]+)', content):
                pads.append({"id": m.group(1), "x": float(m.group(2)), "y": float(m.group(3))})
            labels = []
            for m in re.finditer(r'\(fp_text user\s+"([^"]+)"\s+\(at\s+([-\d.]+)\s+([-\d.]+)', content):
                labels.append({"name": m.group(1), "x": float(m.group(2)), "y": float(m.group(3))})
            if not pads: return None
            for pad in pads:
                best = None
                for lbl in labels:
                    if abs(pad["x"] - lbl["x"]) < 0.1 and abs(pad["y"] - lbl["y"]) < 0.1:
                        best = lbl["name"]; break
                pad["name"] = best or pad["id"]
            min_x = min(p["x"] for p in pads)
            min_y = min(p["y"] for p in pads)
            max_x = max(p["x"] for p in pads)
            max_y = max(p["y"] for p in pads)
            w = int(round((max_x - min_x) / 2.54)) + 1
            h = int(round((max_y - min_y) / 2.54)) + 1
            pins = [{"id": p["id"], "name": p["name"], "offsetRow": int(round((p["y"] - min_y) / 2.54)), "offsetCol": int(round((p["x"] - min_x) / 2.54))} for p in pads]
            body = [{"row": r, "col": c} for r in range(h) for c in range(w) if not any(pp["offsetRow"] == r and pp["offsetCol"] == c for pp in pins)]
            return {"width": w, "height": h, "pins": pins, "bodyCells": body}
        parsed = {n: parse_mod(c) for n, c in raw_mods.items()}
        parsed = {k: v for k, v in parsed.items() if v}
        raw = self.project.raw_data
        defs = raw.setdefault("componentDefs", [])
        existing = {d["id"] for d in defs}
        for c in raw.get("components", []):
            did = c.get("defId") or c.get("componentDefId")
            if not did or did in existing: continue
            label = c.get("label") or c.get("name") or ""
            clean = label.lower().replace(" ", "").replace("-", "").replace("_", "")
            best = None
            for fname in parsed:
                cf = fname.lower().replace(" ", "").replace("-", "").replace("_", "")
                if clean in cf or cf in clean: best = fname; break
            if best:
                new_def = dict(parsed[best])
                new_def["id"] = did
                new_def["name"] = label
                new_def["category"] = "generic"
                new_def["symbol"] = f"custom-footprint-{did}"
                new_def["defaultLabelPrefix"] = "?"
                defs.append(new_def)
                existing.add(did)
        return self.zip_footprints

    def run_preflight(self):
        if not self.project:
            raise Exception("No project loaded.")
        return PreflightService.run(self.project, self.zip_footprints)
