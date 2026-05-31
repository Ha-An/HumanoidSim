from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .catalog import find_project_root, load_task_catalog
from .incident_schema import load_incident_schema
from .interactive_trace import InteractiveTraceConfig, InteractiveTraceResult, run_incident_trace, run_task_trace


@dataclass
class LabUiConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    ros_enabled: bool = False
    gazebo_enabled: bool = False
    wsl_distro: str = "Ubuntu-24.04"
    open_browser: bool = True
    out_dir: Path | None = None


class LabUiRuntime:
    def __init__(self, config: LabUiConfig, *, root: Path | str | None = None) -> None:
        self.root = find_project_root(root)
        self.config = config
        self.catalog = load_task_catalog(self.root, validate=True)
        self.incident_schema = load_incident_schema(self.root)
        self.output_dir = config.out_dir or self.root / "outputs" / "interactive_lab" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, dict[str, Any]] = {}
        self.rviz_process: subprocess.Popen[str] | None = None
        self.gazebo_process: subprocess.Popen[str] | None = None

    def catalog_payload(self) -> dict[str, Any]:
        return {
            "tasks": [
                {
                    "code": spec.code,
                    "name": spec.name,
                    "level": spec.level.value,
                    "category": spec.metadata.get("catalog", {}).get("category", ""),
                    "inputs": [
                        {
                            "name": row.name,
                            "type_hint": row.type_hint,
                            "required": row.required,
                            "description": row.description,
                            "default": row.default,
                            "unit": row.unit,
                            "allowed_values": row.allowed_values,
                        }
                        for row in spec.inputs
                    ],
                }
                for spec in sorted(self.catalog.tasks.values(), key=lambda item: item.code)
            ],
            "incidents": [
                {
                    "code": profile.code,
                    "category": profile.category,
                    "severity": profile.severity,
                    "default_availability": profile.default_availability.value,
                    "description": profile.description,
                    "recovery_protocol": [step.to_dict() for step in profile.recovery_protocol],
                }
                for profile in sorted(self.incident_schema.incidents.values(), key=lambda item: item.code)
            ],
            "ros_enabled": self.config.ros_enabled,
            "gazebo_enabled": self.config.gazebo_enabled,
            "output_dir": str(self.output_dir),
        }

    def run_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_code = str(payload.get("task_code") or "").strip().upper()
        humanoid_id = str(payload.get("humanoid_id") or "LAB-H1").strip() or "LAB-H1"
        args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
        instance_id = str(payload.get("instance_id") or f"LAB-{task_code}-{int(time.time() * 1000)}")
        trace = run_task_trace(
            task_code,
            args,
            humanoid_id=humanoid_id,
            instance_id=instance_id,
            catalog=self.catalog,
            config=InteractiveTraceConfig(humanoid_id=humanoid_id, task_instance_id=instance_id),
        )
        return self._store_trace(trace)

    def run_incident(self, payload: dict[str, Any]) -> dict[str, Any]:
        incident_code = str(payload.get("incident_code") or "").strip().upper()
        humanoid_id = str(payload.get("humanoid_id") or "LAB-H1").strip() or "LAB-H1"
        context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
        trace = run_incident_trace(incident_code, context, humanoid_id=humanoid_id, catalog=self.catalog, incident_schema=self.incident_schema)
        return self._store_trace(trace)

    def session(self, session_id: str) -> dict[str, Any] | None:
        return self.sessions.get(session_id)

    def launch_rviz(self) -> dict[str, Any]:
        if not self.config.ros_enabled:
            return {"ok": False, "message": "ROS controls are disabled. Start with --ros."}
        if self.rviz_process and self.rviz_process.poll() is None:
            return {"ok": True, "message": "RViz launch is already running."}
        command = _wsl_ros_command(
            self.root,
            "ros2 launch humanoidsim_ros rviz_validation.launch.py",
        )
        try:
            self.rviz_process = subprocess.Popen(
                ["wsl", "-d", self.config.wsl_distro, "--", "bash", "-lc", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except Exception as exc:  # noqa: BLE001 - surface OS process failures to UI.
            return {"ok": False, "message": str(exc)}
        return {"ok": True, "message": "RViz launch requested."}

    def launch_gazebo(self) -> dict[str, Any]:
        if not self.config.gazebo_enabled:
            return {"ok": False, "message": "Gazebo controls are disabled. Start with --gazebo."}
        if self.gazebo_process and self.gazebo_process.poll() is None:
            return {"ok": True, "message": "Gazebo physics validation launch is already running."}
        self.gazebo_process = launch_gazebo_validation(self.root, self.config.wsl_distro)
        return {"ok": True, "message": "Gazebo physics validation launch requested."}

    def play_trace(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.config.ros_enabled:
            return {"ok": False, "message": "ROS controls are disabled. Start with --ros."}
        session_id = str(payload.get("session_id") or "")
        speed = float(payload.get("speed") or 1.0)
        session = self.sessions.get(session_id)
        if not session:
            return {"ok": False, "message": f"Unknown session: {session_id}"}
        trace_path = Path(session["trace_path"])
        command = _wsl_ros_command(
            self.root,
            f"ros2 run humanoidsim_ros play_trace_file --file '{_wsl_path(trace_path)}' --speed {speed}",
        )
        try:
            completed = subprocess.run(
                ["wsl", "-d", self.config.wsl_distro, "--", "bash", "-lc", command],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": str(exc)}
        return {
            "ok": completed.returncode == 0,
            "message": (completed.stdout or completed.stderr or "").strip() or f"ros2 exited with {completed.returncode}",
            "returncode": completed.returncode,
        }

    def _store_trace(self, trace: InteractiveTraceResult) -> dict[str, Any]:
        session_id = trace.session_id
        trace_dir = self.output_dir / session_id
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / "trace.json"
        trace_path.write_text(json.dumps(trace.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        session = trace.to_dict()
        session["trace_path"] = str(trace_path)
        self.sessions[session_id] = session
        return session


def run_lab_ui(config: LabUiConfig | None = None, *, root: Path | str | None = None) -> None:
    cfg = config or LabUiConfig()
    runtime = LabUiRuntime(cfg, root=root)
    server = ThreadingHTTPServer((cfg.host, cfg.port), _handler(runtime))
    url = f"http://{cfg.host}:{cfg.port}/"
    print(f"HumanoidSim interactive validation UI: {url}")
    print(f"Output directory: {runtime.output_dir}")
    if cfg.open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _handler(runtime: LabUiRuntime):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html(_HTML)
                return
            if parsed.path == "/api/catalog":
                self._send_json(runtime.catalog_payload())
                return
            if parsed.path.startswith("/api/session/"):
                session_id = parsed.path.rsplit("/", 1)[-1]
                session = runtime.session(session_id)
                if session is None:
                    self._send_json({"ok": False, "message": "session not found"}, HTTPStatus.NOT_FOUND)
                else:
                    self._send_json(session)
                return
            self._send_json({"ok": False, "message": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            payload = self._read_json()
            try:
                if parsed.path == "/api/run-task":
                    self._send_json(runtime.run_task(payload))
                    return
                if parsed.path == "/api/run-incident":
                    self._send_json(runtime.run_incident(payload))
                    return
                if parsed.path == "/api/ros/launch-rviz":
                    self._send_json(runtime.launch_rviz())
                    return
                if parsed.path == "/api/ros/play-trace":
                    self._send_json(runtime.play_trace(payload))
                    return
                if parsed.path == "/api/ros/launch-gazebo":
                    self._send_json(runtime.launch_gazebo())
                    return
            except Exception as exc:  # noqa: BLE001 - UI should display errors.
                self._send_json({"ok": False, "message": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"ok": False, "message": "not found"}, HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            sys.stdout.write("%s - %s\n" % (self.address_string(), format % args))

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            data = json.loads(raw or "{}")
            return data if isinstance(data, dict) else {}

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, payload: str) -> None:
            body = payload.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    suffix = str(resolved)[3:].replace("\\", "/")
    return f"/mnt/{drive}/{suffix}"


def _wsl_ros_command(root: Path, command: str) -> str:
    ros_ws = _wsl_path(root / "integrations" / "ros2" / "ros2_ws")
    humanoidsim_src = _wsl_path(root / "src")
    return (
        f"cd '{ros_ws}' && "
        "source /opt/ros/jazzy/setup.bash && "
        "source install/setup.bash && "
        f"export PYTHONPATH='{humanoidsim_src}':'{ros_ws}/install/humanoidsim_ros/lib/python3.12/site-packages':"
        f"'{ros_ws}/install/humanoidsim_ros_interfaces/lib/python3.12/site-packages':"
        "/opt/ros/jazzy/lib/python3.12/site-packages:${PYTHONPATH:-} && "
        f"{command}"
    )


def launch_gazebo_validation(root: Path | str | None = None, wsl_distro: str = "Ubuntu-24.04") -> subprocess.Popen[str]:
    project_root = find_project_root(root)
    command = _wsl_ros_command(project_root, "ros2 launch humanoidsim_ros gazebo_physics_validation.launch.py")
    return subprocess.Popen(
        ["wsl", "-d", wsl_distro, "--", "bash", "-lc", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


_HTML = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>HumanoidSim Interactive Validation Lab</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, Segoe UI, Arial, sans-serif; background: #0f172a; color: #e5edf8; }
    body { margin: 0; }
    header { padding: 18px 22px; border-bottom: 1px solid #23314a; background: #111827; }
    h1 { margin: 0; font-size: 22px; }
    main {
      display: grid;
      grid-template-columns: 340px minmax(620px, 1fr) 420px;
      grid-template-areas:
        "input viewer detail";
      gap: 14px;
      padding: 14px;
      align-items: start;
    }
    section { background: #111827; border: 1px solid #2d3f5f; border-radius: 8px; overflow: hidden; }
    .inputPanel { grid-area: input; }
    .viewerPanel { grid-area: viewer; }
    .detailPanel { grid-area: detail; }
    h2 { margin: 0; padding: 12px 14px; font-size: 14px; color: #93c5fd; border-bottom: 1px solid #2d3f5f; text-transform: uppercase; letter-spacing: .08em; }
    .panel { padding: 14px; display: grid; gap: 12px; }
    label { display: grid; gap: 6px; color: #b6c7e4; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
    select, input, textarea, button { border: 1px solid #385070; background: #0b1220; color: #f8fbff; border-radius: 6px; padding: 9px 10px; font: inherit; }
    textarea { min-height: 120px; resize: vertical; font-family: Consolas, monospace; }
    button { cursor: pointer; background: #17345d; }
    button.primary { background: #1e60a8; border-color: #5ba7f6; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .row.three { grid-template-columns: 1fr; }
    .row.three button { width: 100%; min-width: 0; white-space: normal; overflow-wrap: anywhere; }
    #launchGazebo { grid-column: auto; }
    .viewerWrap { padding: 12px; display: grid; gap: 10px; }
    .viewerStage { position: relative; }
    #viewer3d { width: 100%; height: 480px; border-radius: 8px; border: 1px solid #2d3f5f; background: linear-gradient(#172235, #07101f); display: block; touch-action: none; }
    .viewerHud { position: absolute; left: 12px; top: 12px; padding: 8px 10px; border: 1px solid rgba(96, 165, 250, .28); border-radius: 7px; background: rgba(8, 13, 25, .72); color: #c7d9f5; font-family: Consolas, monospace; font-size: 12px; pointer-events: none; }
    .viewerControls { display: grid; grid-template-columns: 96px 1fr 80px; gap: 8px; align-items: center; }
    .cameraControls { display: grid; grid-template-columns: repeat(3, minmax(96px, 1fr)) 160px; gap: 8px; align-items: center; }
    .cameraReadout { color: #94a9c9; font-size: 12px; font-family: Consolas, monospace; text-align: right; }
    #viewerSeek { width: 100%; }
    .viewerHint { color: #94a9c9; font-size: 12px; }
    .timeline { max-height: 640px; overflow: auto; display: grid; gap: 8px; padding: 12px; }
    .event { border: 1px solid #2d3f5f; border-radius: 7px; padding: 9px; background: #0d1626; display: grid; grid-template-columns: 72px 1fr auto; gap: 10px; align-items: center; }
    .event.active { border-color: #60a5fa; background: #102543; }
    .code { font-family: Consolas, monospace; font-weight: 700; color: #e8f3ff; }
    .sub { font-size: 12px; color: #91a6c7; margin-top: 3px; }
    .badge { border: 1px solid #395476; border-radius: 999px; padding: 4px 8px; color: #9dd7ff; font-size: 12px; }
    .stateGrid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .stateBox { background: #0b1220; border: 1px solid #2d3f5f; border-radius: 7px; padding: 10px; }
    .stateBox span { display: block; color: #8aa1c4; font-size: 11px; text-transform: uppercase; }
    .stateBox strong { display: block; margin-top: 6px; font-family: Consolas, monospace; }
    pre { white-space: pre-wrap; word-break: break-word; margin: 0; font-size: 12px; max-height: 420px; overflow: auto; }
    .status { padding: 10px 14px; border-top: 1px solid #2d3f5f; color: #9fb5d7; }
    @media (max-width: 1100px) {
      main { grid-template-columns: 1fr; grid-template-areas: "input" "viewer" "detail"; }
    }
  </style>
</head>
<body>
  <header><h1>HumanoidSim Interactive Validation Lab</h1></header>
  <main>
    <section class="inputPanel">
      <h2>Input</h2>
      <div class="panel">
        <label>Mode
          <select id="mode"><option value="task">Task</option><option value="incident">Incident</option></select>
        </label>
        <label id="taskCategoryLabel">Task Category
          <select id="taskCategory"></select>
        </label>
        <label id="taskLabel">Task
          <select id="task"></select>
        </label>
        <label id="incidentLabel" style="display:none">Incident
          <select id="incident"></select>
        </label>
        <div class="row">
          <label>Humanoid ID <input id="humanoid" value="LAB-H1" /></label>
          <label>Speed <input id="speed" value="1.0" /></label>
        </div>
        <label>Args / Context JSON
          <textarea id="json">{}</textarea>
        </label>
        <button class="primary" id="run">Run</button>
        <div class="row three">
          <button id="launchRviz">Launch RViz</button>
          <button id="playRviz">Play in RViz</button>
          <button id="launchGazebo">Launch Gazebo</button>
        </div>
      </div>
      <div class="status" id="status">Loading catalog...</div>
    </section>
    <section class="viewerPanel">
      <h2>Browser 3D Viewer</h2>
      <div class="viewerWrap">
        <div class="viewerStage">
          <canvas id="viewer3d" width="960" height="480"></canvas>
          <div class="viewerHud" id="viewerHud">Run a trace to preview motion</div>
        </div>
        <div class="viewerControls">
          <button id="viewerPlay">Play</button>
          <input id="viewerSeek" type="range" min="0" max="0" step="0.05" value="0" />
          <div class="viewerHint" id="viewerTime">0.0s</div>
        </div>
        <div class="cameraControls">
          <button id="viewerReset">Reset View</button>
          <button id="viewerZoomIn">Zoom +</button>
          <button id="viewerZoomOut">Zoom -</button>
          <div class="cameraReadout" id="viewerCamera">zoom 1.00 / yaw -43° / pitch 36°</div>
        </div>
        <div class="stateGrid" id="stateGrid"></div>
      </div>
    </section>
    <section class="detailPanel">
      <h2>Step Timeline</h2>
      <div class="panel">
        <div>
          <h3>Step Timeline</h3>
          <div class="timeline" id="timeline"></div>
        </div>
        <div>
          <h3>Issues</h3>
          <pre id="issues">[]</pre>
        </div>
      </div>
    </section>
  </main>
  <script>
    let catalog = null;
    let current = null;
    let selected = 0;
    let viewerPlaying = false;
    let viewerTime = 0;
    let lastFrameMs = null;
    const defaultViewerCamera = { yaw: -0.75, pitch: 0.62, zoom: 1, panX: 0, panY: 0 };
    let viewerCamera = { ...defaultViewerCamera };
    let viewerDrag = null;
    let webglViewer = null;
    const $ = (id) => document.getElementById(id);
    const status = (text) => $("status").textContent = text;

    async function api(path, body) {
      const response = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
      return await response.json();
    }
    function parseJson() {
      try { return JSON.parse($("json").value || "{}"); }
      catch (err) { throw new Error("JSON parse error: " + err.message); }
    }
    function taskCategoryName(task) {
      return task.category || "Uncategorized";
    }
    function fillTaskOptions() {
      const category = $("taskCategory").value;
      const tasks = catalog.tasks.filter(task => taskCategoryName(task) === category);
      $("task").innerHTML = tasks.map(t => `<option value="${t.code}">${t.code} - ${t.name}</option>`).join("");
    }
    function fillCatalog() {
      const categories = [...new Set(catalog.tasks.map(taskCategoryName))].sort();
      $("taskCategory").innerHTML = categories.map(category => `<option value="${category}">${category}</option>`).join("");
      fillTaskOptions();
      $("incident").innerHTML = catalog.incidents.map(i => `<option value="${i.code}">${i.code} - ${i.category}</option>`).join("");
      $("launchRviz").style.display = catalog.ros_enabled ? "" : "none";
      $("playRviz").style.display = catalog.ros_enabled ? "" : "none";
      $("launchGazebo").style.display = catalog.gazebo_enabled ? "" : "none";
      status(`Ready. Output: ${catalog.output_dir}`);
    }
    function modeChanged() {
      const taskMode = $("mode").value === "task";
      $("taskCategoryLabel").style.display = taskMode ? "" : "none";
      $("taskLabel").style.display = taskMode ? "" : "none";
      $("incidentLabel").style.display = taskMode ? "none" : "";
    }
    function render() {
      if (!current) return;
      const rows = timelineRows();
      $("timeline").innerHTML = rows.map(({ event, index }) => `
        <div class="event ${index === selected ? "active" : ""}" data-index="${index}" onclick="selectEvent(${index})">
          <div>${Number(event.time_s || 0).toFixed(1)}s</div>
          <div><div class="code">${event.display_code || event.kind}</div><div class="sub">${event.task_code || "-"} / ${timelineKindLabel(event.kind)}</div></div>
          <div class="badge">${event.is_recovery ? "RECOVERY" : "NORMAL"}</div>
        </div>`).join("");
      renderSelected();
      $("issues").textContent = JSON.stringify(current.issues || [], null, 2);
      setupViewer();
      drawViewer();
    }
    function timelineRows() {
      return (current?.events || [])
        .map((event, index) => ({ event, index }))
        .filter(({ event }) => isTimelineVisible(event));
    }
    function isTimelineVisible(event) {
      // Keep start/end events in the trace for validation, but show each primitive once in the UI.
      const kind = String(event?.kind || "");
      if (kind === "primitive_finished" || kind === "recovery_primitive_finished") return false;
      if (kind === "task_started") return false;
      return true;
    }
    function timelineKindLabel(kind) {
      if (kind === "primitive_started") return "primitive";
      if (kind === "recovery_primitive_started") return "recovery primitive";
      if (kind === "task_boundary") return "child task";
      if (kind === "recovery_task_boundary") return "recovery task";
      return kind;
    }
    function renderSelected() {
      const event = (current.events || [])[selected] || {};
      const state = event.state_after || {};
      $("stateGrid").innerHTML = ["availability","mobility","power","manipulation"].map(axis => `
        <div class="stateBox"><span>${axis}</span><strong>${state[axis] || "-"}</strong></div>`).join("");
    }
    function traceDuration() {
      if (!current) return 0;
      return Math.max(0, ...(current.events || []).map(event => Number(event.time_s || 0) + Number(event.duration_s || 0)));
    }
    function eventIndexAt(time) {
      const events = current?.events || [];
      let index = 0;
      for (let i = 0; i < events.length; i += 1) {
        const event = events[i];
        const start = Number(event.time_s || 0);
        const duration = Math.max(0, Number(event.duration_s || 0));
        if (time >= start) index = i;
        if (duration > 0 && time >= start && time <= start + duration) return i;
      }
      return index;
    }
    function visibleEventIndexAt(time) {
      const events = current?.events || [];
      let index = eventIndexAt(time);
      if (isTimelineVisible(events[index])) return index;
      for (let i = index; i >= 0; i -= 1) {
        if (isTimelineVisible(events[i])) return i;
      }
      for (let i = index + 1; i < events.length; i += 1) {
        if (isTimelineVisible(events[i])) return i;
      }
      return index;
    }
    function syncTimelineToTime(time, shouldScroll = false) {
      if (!current) return;
      const next = visibleEventIndexAt(time);
      if (next !== selected) {
        selected = next;
        renderSelected();
      }
      document.querySelectorAll(".event").forEach(node => {
        node.classList.toggle("active", Number(node.dataset.index) === selected);
      });
      if (shouldScroll) {
        const active = document.querySelector(`.event[data-index="${selected}"]`);
        if (active) active.scrollIntoView({ block: "nearest" });
      }
    }
    function setupViewer() {
      const duration = traceDuration();
      $("viewerSeek").max = String(duration || 0);
      if (viewerTime > duration || viewerTime === 0) viewerTime = 0;
      $("viewerSeek").value = String(viewerTime);
      $("viewerTime").textContent = `${viewerTime.toFixed(1)}s / ${duration.toFixed(1)}s`;
    }
    function currentEventAt(time) {
      const events = current?.events || [];
      let active = events[0] || null;
      for (const event of events) {
        const start = Number(event.time_s || 0);
        const duration = Math.max(0, Number(event.duration_s || 0));
        if (time >= start) active = event;
        if (duration > 0 && time >= start && time <= start + duration) return event;
      }
      return active;
    }
    function poseAt(time) {
      const pose = { x: 0, y: 0, yaw: 0, event: currentEventAt(time), progress: 0 };
      for (const event of current?.events || []) {
        const start = Number(event.time_s || 0);
        const duration = Math.max(0, Number(event.duration_s || 0));
        const motion = event.motion_hint || {};
        const apply = (ratio) => {
          if (motion.type === "translate") {
            const heading = Number(motion.heading_rad ?? pose.yaw);
            const distance = Number(motion.distance_m || 0) * ratio;
            pose.x += Math.cos(heading) * distance;
            pose.y += Math.sin(heading) * distance;
            pose.yaw = heading;
          } else if (motion.type === "rotate") {
            pose.yaw += Number(motion.angle_rad || 0) * ratio;
          }
        };
        if (duration <= 0) continue;
        if (time >= start + duration) {
          apply(1);
        } else if (time >= start) {
          const ratio = Math.max(0, Math.min(1, (time - start) / duration));
          apply(ratio);
          pose.event = event;
          pose.progress = ratio;
          break;
        }
      }
      return pose;
    }
    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }
    function vec3(x, y, z) { return [x, y, z]; }
    function normalize(v) {
      const len = Math.hypot(v[0], v[1], v[2]) || 1;
      return [v[0] / len, v[1] / len, v[2] / len];
    }
    function cross(a, b) {
      return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    }
    function subtract(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
    function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
    function m4Multiply(a, b) {
      const out = new Float32Array(16);
      for (let col = 0; col < 4; col += 1) {
        for (let row = 0; row < 4; row += 1) {
          out[col * 4 + row] =
            a[0 * 4 + row] * b[col * 4 + 0] +
            a[1 * 4 + row] * b[col * 4 + 1] +
            a[2 * 4 + row] * b[col * 4 + 2] +
            a[3 * 4 + row] * b[col * 4 + 3];
        }
      }
      return out;
    }
    function m4Perspective(fovy, aspect, near, far) {
      const f = 1 / Math.tan(fovy / 2);
      const nf = 1 / (near - far);
      return new Float32Array([
        f / aspect, 0, 0, 0,
        0, f, 0, 0,
        0, 0, (far + near) * nf, -1,
        0, 0, (2 * far * near) * nf, 0,
      ]);
    }
    function m4LookAt(eye, target, up) {
      const z = normalize(subtract(eye, target));
      const x = normalize(cross(up, z));
      const y = cross(z, x);
      return new Float32Array([
        x[0], y[0], z[0], 0,
        x[1], y[1], z[1], 0,
        x[2], y[2], z[2], 0,
        -dot(x, eye), -dot(y, eye), -dot(z, eye), 1,
      ]);
    }
    function m4Model(x, y, z, sx, sy, sz, yaw = 0) {
      const c = Math.cos(yaw);
      const s = Math.sin(yaw);
      return new Float32Array([
        c * sx, 0, -s * sx, 0,
        0, sy, 0, 0,
        s * sz, 0, c * sz, 0,
        x, y, z, 1,
      ]);
    }
    function m4ModelTilt(x, y, z, sx, sy, sz, yaw = 0, pitch = 0) {
      const cy = Math.cos(yaw);
      const syaw = Math.sin(yaw);
      const cp = Math.cos(pitch);
      const sp = Math.sin(pitch);
      return new Float32Array([
        cy * sx, 0, -syaw * sx, 0,
        syaw * sp * sy, cp * sy, cy * sp * sy, 0,
        syaw * cp * sz, -sp * sz, cy * cp * sz, 0,
        x, y, z, 1,
      ]);
    }
    function colorRgb(hex) {
      const value = hex.replace("#", "");
      return [
        parseInt(value.slice(0, 2), 16) / 255,
        parseInt(value.slice(2, 4), 16) / 255,
        parseInt(value.slice(4, 6), 16) / 255,
      ];
    }
    function initWebGLViewer(canvas) {
      // The browser viewer is dependency-free on purpose; RViz remains the ROS-grounded comparison view.
      const gl = canvas.getContext("webgl", { antialias: true, alpha: false });
      if (!gl) return null;
      const vertexShader = compileShader(gl, gl.VERTEX_SHADER, `
        attribute vec3 aPosition;
        attribute vec3 aNormal;
        uniform mat4 uViewProjection;
        uniform mat4 uModel;
        uniform vec3 uColor;
        uniform vec3 uLightDir;
        varying vec3 vColor;
        void main() {
          vec3 normal = normalize(mat3(uModel) * aNormal);
          float light = max(dot(normal, normalize(uLightDir)), 0.0) * 0.55 + 0.32;
          vColor = uColor * light + vec3(0.06, 0.08, 0.12);
          gl_Position = uViewProjection * uModel * vec4(aPosition, 1.0);
        }
      `);
      const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, `
        precision mediump float;
        varying vec3 vColor;
        void main() { gl_FragColor = vec4(vColor, 1.0); }
      `);
      const program = gl.createProgram();
      gl.attachShader(program, vertexShader);
      gl.attachShader(program, fragmentShader);
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
      const vertices = new Float32Array([
        -0.5,-0.5, 0.5, 0,0,1, 0.5,-0.5, 0.5, 0,0,1, 0.5,0.5,0.5,0,0,1, -0.5,-0.5,0.5,0,0,1, 0.5,0.5,0.5,0,0,1, -0.5,0.5,0.5,0,0,1,
        0.5,-0.5,-0.5, 0,0,-1, -0.5,-0.5,-0.5,0,0,-1, -0.5,0.5,-0.5,0,0,-1, 0.5,-0.5,-0.5,0,0,-1, -0.5,0.5,-0.5,0,0,-1, 0.5,0.5,-0.5,0,0,-1,
        -0.5,0.5,0.5, 0,1,0, 0.5,0.5,0.5,0,1,0, 0.5,0.5,-0.5,0,1,0, -0.5,0.5,0.5,0,1,0, 0.5,0.5,-0.5,0,1,0, -0.5,0.5,-0.5,0,1,0,
        -0.5,-0.5,-0.5, 0,-1,0, 0.5,-0.5,-0.5,0,-1,0, 0.5,-0.5,0.5,0,-1,0, -0.5,-0.5,-0.5,0,-1,0, 0.5,-0.5,0.5,0,-1,0, -0.5,-0.5,0.5,0,-1,0,
        0.5,-0.5,0.5, 1,0,0, 0.5,-0.5,-0.5,1,0,0, 0.5,0.5,-0.5,1,0,0, 0.5,-0.5,0.5,1,0,0, 0.5,0.5,-0.5,1,0,0, 0.5,0.5,0.5,1,0,0,
        -0.5,-0.5,-0.5, -1,0,0, -0.5,-0.5,0.5,-1,0,0, -0.5,0.5,0.5,-1,0,0, -0.5,-0.5,-0.5,-1,0,0, -0.5,0.5,0.5,-1,0,0, -0.5,0.5,-0.5,-1,0,0,
      ]);
      const buffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
      return {
        gl, program, buffer,
        aPosition: gl.getAttribLocation(program, "aPosition"),
        aNormal: gl.getAttribLocation(program, "aNormal"),
        uViewProjection: gl.getUniformLocation(program, "uViewProjection"),
        uModel: gl.getUniformLocation(program, "uModel"),
        uColor: gl.getUniformLocation(program, "uColor"),
        uLightDir: gl.getUniformLocation(program, "uLightDir"),
      };
    }
    function compileShader(gl, type, source) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.warn(gl.getShaderInfoLog(shader));
      }
      return shader;
    }
    function drawCube3D(state, x, y, z, sx, sy, sz, color, yaw = 0) {
      const { gl } = state;
      gl.uniformMatrix4fv(state.uModel, false, m4Model(x, y, z, sx, sy, sz, yaw));
      gl.uniform3fv(state.uColor, new Float32Array(colorRgb(color)));
      gl.drawArrays(gl.TRIANGLES, 0, 36);
    }
    function drawTiltedCube3D(state, x, y, z, sx, sy, sz, color, yaw = 0, pitch = 0) {
      const { gl } = state;
      gl.uniformMatrix4fv(state.uModel, false, m4ModelTilt(x, y, z, sx, sy, sz, yaw, pitch));
      gl.uniform3fv(state.uColor, new Float32Array(colorRgb(color)));
      gl.drawArrays(gl.TRIANGLES, 0, 36);
    }
    function drawLocalCube3D(state, pose, lx, ly, lz, sx, sy, sz, color, extraYaw = 0) {
      const yaw = pose.yaw + extraYaw;
      const c = Math.cos(pose.yaw);
      const s = Math.sin(pose.yaw);
      const x = pose.x + lx * c - lz * s;
      const z = pose.y + lx * s + lz * c;
      drawCube3D(state, x, ly, z, sx, sy, sz, color, yaw);
    }
    function localPoint3D(pose, lx, ly, lz) {
      const c = Math.cos(pose.yaw);
      const s = Math.sin(pose.yaw);
      return [pose.x + lx * c - lz * s, ly, pose.y + lx * s + lz * c];
    }
    function drawLimbSegment3D(state, pose, anchorLocal, length, width, color, pitch) {
      const anchor = localPoint3D(pose, anchorLocal[0], anchorLocal[1], anchorLocal[2]);
      const yaw = pose.yaw;
      const syaw = Math.sin(yaw);
      const cyaw = Math.cos(yaw);
      const sp = Math.sin(pitch);
      const cp = Math.cos(pitch);
      const axisY = [syaw * sp, cp, cyaw * sp];
      const center = [
        anchor[0] - axisY[0] * length * 0.5,
        anchor[1] - axisY[1] * length * 0.5,
        anchor[2] - axisY[2] * length * 0.5,
      ];
      drawTiltedCube3D(state, center[0], center[1], center[2], width, length, width, color, yaw, pitch);
      return [
        anchor[0] - axisY[0] * length,
        anchor[1] - axisY[1] * length,
        anchor[2] - axisY[2] * length,
      ];
    }
    function drawJoint3D(state, point, size, color, yaw = 0) {
      drawCube3D(state, point[0], point[1], point[2], size, size, size, color, yaw);
    }
    function drawTracePath3D(state) {
      if (!current) return;
      const duration = traceDuration();
      const step = Math.max(0.2, duration / 80);
      for (let t = 0; t <= duration + 0.001; t += step) {
        const pose = poseAt(t);
        const active = t <= viewerTime + 0.001;
        drawCube3D(state, pose.x, 0.035, pose.y, active ? 0.12 : 0.07, 0.035, active ? 0.12 : 0.07, active ? "#60a5fa" : "#25415f");
      }
    }
    function drawProgressBase3D(state, pose) {
      const progress = clamp(Number(pose.progress || 0), 0, 1);
      drawLocalCube3D(state, pose, 0, 0.08, 0.48, 0.86, 0.04, 0.08, "#223954");
      drawLocalCube3D(state, pose, -0.43 + progress * 0.43, 0.105, 0.48, Math.max(0.02, progress * 0.86), 0.05, 0.09, "#7dd3fc");
    }
    function drawRobot3D(state, pose) {
      const event = pose.event || {};
      const primitive = String(event.primitive_call_code || "");
      const manipulation = String(event.manipulation_hint?.type || "");
      const after = event.state_after || {};
      const recovery = Boolean(event.is_recovery);
      const navigating = primitive === "NAVIGATE_TO" || after.mobility === "NAVIGATING";
      const working = Boolean(primitive && primitive !== "NAVIGATE_TO");
      const holding = after.manipulation === "HOLDING" || ["grasp", "lift", "place", "holding"].includes(manipulation);
      const base = recovery ? "#e8793f" : "#7fb4e8";
      const walkCycle = Math.sin(viewerTime * 8);
      const legPitch = navigating ? walkCycle * 0.46 : 0.03;
      const counterLegPitch = navigating ? -walkCycle * 0.46 : -0.03;
      const workCycle = Math.sin(viewerTime * 9);
      const reaching = ["reach_to", "grasp", "lift", "place", "release", "reaching", "placing"].includes(manipulation);
      const leftArmPitch = reaching ? 0.95 + workCycle * 0.10 : (working ? 0.34 + workCycle * 0.18 : 0.12);
      const rightArmPitch = reaching ? 0.95 - workCycle * 0.10 : (working ? 0.34 - workCycle * 0.18 : 0.12);

      // Body parts are anchored at shoulders and hips so motion reads as a connected humanoid.
      drawLocalCube3D(state, pose, 0, 0.015, 0, 0.78, 0.03, 0.56, "#030712");
      drawLocalCube3D(state, pose, 0, 0.84, 0, 0.46, 0.76, 0.30, base);
      drawLocalCube3D(state, pose, 0, 1.24, 0, 0.28, 0.10, 0.24, "#8ba4c0");
      drawLocalCube3D(state, pose, 0, 1.43, 0, 0.34, 0.32, 0.32, "#e6edf5");
      drawLocalCube3D(state, pose, 0, 1.48, -0.18, 0.20, 0.055, 0.04, "#0ea5e9");

      const leftShoulder = [-0.30, 1.17, -0.01];
      const rightShoulder = [0.30, 1.17, -0.01];
      const leftHip = [-0.16, 0.50, 0.02];
      const rightHip = [0.16, 0.50, 0.02];
      drawLocalCube3D(state, pose, -0.30, 1.17, -0.01, 0.16, 0.16, 0.16, "#7d91aa");
      drawLocalCube3D(state, pose, 0.30, 1.17, -0.01, 0.16, 0.16, 0.16, "#7d91aa");
      drawLocalCube3D(state, pose, -0.16, 0.50, 0.02, 0.15, 0.15, 0.15, "#1b2b42");
      drawLocalCube3D(state, pose, 0.16, 0.50, 0.02, 0.15, 0.15, 0.15, "#1b2b42");

      const leftHand = drawLimbSegment3D(state, pose, leftShoulder, 0.55, 0.12, "#9fb2c8", leftArmPitch);
      const rightHand = drawLimbSegment3D(state, pose, rightShoulder, 0.55, 0.12, "#9fb2c8", rightArmPitch);
      drawJoint3D(state, leftHand, 0.11, "#cbd5e1", pose.yaw);
      drawJoint3D(state, rightHand, 0.11, "#cbd5e1", pose.yaw);

      const leftFoot = drawLimbSegment3D(state, pose, leftHip, 0.56, 0.13, "#253750", legPitch);
      const rightFoot = drawLimbSegment3D(state, pose, rightHip, 0.56, 0.13, "#253750", counterLegPitch);
      drawTiltedCube3D(state, leftFoot[0], leftFoot[1] - 0.025, leftFoot[2] - 0.04, 0.22, 0.08, 0.26, "#132033", pose.yaw, legPitch * 0.25);
      drawTiltedCube3D(state, rightFoot[0], rightFoot[1] - 0.025, rightFoot[2] - 0.04, 0.22, 0.08, 0.26, "#132033", pose.yaw, counterLegPitch * 0.25);
      if (holding) {
        const itemColor = event.task_code === "MANAGE_ROBOT_POWER" ? "#22c55e" : "#fbbf24";
        drawLocalCube3D(state, pose, 0, 0.84, -0.58, 0.28, 0.24, 0.28, itemColor);
      }
      drawProgressBase3D(state, pose);
    }
    function drawScene3D(state, pose) {
      drawCube3D(state, 0, -0.04, 0, 18, 0.08, 18, "#1b2a42");
      for (let i = -9; i <= 9; i += 1) {
        const heavy = i === 0 ? "#5b7da8" : "#2e4567";
        drawCube3D(state, i, 0.004, 0, i === 0 ? 0.035 : 0.018, 0.018, 18, heavy);
        drawCube3D(state, 0, 0.004, i, 18, 0.018, i === 0 ? 0.035 : 0.018, heavy);
      }
      drawCube3D(state, 0, 0.10, -2.8, 5.2, 0.20, 0.24, "#376291");
      drawCube3D(state, 2.8, 0.10, 0, 0.24, 0.20, 5.2, "#376291");
      drawCube3D(state, -2.8, 0.06, 2.4, 2.4, 0.12, 1.0, "#72542c");
      drawCube3D(state, -2.8, 0.22, 2.4, 1.8, 0.18, 0.18, "#fbbf24");
      drawCube3D(state, 3.4, 0.05, -3.2, 0.7, 0.1, 0.7, "#2563eb");
      drawTracePath3D(state);
      if (!current) return;
      drawRobot3D(state, pose);
    }
    function drawWebGLViewer(canvas, width, height) {
      webglViewer = webglViewer || initWebGLViewer(canvas);
      if (!webglViewer) return false;
      const state = webglViewer;
      const gl = state.gl;
      const ratio = window.devicePixelRatio || 1;
      if (canvas.width !== Math.floor(width * ratio) || canvas.height !== Math.floor(height * ratio)) {
        canvas.width = Math.floor(width * ratio);
        canvas.height = Math.floor(height * ratio);
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.clearColor(0.035, 0.055, 0.095, 1);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.useProgram(state.program);
      gl.bindBuffer(gl.ARRAY_BUFFER, state.buffer);
      gl.enableVertexAttribArray(state.aPosition);
      gl.enableVertexAttribArray(state.aNormal);
      gl.vertexAttribPointer(state.aPosition, 3, gl.FLOAT, false, 24, 0);
      gl.vertexAttribPointer(state.aNormal, 3, gl.FLOAT, false, 24, 12);
      const target = vec3(-viewerCamera.panX / 80 / viewerCamera.zoom, 0.72, viewerCamera.panY / 80 / viewerCamera.zoom);
      const radius = 7.8 / viewerCamera.zoom;
      const pitch = clamp(viewerCamera.pitch ?? 0.62, 0.18, 1.22);
      const eye = vec3(
        target[0] + Math.sin(viewerCamera.yaw) * Math.cos(pitch) * radius,
        target[1] + Math.sin(pitch) * radius,
        target[2] + Math.cos(viewerCamera.yaw) * Math.cos(pitch) * radius
      );
      const projection = m4Perspective(Math.PI / 4.0, canvas.width / Math.max(1, canvas.height), 0.1, 100);
      const view = m4LookAt(eye, target, vec3(0, 1, 0));
      const vp = m4Multiply(projection, view);
      gl.uniformMatrix4fv(state.uViewProjection, false, vp);
      gl.uniform3fv(state.uLightDir, new Float32Array(normalize(vec3(-0.45, 0.85, 0.35))));
      drawScene3D(state, poseAt(viewerTime));
      return true;
    }
    function project(x, y, z, scale, cx, cy) {
      const cos = Math.cos(viewerCamera.yaw);
      const sin = Math.sin(viewerCamera.yaw);
      const rx = x * cos - y * sin;
      const ry = x * sin + y * cos;
      const cameraScale = scale * viewerCamera.zoom;
      return {
        x: cx + viewerCamera.panX + (rx - ry) * cameraScale,
        y: cy + viewerCamera.panY + (rx + ry) * cameraScale * 0.42 - z * cameraScale,
      };
    }
    function shade(hex, delta) {
      const value = hex.replace("#", "");
      const r = Math.max(0, Math.min(255, parseInt(value.slice(0, 2), 16) + delta));
      const g = Math.max(0, Math.min(255, parseInt(value.slice(2, 4), 16) + delta));
      const b = Math.max(0, Math.min(255, parseInt(value.slice(4, 6), 16) + delta));
      return `rgb(${r},${g},${b})`;
    }
    function poly(ctx, points, fill, stroke = "#0b1220") {
      ctx.beginPath();
      points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    function block(ctx, x, y, z, w, d, h, color, scale, cx, cy) {
      const p = (dx, dy, dz) => project(x + dx, y + dy, z + dz, scale, cx, cy);
      const top = [p(0, 0, h), p(w, 0, h), p(w, d, h), p(0, d, h)];
      const left = [p(0, d, 0), p(0, d, h), p(w, d, h), p(w, d, 0)];
      const right = [p(w, 0, 0), p(w, 0, h), p(w, d, h), p(w, d, 0)];
      poly(ctx, left, shade(color, -36));
      poly(ctx, right, shade(color, -20));
      poly(ctx, top, shade(color, 20));
    }
    function drawGrid(ctx, scale, cx, cy) {
      ctx.strokeStyle = "#243551";
      ctx.lineWidth = 1;
      for (let i = -8; i <= 8; i += 1) {
        const a = project(-8, i, 0, scale, cx, cy);
        const b = project(8, i, 0, scale, cx, cy);
        const c = project(i, -8, 0, scale, cx, cy);
        const d = project(i, 8, 0, scale, cx, cy);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(c.x, c.y); ctx.lineTo(d.x, d.y); ctx.stroke();
      }
    }
    function drawRobot(ctx, pose, scale, cx, cy) {
      const event = pose.event || {};
      const primitive = String(event.primitive_call_code || "");
      const recovery = Boolean(event.is_recovery);
      const base = recovery ? "#e8793f" : "#7fb4e8";
      const swing = primitive === "NAVIGATE_TO" ? Math.sin(viewerTime * 8) * 0.16 : 0;
      const work = primitive && primitive !== "NAVIGATE_TO" ? Math.sin(viewerTime * 9) * 0.2 : 0;
      const x = pose.x - 0.25;
      const y = pose.y - 0.25;
      block(ctx, x + 0.08, y + 0.08, 0.75, 0.34, 0.34, 0.52, base, scale, cx, cy);
      block(ctx, x + 0.12, y + 0.12, 1.32, 0.26, 0.26, 0.24, "#e6edf5", scale, cx, cy);
      block(ctx, x + 0.02, y + 0.12 + work, 0.82, 0.08, 0.12, 0.46, "#90a4bd", scale, cx, cy);
      block(ctx, x + 0.40, y + 0.12 - work, 0.82, 0.08, 0.12, 0.46, "#90a4bd", scale, cx, cy);
      block(ctx, x + 0.13 + swing, y + 0.15, 0.15, 0.10, 0.12, 0.58, "#24364d", scale, cx, cy);
      block(ctx, x + 0.28 - swing, y + 0.15, 0.15, 0.10, 0.12, 0.58, "#24364d", scale, cx, cy);
      const p = project(pose.x, pose.y, 1.86, scale, cx, cy);
      ctx.fillStyle = "#f8fbff";
      ctx.font = "700 13px Consolas, monospace";
      ctx.textAlign = "center";
      ctx.fillText(event.display_code || "Humanoid", p.x, p.y - 12);
    }
    function updateViewerReadout() {
      $("viewerTime").textContent = `${viewerTime.toFixed(1)}s / ${traceDuration().toFixed(1)}s`;
      $("viewerSeek").value = String(viewerTime);
      $("viewerCamera").textContent =
        `zoom ${viewerCamera.zoom.toFixed(2)} / yaw ${Math.round(viewerCamera.yaw * 180 / Math.PI)}° / pitch ${Math.round((viewerCamera.pitch ?? 0) * 180 / Math.PI)}°`;
      const event = current ? currentEventAt(viewerTime) : null;
      const state = event?.state_after || {};
      $("viewerHud").textContent = event
        ? `${event.display_code || event.kind}  ${state.availability || "-"}`
        : "Run a trace to preview motion";
      syncTimelineToTime(viewerTime, viewerPlaying);
    }
    function drawViewer() {
      const canvas = $("viewer3d");
      const ratio = window.devicePixelRatio || 1;
      const width = canvas.clientWidth || 960;
      const height = canvas.clientHeight || 480;
      if (drawWebGLViewer(canvas, width, height)) {
        updateViewerReadout();
        return;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      if (canvas.width !== Math.floor(width * ratio) || canvas.height !== Math.floor(height * ratio)) {
        canvas.width = Math.floor(width * ratio);
        canvas.height = Math.floor(height * ratio);
      }
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, width, height);
      const grad = ctx.createLinearGradient(0, 0, 0, height);
      grad.addColorStop(0, "#172235");
      grad.addColorStop(1, "#07101f");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, width, height);
      const scale = Math.min(width / 18, 44);
      const cx = width / 2;
      const cy = height * 0.62;
      drawGrid(ctx, scale, cx, cy);
      block(ctx, -2.5, -1.8, 0, 5.0, 0.24, 0.12, "#355f8f", scale, cx, cy);
      block(ctx, 2.0, -2.5, 0, 0.24, 5.0, 0.12, "#355f8f", scale, cx, cy);
      if (!current) {
        ctx.fillStyle = "#c9d8ee";
        ctx.font = "700 18px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Run a Task or Incident to preview scripted motion", width / 2, height / 2);
        return;
      }
      const pose = poseAt(viewerTime);
      drawRobot(ctx, pose, scale, cx, cy);
      const state = pose.event?.state_after || {};
      ctx.fillStyle = "#9fb5d7";
      ctx.font = "12px Consolas, monospace";
      ctx.textAlign = "left";
      ctx.fillText(`${(pose.event?.display_code || "-")}  ${state.availability || "-"}`, 14, 24);
      updateViewerReadout();
    }
    function viewerLoop(frameMs) {
      if (viewerPlaying) {
        if (lastFrameMs == null) lastFrameMs = frameMs;
        const delta = (frameMs - lastFrameMs) / 1000;
        lastFrameMs = frameMs;
        const duration = traceDuration();
        viewerTime = Math.min(duration, viewerTime + delta);
        if (viewerTime >= duration) {
          viewerPlaying = false;
          $("viewerPlay").textContent = "Play";
        }
        drawViewer();
      } else {
        lastFrameMs = frameMs;
      }
      requestAnimationFrame(viewerLoop);
    }
    window.selectEvent = (index) => {
      const event = (current?.events || [])[index];
      selected = index;
      viewerTime = Number(event?.time_s || 0);
      viewerPlaying = false;
      $("viewerPlay").textContent = "Play";
      renderSelected();
      syncTimelineToTime(viewerTime, true);
      drawViewer();
    };
    $("mode").addEventListener("change", modeChanged);
    $("taskCategory").addEventListener("change", fillTaskOptions);
    $("run").addEventListener("click", async () => {
      try {
        const mode = $("mode").value;
        status("Running...");
        const body = { humanoid_id: $("humanoid").value, args: parseJson(), context: parseJson() };
        current = mode === "task"
          ? await api("/api/run-task", { task_code: $("task").value, humanoid_id: body.humanoid_id, args: body.args })
          : await api("/api/run-incident", { incident_code: $("incident").value, humanoid_id: body.humanoid_id, context: body.context });
        selected = 0;
        viewerTime = 0;
        viewerPlaying = true;
        $("viewerPlay").textContent = "Pause";
        render();
        status(`${current.ok ? "OK" : "ISSUES"} session ${current.session_id || "-"}`);
      } catch (err) { status(err.message); }
    });
    $("viewerPlay").addEventListener("click", () => {
      if (!current) { status("Run a trace first."); return; }
      viewerPlaying = !viewerPlaying;
      $("viewerPlay").textContent = viewerPlaying ? "Pause" : "Play";
    });
    $("viewerSeek").addEventListener("input", () => {
      viewerTime = Number($("viewerSeek").value || 0);
      viewerPlaying = false;
      $("viewerPlay").textContent = "Play";
      drawViewer();
    });
    $("viewerReset").addEventListener("click", () => {
      viewerCamera = { ...defaultViewerCamera };
      drawViewer();
    });
    $("viewerZoomIn").addEventListener("click", () => {
      viewerCamera.zoom = clamp(viewerCamera.zoom * 1.2, 0.45, 4.0);
      drawViewer();
    });
    $("viewerZoomOut").addEventListener("click", () => {
      viewerCamera.zoom = clamp(viewerCamera.zoom / 1.2, 0.45, 4.0);
      drawViewer();
    });
    $("viewer3d").addEventListener("wheel", (event) => {
      event.preventDefault();
      const factor = event.deltaY < 0 ? 1.12 : 1 / 1.12;
      viewerCamera.zoom = clamp(viewerCamera.zoom * factor, 0.45, 4.0);
      drawViewer();
    }, { passive: false });
    $("viewer3d").addEventListener("pointerdown", (event) => {
      $("viewer3d").setPointerCapture(event.pointerId);
      viewerDrag = {
        x: event.clientX,
        y: event.clientY,
        yaw: viewerCamera.yaw,
        pitch: viewerCamera.pitch,
        panX: viewerCamera.panX,
        panY: viewerCamera.panY,
        pan: event.shiftKey || event.button === 2,
      };
    });
    $("viewer3d").addEventListener("pointermove", (event) => {
      if (!viewerDrag) return;
      const dx = event.clientX - viewerDrag.x;
      const dy = event.clientY - viewerDrag.y;
      if (viewerDrag.pan || event.shiftKey) {
        viewerCamera.panX = viewerDrag.panX + dx;
        viewerCamera.panY = viewerDrag.panY + dy;
      } else {
        viewerCamera.yaw = viewerDrag.yaw + dx * 0.01;
        viewerCamera.pitch = clamp(viewerDrag.pitch + dy * 0.006, 0.18, 1.22);
      }
      drawViewer();
    });
    $("viewer3d").addEventListener("pointerup", () => { viewerDrag = null; });
    $("viewer3d").addEventListener("pointercancel", () => { viewerDrag = null; });
    $("viewer3d").addEventListener("contextmenu", (event) => event.preventDefault());
    $("viewer3d").addEventListener("dblclick", () => {
      viewerCamera = { ...defaultViewerCamera };
      drawViewer();
    });
    $("launchRviz").addEventListener("click", async () => {
      const result = await api("/api/ros/launch-rviz", {});
      status(result.message);
    });
    $("playRviz").addEventListener("click", async () => {
      if (!current) { status("Run a trace first."); return; }
      const result = await api("/api/ros/play-trace", { session_id: current.session_id, speed: Number($("speed").value || 1) });
      status(result.message);
    });
    $("launchGazebo").addEventListener("click", async () => {
      const result = await api("/api/ros/launch-gazebo", {});
      status(result.message);
    });
    requestAnimationFrame(viewerLoop);
    api("/api/catalog").then(data => { catalog = data; fillCatalog(); modeChanged(); drawViewer(); });
  </script>
</body>
</html>"""


__all__ = ["LabUiConfig", "LabUiRuntime", "launch_gazebo_validation", "run_lab_ui"]
