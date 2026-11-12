import json

class Project:
    def __init__(self, data):
        self.raw_data = data
        board = data.get("board", {})
        
        # The JSON format uses rows/cols inside the board object, 
        # but sometimes lockedRows/lockedCols are at the root.
        self.rows = board.get("rows", 0)
        self.cols = board.get("columns", board.get("cols", 0))
        
        self.locked_rows = data.get("lockedRows", board.get("lockedRows", False))
        self.locked_cols = data.get("lockedCols", board.get("lockedCols", False))
        
        self.components = data.get("components", [])
        self.component_defs = {d["id"]: d for d in data.get("componentDefs", [])}
        self.nets = data.get("nets", [])
        self.net_assignments = data.get("netAssignments", [])
        
    @property
    def missing_footprints(self):
        missing = []
        for c in self.components:
            def_id = c.get("componentDefId") or c.get("defId")
            if def_id not in self.component_defs:
                missing.append(c)
        return missing

    @property
    def pin_count(self):
        return len(self.net_assignments)
