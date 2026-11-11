# AGENTS.md

## What this is

PyQt6 desktop trainer for shooting drones: YOLOv8s-seg detection on the PC, UDP link
to the camera/trigger board, SQLite session journal. Single Python app — no monorepo,
no CI, no lint/format/typecheck config (don't invent those commands).

## Commands

- Setup: `python3 -m venv venv && venv/bin/pip install -r requirements.txt`
  (README shows the Windows variant: `venv\Scripts\python ...`)
- Run: `venv/bin/python main.py` — **must run from repo root**; `config/settings.json`
  and all `data/` paths are CWD-relative (`src/utils/config.py` uses `Path("config/settings.json")`).
- The project venv is `venv/` (no dot). System `python3` has NO pytest/numpy/cv2 —
  run everything through `venv/bin/python`.
- On this machine only `python3` exists — there is no `python` alias.
- Tests:
  - all: `venv/bin/python -m pytest tests/ -q`
  - single file: `venv/bin/python -m pytest tests/test_lead.py -q`
  - single case: `venv/bin/python -m pytest tests/test_hit_checker.py::TestPointInPolygon::test_point_inside_square -q`
- There is no lint/typecheck/format command in this repo.

## Test quirks

- Tests import `from src....`; `tests/__init__.py` makes repo root the sys.path root —
  run pytest from repo root.
- Suite needs only `pytest`, `numpy`, `opencv-python`. PyQt6 and ultralytics are NOT
  required: YOLO is imported lazily inside `DroneDetector._load_model`, and there are
  no GUI tests.
- Model weights `data/models/yolov8s-seg.pt` are gitignored and absent; detector tests
  use dummy paths and never load a model.
- DB/report tests use `tmp_path` fixtures — no services, no cleanup step.

## Architecture (what filenames don't say)

- Entry flow: `main.py` → `SplashScreen` → `SetupDialog` → `MainWindow`.
  Hotkeys: F1 calibrate, F2 start session, F3 finish, F4 stats.
- `src/analysis/` is pure logic (no Qt, no I/O) — keep it that way; it's the best-tested code.
- `src/storage/journal.py` runs SQLite schema migrations on init (tests cover old-schema upgrade).
- Report CSV is UTF-8 **with BOM**, `;` separator (Excel/Russian locale) — don't "fix" it to commas.
- UDP ports (5000/5001/5002), model path, DB path all come from `config/settings.json`.
- Packet contract: one UDP datagram = JSON `{"type", "frame": base64 JPEG}`; `timestamp`
  is optional — the PC stamps receipt time (`UDPReceiver._decode_packet`).
- `MainWindow` starts `UDPReceiver` at startup: each trigger frame is shown and, in
  "Автоматический" mode, recorded as a shot via `StubDetector` (заглушка until YOLO is
  wired); "Ручной" mode waits for the trainer's ✔/✘ buttons.
- `src/detection/detector.py`: `cv2` is a hard top-level import; `ultralytics` is a soft dep.
- Global stylesheet `src/gui/styles.qss` is loaded by `main.py` at startup.

## Conventions

- Docstrings, comments, and UI strings are in **Russian** — match the surrounding file.
- Runtime log: `trainer.log` in CWD (gitignored).
- Everything under `data/` is runtime output (logs, calibration, shots, reports, weights) —
  gitignored; never commit it.
- README's structure section is stale (omits `setup_dialog`, `splash_screen`,
  `stats_dialog`, `shot_photo_dialog`, `session_stats`, `report`); trust the filesystem.

## Out of scope

- MaixCAM board code lives in another repo; `MAIXCAM_RECOVERY.md` is a hardware ops note
  referencing scripts (`maixcam/…`) not present here.
- `Оптико-электронный тренажёр….docx/.pptx` are project docs, not code.
