import json
import os
from stripboard_optimizer.models.project import Project

class ImportService:
    @staticmethod
    def load_project(path):
        with open(path, 'r') as f:
            data = json.load(f)
        return Project(data)
        
    @staticmethod
    def count_netlist_nodes(path):
        net_nodes = 0
        with open(path, 'r') as f:
            for line in f:
                if line.strip().startswith("(node (ref"):
                    net_nodes += 1
        return net_nodes

    @staticmethod
    def parse_kicad_footprint(content):
        """Extracts the footprint name and counts pads (pins) from a .kicad_mod file."""
        name = "Unknown"
        pin_count = 0
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("(module") or line.startswith("(footprint"):
                parts = line.split()
                if len(parts) > 1:
                    name = parts[1].strip('"')
            elif line.startswith("(pad "):
                pin_count += 1
        return name, pin_count
