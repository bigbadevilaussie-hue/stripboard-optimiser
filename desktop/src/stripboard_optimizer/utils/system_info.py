"""Detect CPU model, cores, RAM. macOS via sysctl, Windows via PowerShell/CIM."""
import os
import platform
import subprocess
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SystemInfo:
    os_name: str
    cpu_model: str | None
    physical_cores: int | None
    logical_cores: int | None
    total_ram_gb: float | None
    recommended_threads: int
    detection_notes: list[str] = field(default_factory=list)


def _run(cmd: list[str], timeout: int = 5) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _detect_macos(notes: list[str]) -> dict:
    model = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    if not model:
        notes.append("macOS: cpu model unavailable from sysctl")

    physical = _run(["sysctl", "-n", "hw.physicalcpu"])
    physical = int(physical) if physical and physical.isdigit() else None
    if physical is None:
        notes.append("macOS: physical core count unavailable")

    logical = _run(["sysctl", "-n", "hw.logicalcpu"])
    logical = int(logical) if logical and logical.isdigit() else None
    if logical is None:
        notes.append("macOS: logical core count unavailable")

    mem = _run(["sysctl", "-n", "hw.memsize"])
    ram_gb = None
    if mem and mem.isdigit():
        ram_gb = round(int(mem) / (1024 ** 3), 1)
    else:
        notes.append("macOS: installed RAM unavailable")

    return {"cpu_model": model, "physical_cores": physical,
            "logical_cores": logical, "total_ram_gb": ram_gb}


def _detect_windows(notes: list[str]) -> dict:
    ps = _run([
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Processor | "
        "Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | "
        "ConvertTo-Json -Compress"
    ], timeout=10)
    model = physical = logical = None
    if ps:
        import json
        try:
            obj = json.loads(ps)
            if isinstance(obj, list):
                obj = obj[0]
            model = obj.get("Name")
            physical = obj.get("NumberOfCores")
            logical = obj.get("NumberOfLogicalProcessors")
        except (ValueError, IndexError, AttributeError):
            notes.append("Windows: PowerShell CPU output unparseable")

    if not ps:
        notes.append("Windows: PowerShell/CIM CPU query failed")

    mem_ps = _run([
        "powershell", "-NoProfile", "-Command",
        "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"
    ], timeout=10)
    ram_gb = None
    if mem_ps and mem_ps.isdigit():
        ram_gb = round(int(mem_ps) / (1024 ** 3), 1)
    else:
        notes.append("Windows: RAM query failed")

    return {"cpu_model": model, "physical_cores": physical,
            "logical_cores": logical, "total_ram_gb": ram_gb}


def detect() -> SystemInfo:
    notes: list[str] = []
    system = platform.system()

    if system == "Darwin":
        data = _detect_macos(notes)
        os_name = "macos"
    elif system == "Windows":
        data = _detect_windows(notes)
        os_name = "windows"
    else:
        data = {"cpu_model": None, "physical_cores": None,
                "logical_cores": None, "total_ram_gb": None}
        os_name = system.lower() or "unknown"
        notes.append(f"{system}: not a supported OS for detection; fields left None")

    # Fallback to os.cpu_count() for logical only. Physical still needs native.
    if data["logical_cores"] is None:
        guessed = os.cpu_count()
        if guessed:
            data["logical_cores"] = guessed
            notes.append("Logical cores fell back to os.cpu_count()")
        else:
            notes.append("Logical cores: os.cpu_count() returned None")

    base = data["physical_cores"] or data["logical_cores"] or 1
    recommended = max(1, min(base, 4))

    return SystemInfo(
        os_name=os_name,
        cpu_model=data["cpu_model"],
        physical_cores=data["physical_cores"],
        logical_cores=data["logical_cores"],
        total_ram_gb=data["total_ram_gb"],
        recommended_threads=recommended,
        detection_notes=notes,
    )
