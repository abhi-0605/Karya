"""
Unified Local Process Runner for KaryaOS.
Starts Mock APIs (:8001), Backend API (:8000), and Operations Dashboard (:8501)
together with port pre-flight checks, clear logs, and coordinated clean shutdown.
"""
from __future__ import annotations
import os
import sys
import socket
import subprocess
import time
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SERVICES = [
    {
        "name": "Mock Fulfillment APIs",
        "port": 8001,
        "env_var": "MOCK_API_PORT",
        "cmd": [sys.executable, "-m", "uvicorn", "mocks.main:app", "--port", "8001", "--host", "0.0.0.0"],
        "cwd": PROJECT_ROOT,
    },
    {
        "name": "KaryaOS Backend API",
        "port": 8000,
        "env_var": "BACKEND_PORT",
        "cmd": [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "0.0.0.0"],
        "cwd": PROJECT_ROOT / "backend",
    },
    {
        "name": "Streamlit Governance Dashboard",
        "port": 8501,
        "env_var": "STREAMLIT_PORT",
        "cmd": [sys.executable, "-m", "streamlit", "run", "apps/web/dashboard.py", "--server.port", "8501", "--server.headless", "true"],
        "cwd": PROJECT_ROOT,
    },
]


def is_port_in_use(port: int) -> bool:
    """Check if a TCP port is currently occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def check_ports() -> bool:
    """Pre-flight check across all target ports."""
    busy_ports = []
    for svc in SERVICES:
        if is_port_in_use(svc["port"]):
            busy_ports.append(svc)

    if busy_ports:
        print("\n" + "=" * 60)
        print("❌ PRE-FLIGHT ERROR: Target ports are already occupied:")
        print("=" * 60)
        for svc in busy_ports:
            print(f"  • {svc['name']}: Port {svc['port']} is busy.")
            print(f"    👉 Free the port, or override with ${svc['env_var']}=<new_port>")
        print("=" * 60 + "\n")
        return False
    return True


def run_all():
    print("=" * 65)
    print("⚡ KaryaOS Unified Local Runner")
    print("   Starting Mock APIs (:8001), Backend (:8000), Dashboard (:8501)")
    print("=" * 65)

    if not check_ports():
        sys.exit(1)

    processes: list[tuple[str, subprocess.Popen]] = []

    def shutdown(signum=None, frame=None):
        print("\n🛑 Initiating graceful shutdown of all KaryaOS services...")
        for name, proc in processes:
            try:
                print(f"   Terminating {name} (PID {proc.pid})...")
                proc.terminate()
            except Exception:
                pass
        time.sleep(1)
        for name, proc in processes:
            try:
                proc.kill()
            except Exception:
                pass
        print("✅ All services stopped cleanly. Bye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Set local env vars
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT};{PROJECT_ROOT / 'backend'};{env.get('PYTHONPATH', '')}"
    env["DATABASE_URL"] = env.get("DATABASE_URL", "sqlite+aiosqlite:///./karyaos.db")
    env["MOCK_API_BASE_URL"] = "http://localhost:8001"

    try:
        for svc in SERVICES:
            print(f"🚀 Starting {svc['name']} on port {svc['port']}...")
            proc = subprocess.Popen(
                svc["cmd"],
                cwd=str(svc["cwd"]),
                env=env,
            )
            processes.append((svc["name"], proc))
            time.sleep(1.5)

        print("\n" + "=" * 65)
        print("🎉 ALL KARYAOS SERVICES ARE LIVE!")
        print("   • Backend API Swagger: http://localhost:8000/docs")
        print("   • Operations Dashboard: http://localhost:8501")
        print("   • Mock Fulfillment APIs: http://localhost:8001/docs")
        print("   Press Ctrl+C to stop all services.")
        print("=" * 65 + "\n")

        # Monitor child processes
        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"⚠️ Service '{name}' exited unexpectedly with code {ret}")
                    shutdown()
            time.sleep(1)

    except KeyboardInterrupt:
        shutdown()
    except Exception as e:
        print(f"❌ Unexpected runner error: {e}")
        shutdown()


if __name__ == "__main__":
    run_all()
