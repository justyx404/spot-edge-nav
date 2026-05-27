from __future__ import annotations

import asyncio
import os
import signal
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .stack_config import REPO_ROOT, with_ros_setup, without_ros_setup


@dataclass
class ProcessState:
    name: str
    command: str
    process: asyncio.subprocess.Process | None = None
    started_at: str | None = None
    stopped_at: str | None = None
    returncode: int | None = None
    log: deque[str] = field(default_factory=lambda: deque(maxlen=500))

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    def snapshot(self) -> dict:
        if self.process is not None:
            self.returncode = self.process.returncode
        return {
            "name": self.name,
            "command": self.command,
            "running": self.running,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "returncode": self.returncode,
        }


class ProcessManager:
    def __init__(self) -> None:
        self._states: dict[str, ProcessState] = {}
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    def status(self) -> dict[str, dict]:
        return {name: state.snapshot() for name, state in self._states.items()}

    def logs(self, name: str | None = None) -> list[str]:
        if name is not None:
            state = self._states.get(name)
            return list(state.log) if state else []
        lines: list[str] = []
        for state in self._states.values():
            lines.extend(state.log)
        return lines[-500:]

    async def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    async def start(self, name: str, command: str) -> dict:
        async with self._lock:
            existing = self._states.get(name)
            if existing and existing.running:
                return {"ok": False, "message": f"{name} is already running", "state": existing.snapshot()}

            state = ProcessState(
                name=name,
                command=command,
                started_at=_now(),
                stopped_at=None,
                returncode=None,
            )
            self._states[name] = state
            wrapped = with_ros_setup(command)
            await self._append(state, f"$ {command}")
            process = await asyncio.create_subprocess_exec(
                "bash",
                "-lc",
                wrapped,
                cwd=REPO_ROOT,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                preexec_fn=os.setsid,
            )
            state.process = process
            asyncio.create_task(self._read_output(state))
            asyncio.create_task(self._wait_for_exit(state))
            return {"ok": True, "message": f"started {name}", "state": state.snapshot()}

    async def run_once(self, name: str, command: str, timeout: float = 20.0, use_ros_setup: bool = True) -> dict:
        state = ProcessState(name=name, command=command, started_at=_now())
        self._states[name] = state
        await self._append(state, f"$ {command}")
        wrapped = with_ros_setup(command) if use_ros_setup else without_ros_setup(command)
        process = await asyncio.create_subprocess_exec(
            "bash",
            "-lc",
            wrapped,
            cwd=REPO_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
        state.process = process
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            await self.stop(name)
            return {"ok": False, "message": f"{name} timed out after {timeout:.0f}s", "state": state.snapshot()}

        text = output.decode(errors="replace")
        for line in text.splitlines():
            await self._append(state, line)
        state.returncode = process.returncode
        state.stopped_at = _now()
        ok = process.returncode == 0
        return {
            "ok": ok,
            "message": f"{name} completed" if ok else f"{name} failed with code {process.returncode}",
            "state": state.snapshot(),
        }

    async def stop(self, name: str) -> dict:
        async with self._lock:
            state = self._states.get(name)
            if not state or not state.process:
                return {"ok": False, "message": f"{name} has not been started"}
            if not state.running:
                return {"ok": True, "message": f"{name} is already stopped", "state": state.snapshot()}

            await self._append(state, f"stopping {name}")
            assert state.process.pid is not None
            os.killpg(os.getpgid(state.process.pid), signal.SIGTERM)
            try:
                await asyncio.wait_for(state.process.wait(), timeout=8.0)
            except asyncio.TimeoutError:
                await self._append(state, f"force stopping {name}")
                os.killpg(os.getpgid(state.process.pid), signal.SIGKILL)
                await state.process.wait()

            state.returncode = state.process.returncode
            state.stopped_at = _now()
            return {"ok": True, "message": f"stopped {name}", "state": state.snapshot()}

    async def stop_all(self) -> None:
        for name in list(self._states):
            await self.stop(name)

    async def _read_output(self, state: ProcessState) -> None:
        if not state.process or not state.process.stdout:
            return
        while True:
            line = await state.process.stdout.readline()
            if not line:
                break
            await self._append(state, line.decode(errors="replace").rstrip())

    async def _wait_for_exit(self, state: ProcessState) -> None:
        if not state.process:
            return
        await state.process.wait()
        state.returncode = state.process.returncode
        state.stopped_at = _now()
        await self._append(state, f"{state.name} exited with code {state.returncode}")

    async def _append(self, state: ProcessState, message: str) -> None:
        line = f"{_now()} [{state.name}] {message}"
        state.log.append(line)
        stale: list[asyncio.Queue[str]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(line)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            self.unsubscribe(queue)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
