"""Détections d'environnement et vérifications cross-OS."""
import os
import platform
import shutil
import subprocess
from pathlib import Path


def detect_os() -> str:
    """Retourne 'macos', 'linux', 'windows', ou 'unknown'."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    return "unknown"


def get_os_info() -> dict:
    """Infos système détaillées."""
    home = Path.home()
    try:
        free = shutil.disk_usage(home).free / (1024**3)
    except Exception:
        free = 0

    try:
        # RAM (cross-OS)
        if platform.system() == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip()
            ram_gb = int(out) / (1024**3)
        elif platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        ram_gb = int(line.split()[1]) / (1024**2)
                        break
                else:
                    ram_gb = 0
        elif platform.system() == "Windows":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            ram_gb = stat.ullTotalPhys / (1024**3)
        else:
            ram_gb = 0
    except Exception:
        ram_gb = 0

    return {
        "system": platform.system(),
        "release": platform.release(),
        "arch": platform.machine(),
        "ram_gb": round(ram_gb, 1),
        "free_disk_gb": round(free, 1),
        "home": str(home),
    }


def command_exists(cmd: str) -> bool:
    """Vérifie qu'une commande est dans le PATH."""
    return shutil.which(cmd) is not None


def get_command_version(cmd: str, version_arg: str = "--version") -> str:
    """Retourne la sortie de `cmd --version` ou '' si non disponible."""
    try:
        out = subprocess.check_output(
            [cmd, version_arg],
            stderr=subprocess.STDOUT,
            timeout=5,
        )
        return out.decode().strip().split("\n")[0]
    except Exception:
        return ""


def check_docker_running() -> bool:
    """Vérifie que le daemon Docker tourne."""
    try:
        subprocess.check_output(
            ["docker", "info"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return True
    except Exception:
        return False


def check_url_reachable(url: str, timeout: int = 5) -> bool:
    """Vérifie qu'une URL HTTP répond."""
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False