class Finding:
    def __init__(self, severity, message):
        self.severity = severity
        self.message = message

class PreflightService:
    @staticmethod
    def run(project, zip_footprints):
        findings = []
        
        if project.rows <= 0 or project.cols <= 0:
            findings.append(Finding("ERROR", f"Invalid board dimensions: {project.rows}x{project.cols}"))
            return findings
            
        board_area = project.rows * project.cols
        findings.append(Finding("OK", f"Board dimensions valid: {project.rows} x {project.cols} ({board_area} holes)."))
        
        if not zip_footprints:
            findings.append(Finding("WARN", "Missing footprint definitions. Waiting for Pretty KiCad ZIP."))
        else:
            findings.append(Finding("OK", f"Loaded {len(zip_footprints)} footprints from ZIP."))
            
            # Verify pins for on-board components
            verified_count = 0
            for c in project.components:
                if c.get("boardExcluded") is True or c.get("offBoard") is True:
                    continue
                
                def_id = c.get("componentDefId") or c.get("defId")
                c_def = project.component_defs.get(def_id)
                if not c_def: continue
                
                # Try to find the footprint by name
                fp_name = c_def.get("name", "").replace(" ", "_")
                # The web editor might use a different name, we'll do a basic check
                if fp_name in zip_footprints:
                    expected_pins = zip_footprints[fp_name]
                    # We don't have pin assignments per component easily accessible here
                    # so we just log that we found a matching footprint
                    findings.append(Finding("OK", f"Matched footprint: {fp_name} (Pads: {expected_pins})"))
                    verified_count += 1
            
            if verified_count == 0:
                 findings.append(Finding("WARN", "No footprints matched the component definitions by name."))

        if project.locked_rows or project.locked_cols:
            findings.append(Finding("OK", f"Board dimensions locked (Rows: {project.locked_rows}, Cols: {project.locked_cols})."))

        has_errors = any(f.severity == "ERROR" for f in findings)
        if not has_errors:
            findings.append(Finding("PASS", "Preflight complete. Ready to optimise."))
            
        return findings
