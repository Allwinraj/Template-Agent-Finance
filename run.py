"""
Nexus 2.0 - Start backend + frontend together.

Usage:
    python run.py            # start both servers
    python run.py --backend  # backend only
    python run.py --frontend # frontend only

Backend : http://127.0.0.1:8000  (API docs at /docs)
Frontend: http://localhost:3000
"""
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

BACKEND_PORT = 8000
FRONTEND_PORT = 3000

# Make sure node/npm are reachable even if not on PATH
NODE_CANDIDATES = [
    Path(r"C:\Program Files\nodejs"),
    Path(r"C:\Program Files (x86)\nodejs"),
    Path.home() / "AppData" / "Roaming" / "npm",
]
for candidate in NODE_CANDIDATES:
    if candidate.exists() and str(candidate) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
        break

IS_WINDOWS = os.name == "nt"
NPM = "npm.cmd" if IS_WINDOWS else "npm"
PYTHON = sys.executable

processes = []


def kill_port(port):
    """Kill any process currently listening on the given port."""
    if IS_WINDOWS:
        try:
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if (":" + str(port)) in line and "LISTENING" in line:
                    parts = line.strip().split()
                    pid = parts[-1]
                    if pid.isdigit():
                        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
                        print("[Nexus] Killed existing process on port " + str(port) + " (PID " + pid + ")")
        except Exception as e:
            print("[Nexus] Warning: could not kill port " + str(port) + ": " + str(e))
    else:
        try:
            result = subprocess.run(["lsof", "-ti", ":" + str(port)], capture_output=True, text=True)
            for pid in result.stdout.strip().splitlines():
                if pid.isdigit():
                    subprocess.run(["kill", "-9", pid], capture_output=True)
                    print("[Nexus] Killed existing process on port " + str(port) + " (PID " + pid + ")")
        except Exception as e:
            print("[Nexus] Warning: could not kill port " + str(port) + ": " + str(e))


def start_backend():
    os.environ["NEXUS_PORT"] = str(BACKEND_PORT)
    print("[Nexus] Starting backend  ->  http://127.0.0.1:" + str(BACKEND_PORT) + "  (docs: /docs)")
    proc = subprocess.Popen(
        [PYTHON, str(BACKEND_DIR / "run.py")],
        cwd=str(BACKEND_DIR),
        env=os.environ.copy(),
    )
    processes.append(("backend", proc))


def start_frontend():
    os.environ["VITE_PORT"] = str(FRONTEND_PORT)
    os.environ["PORT"] = str(FRONTEND_PORT)

    if not (FRONTEND_DIR / "node_modules").exists():
        print("[Nexus] Installing frontend dependencies (first run)...")
        subprocess.run([NPM, "install"], cwd=str(FRONTEND_DIR), env=os.environ.copy())

    print("[Nexus] Starting frontend ->  http://localhost:" + str(FRONTEND_PORT))
    proc = subprocess.Popen(
        [NPM, "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort"],
        cwd=str(FRONTEND_DIR),
        env=os.environ.copy(),
    )
    processes.append(("frontend", proc))


def main():
    args = sys.argv[1:]
    run_backend = "--frontend" not in args
    run_frontend = "--backend" not in args

    print("=" * 60)
    print("  NEXUS 2.0 - Finance Operations Agent Platform")
    print("=" * 60)

    # Kill any existing processes on our ports first
    if run_backend:
        kill_port(BACKEND_PORT)
    if run_frontend:
        kill_port(FRONTEND_PORT)

    # Small pause to let the OS release the ports
    time.sleep(1)

    if run_backend:
        start_backend()
        time.sleep(2)

    if run_frontend:
        start_frontend()
        time.sleep(3)
        try:
            webbrowser.open("http://localhost:" + str(FRONTEND_PORT))
        except Exception:
            pass

    print("-" * 60)
    print("  Press Ctrl+C to stop all servers")
    print("=" * 60)

    try:
        while True:
            for name, proc in processes:
                if proc.poll() is not None:
                    print("\n[Nexus] " + name + " exited (code " + str(proc.returncode) + ").")
                    raise KeyboardInterrupt
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Nexus] Shutting down...")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                print("[Nexus] " + name + " stopped.")
        print("[Nexus] Goodbye.")


if __name__ == "__main__":
    main()
