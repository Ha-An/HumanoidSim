from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

from .catalog import TaskCatalog, load_task_catalog
from .execution import load_sequence_file, simulate_task_sequence


def export_validation_viewer(
    sequence_path: Path | str,
    *,
    out: Path | str,
    catalog: TaskCatalog | None = None,
    report_out: Path | str | None = None,
) -> Path:
    catalog = catalog or load_task_catalog()
    output_path = Path(out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    profiles, instances = load_sequence_file(sequence_path)
    simulation = simulate_task_sequence(profiles, instances, catalog=catalog)
    simulation = _with_relative_frames(simulation, output_path.parent, catalog.root)

    if report_out is None:
        report_out = output_path.with_suffix(".json")
    report_path = Path(report_out)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(simulation, ensure_ascii=False, indent=2), encoding="utf-8")

    payload = json.dumps(simulation, ensure_ascii=False)
    output_path.write_text(_html(payload, Path(sequence_path).name), encoding="utf-8")
    return output_path


def _with_relative_frames(simulation: dict[str, Any], output_dir: Path, root: Path) -> dict[str, Any]:
    def rel(frame: str) -> str:
        path = root / frame
        return os.path.relpath(path, output_dir).replace("\\", "/")

    for task in simulation.get("tasks", []):
        task["frames"] = [rel(frame) for frame in task.get("frames", [])]
    for event in simulation.get("events", []):
        event["frames"] = [rel(frame) for frame in event.get("frames", [])]
    return simulation


