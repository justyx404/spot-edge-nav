from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .process_manager import ProcessManager
from .stack_config import (
    LIO_COMMANDS,
    MANAGED_COMMANDS,
    PLANNER_COMMANDS,
    REPO_ROOT,
    command_for,
)


manager = ProcessManager()
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await manager.stop_all()


app = FastAPI(title="Spot Edge Operator Console", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class StartRequest(BaseModel):
    profile: str | None = None
    mode: str | None = None


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def status():
    return {
        "repo_root": str(REPO_ROOT),
        "processes": manager.status(),
        "profiles": {
            "localization": list(LIO_COMMANDS),
            "planner": list(PLANNER_COMMANDS),
        },
    }


@app.get("/api/commands")
async def commands():
    return {
        name: {"command": cmd.command, "description": cmd.description}
        for name, cmd in MANAGED_COMMANDS.items()
    }


@app.get("/api/logs")
async def logs(name: str | None = None):
    return {"logs": manager.logs(name)}


@app.post("/api/imu/configure")
async def configure_imu():
    return await manager.run_once(
        "configure_imu",
        "python3 -u src/wit_ros2_imu/configure_imu.py",
        timeout=30.0,
        use_ros_setup=False,
    )


@app.post("/api/imu/test")
async def test_imu():
    return await manager.run_once(
        "test_imu",
        "python3 -u -m operator_console.app.imu_test --port /dev/imu_usb --baud 115200 --duration 2.0",
        timeout=8.0,
        use_ros_setup=False,
    )


@app.post("/api/{name}/start")
async def start_process(name: str, request: StartRequest | None = None):
    if name not in MANAGED_COMMANDS:
        raise HTTPException(status_code=404, detail=f"unknown process: {name}")
    profile = request.profile if request else None
    mode = request.mode if request else None
    try:
        command = command_for(name, profile=profile, mode=mode)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"invalid profile or mode: {exc}") from exc
    return await manager.start(name, command)


@app.post("/api/{name}/stop")
async def stop_process(name: str):
    if name not in MANAGED_COMMANDS and name != "configure_imu":
        raise HTTPException(status_code=404, detail=f"unknown process: {name}")
    return await manager.stop(name)


@app.post("/api/stack/navigation/start")
async def start_navigation(request: StartRequest | None = None):
    profile = request.profile if request else "microgrid"
    results = []
    results.append(await manager.start("localization", command_for("localization", profile=profile)))
    results.append(await manager.start("planner", command_for("planner", profile=profile)))
    results.append(await manager.start("route_manager", command_for("route_manager")))
    return {"ok": all(result["ok"] for result in results), "results": results}


@app.post("/api/stack/navigation/stop")
async def stop_navigation():
    results = []
    for name in ("route_manager", "planner", "localization"):
        results.append(await manager.stop(name))
    return {"ok": True, "results": results}


@app.websocket("/api/logs/ws")
async def logs_ws(websocket: WebSocket):
    await websocket.accept()
    for line in manager.logs():
        await websocket.send_text(line)
    queue = await manager.subscribe()
    try:
        while True:
            await websocket.send_text(await queue.get())
    except WebSocketDisconnect:
        manager.unsubscribe(queue)
