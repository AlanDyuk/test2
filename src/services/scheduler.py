"""Cross-platform background scheduler for price collection."""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Cross-platform background scheduler.
    Manages subprocess lifecycle (start/stop/check).
    Works on Windows and Linux/macOS.
    """

    def __init__(self, pid_file: str = "scheduler_pid.txt"):
        self.pid_file = Path(pid_file)

    def is_running(self) -> bool:
        """Check if scheduler process is alive."""
        if not self.pid_file.exists():
            return False
        try:
            pid = int(self.pid_file.read_text().strip())
            if HAS_PSUTIL:
                return psutil.pid_exists(pid)
            # Fallback: try to signal the process
            try:
                os.kill(pid, 0)
                return True
            except (ProcessLookupError, PermissionError):
                return False
        except (ValueError, IOError):
            return False

    def start(self, interval: int = 300,
              collector_script: str = "albion_data_collector.py") -> subprocess.Popen:
        """
        Start the price collection subprocess.
        Returns the Popen object.
        """
        # Don't start if already running
        if self.is_running():
            logger.warning("Scheduler already running")
            # Kill old process first
            self.stop()
            time.sleep(0.5)

        cmd = [
            sys.executable, collector_script,
            "--interval", str(interval),
        ]

        logger.info(f"Starting scheduler: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )

        # Write PID
        self.pid_file.write_text(str(proc.pid))
        logger.info(f"Scheduler started with PID {proc.pid}")
        return proc

    def stop(self, pid: Optional[int] = None) -> bool:
        """Stop the scheduler process."""
        if pid is None:
            if not self.pid_file.exists():
                return False
            try:
                pid = int(self.pid_file.read_text().strip())
            except ValueError:
                return False

        if HAS_PSUTIL:
            try:
                process = psutil.Process(pid)
                # Graceful kill
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    process.kill()
                    logger.info(f"Force-killed PID {pid}")
                return True
            except psutil.NoSuchProcess:
                pass
        else:
            # Fallback: OS-native kill
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
                try:
                    os.kill(pid, 0)  # Still alive?
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass

        # Clean up PID file
        if self.pid_file.exists():
            self.pid_file.unlink()
        logger.info(f"Scheduler stopped (PID {pid})")
        return True

    def cleanup_stale_pid(self) -> None:
        """Remove PID file if process is dead."""
        if self.pid_file.exists() and not self.is_running():
            self.pid_file.unlink()
            logger.info("Stale PID file removed")