def _html(payload: str, sequence_name: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Humanoid_Tasks Sequence Viewer</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, Segoe UI, Arial, sans-serif; background: #f5f7fb; color: #18243a; }}
    body {{ margin: 0; }}
    header {{ padding: 18px 24px; background: #16213a; color: white; display: flex; align-items: baseline; gap: 16px; }}
    header h1 {{ margin: 0; font-size: 22px; }}
    header span {{ opacity: .75; }}
    main {{ display: grid; grid-template-columns: 320px 1fr 360px; gap: 16px; padding: 16px; }}
    section {{ background: white; border: 1px solid #d8e0ec; border-radius: 8px; overflow: hidden; }}
    h2 {{ margin: 0; padding: 12px 14px; font-size: 15px; background: #eef3fb; border-bottom: 1px solid #d8e0ec; }}
    .queue {{ list-style: none; margin: 0; padding: 8px; display: grid; gap: 8px; }}
    .queue li {{ padding: 9px; border: 1px solid #dce5f1; border-radius: 6px; background: #fbfdff; }}
    .queue li.active {{ border-color: #2878d8; box-shadow: 0 0 0 2px #d8eaff; }}
    .code {{ font-family: Consolas, monospace; font-weight: 700; color: #153c68; }}
    .sub {{ color: #65738a; font-size: 12px; margin-top: 4px; }}
    .stage {{ min-height: 500px; display: grid; place-items: center; position: relative; background: linear-gradient(180deg, #f8fbff, #eef4fb); }}
    .spriteWrap {{ display: grid; place-items: center; gap: 10px; }}
    .sprite {{ image-rendering: pixelated; width: 112px; height: 112px; object-fit: contain; }}
    .badge {{ padding: 6px 10px; border-radius: 999px; background: #173a63; color: white; font-size: 13px; }}
    .timeline {{ padding: 10px; display: grid; gap: 7px; max-height: 540px; overflow: auto; }}
    .event {{ display: grid; grid-template-columns: 68px 1fr; gap: 8px; padding: 8px; border: 1px solid #dce5f1; border-radius: 6px; }}
    .event.active {{ background: #eaf4ff; border-color: #2878d8; }}
    .panel {{ padding: 12px 14px; display: grid; gap: 10px; }}
    .metric {{ display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid #edf1f6; padding-bottom: 6px; }}
    .ok {{ color: #0f7b4f; font-weight: 700; }}
    .bad {{ color: #be2b39; font-weight: 700; }}
    button {{ border: 1px solid #c2d0e2; background: white; border-radius: 6px; padding: 8px 10px; cursor: pointer; }}
    .controls {{ position: absolute; bottom: 18px; display: flex; gap: 8px; }}
  </style>
</head>
<body>
  <header><h1>Humanoid_Tasks Sequence Viewer</h1><span>{html.escape(sequence_name)}</span></header>
  <main>
    <section><h2>Task Queue</h2><ul id="queue" class="queue"></ul></section>
    <section>
      <h2>Animation Preview</h2>
      <div class="stage">
        <div class="spriteWrap">
          <img id="sprite" class="sprite" alt="humanoid task animation" />
          <div id="badge" class="badge">Ready</div>
        </div>
        <div class="controls"><button id="play">Pause</button><button id="restart">Restart</button></div>
      </div>
    </section>
    <section><h2>Details</h2><div id="details" class="panel"></div><h2>Step Timeline</h2><div id="timeline" class="timeline"></div></section>
  </main>
  <script>
    const DATA = {payload};
    let started = performance.now();
    let paused = false;
    let pausedAt = 0;
    const queue = document.getElementById("queue");
    const timeline = document.getElementById("timeline");
    const details = document.getElementById("details");
    const sprite = document.getElementById("sprite");
    const badge = document.getElementById("badge");
    const play = document.getElementById("play");
    const restart = document.getElementById("restart");
    function currentTime() {{ return ((paused ? pausedAt : performance.now()) - started) / 1000; }}
    function currentTask(t) {{ return DATA.tasks.find(task => t >= task.start_s && t < task.end_s) || DATA.tasks[DATA.tasks.length - 1]; }}
    function currentEvent(t) {{ return DATA.events.find(event => t >= event.start_s && t < event.end_s); }}
    function renderQueue(active) {{
      queue.innerHTML = DATA.tasks.map(task => `<li class="${{active && active.instance_id === task.instance_id ? "active" : ""}}"><div class="code">${{task.task_code}}</div><div>${{task.task_name}}</div><div class="sub">${{task.humanoid_id}} | ${{task.status}} | ${{task.risk}}</div></li>`).join("");
    }}
    function renderTimeline(activeEvent) {{
      timeline.innerHTML = DATA.events.map(event => `<div class="event ${{activeEvent && activeEvent.step_id === event.step_id && activeEvent.instance_id === event.instance_id ? "active" : ""}}"><div>${{event.start_s.toFixed(1)}}s</div><div><div class="code">${{event.call_code}}</div><div class="sub">${{event.task_code}} / ${{event.step_id}}</div></div></div>`).join("");
    }}
    function renderDetails(task, event) {{
      const issueCount = DATA.validation.issues.length;
      details.innerHTML = `
        <div class="metric"><span>Status</span><span class="${{DATA.validation.ok ? "ok" : "bad"}}">${{DATA.validation.ok ? "OK" : "HAS ISSUES"}}</span></div>
        <div class="metric"><span>Current task</span><span class="code">${{task?.task_code || "-"}}</span></div>
        <div class="metric"><span>Current step</span><span class="code">${{event?.call_code || "-"}}</span></div>
        <div class="metric"><span>Category</span><span>${{task?.category || "-"}}</span></div>
        <div class="metric"><span>Risk</span><span>${{task?.risk || "-"}}</span></div>
        <div class="metric"><span>Issues</span><span>${{issueCount}}</span></div>`;
    }}
    function tick() {{
      const duration = Math.max(DATA.duration_s, 1);
      const t = currentTime() % duration;
      const task = currentTask(t);
      const event = currentEvent(t);
      const frames = task?.frames || [];
      if (frames.length) sprite.src = frames[Math.floor(performance.now() / 350) % frames.length];
      badge.textContent = event ? `${{task.task_code}} / ${{event.call_code}}` : "Complete";
      renderQueue(task);
      renderTimeline(event);
      renderDetails(task, event);
      requestAnimationFrame(tick);
    }}
    play.addEventListener("click", () => {{
      if (paused) {{ started += performance.now() - pausedAt; paused = false; play.textContent = "Pause"; }}
      else {{ pausedAt = performance.now(); paused = true; play.textContent = "Play"; }}
    }});
    restart.addEventListener("click", () => {{ started = performance.now(); paused = false; play.textContent = "Pause"; }});
    tick();
  </script>
</body>
</html>
"""
