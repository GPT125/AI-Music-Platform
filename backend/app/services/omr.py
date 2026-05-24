from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from backend.app.services.musicxml import read_score_payload


class OmrNotConfigured(RuntimeError):
    pass


def resolve_audiveris_path(configured_path: str = "") -> str:
    candidates = []
    if configured_path:
        candidates.append(configured_path)

    path_binary = shutil.which("audiveris") or shutil.which("Audiveris")
    if path_binary:
        candidates.append(path_binary)

    repo_root = Path(__file__).resolve().parents[3]
    candidates.extend(
        [
            repo_root / "tools" / "audiveris" / "Audiveris.app" / "Contents" / "MacOS" / "Audiveris",
            Path("/Applications/Audiveris.app/Contents/MacOS/Audiveris"),
            Path.home() / "Applications" / "Audiveris.app" / "Contents" / "MacOS" / "Audiveris",
        ]
    )

    for candidate in candidates:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.is_file():
            return str(candidate_path)
    return ""


def run_audiveris(asset_path: str, audiveris_path: str, timeout_s: int = 180) -> Dict[str, Any]:
    resolved_path = resolve_audiveris_path(audiveris_path)
    if not resolved_path:
        raise OmrNotConfigured(
            "Audiveris is not available. Install Audiveris or set OMR_AUDIVERIS_PATH to its executable to enable PDF/image recognition."
        )

    source = Path(asset_path)
    if not source.exists():
        raise FileNotFoundError(f"Uploaded score asset does not exist: {asset_path}")

    output_dir = source.parent / "omr"
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        resolved_path,
        "-batch",
        "-export",
        "-output",
        str(output_dir),
        "--",
        str(source),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_s, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "Audiveris failed without output"
        raise RuntimeError(message[-1200:])

    candidates = sorted(output_dir.glob("*.mxl")) + sorted(output_dir.glob("*.musicxml")) + sorted(output_dir.glob("*.xml"))
    if not candidates:
        candidates = sorted(source.parent.glob("*.mxl")) + sorted(source.parent.glob("*.musicxml")) + sorted(source.parent.glob("*.xml"))
    if not candidates:
        raise RuntimeError("Audiveris completed but did not produce a MusicXML/MXL file.")

    exported = candidates[0]
    musicxml, source_format = read_score_payload(exported.read_bytes(), exported.suffix)
    return {
        "musicxml": musicxml,
        "source_format": f"omr:{source_format}",
        "export_path": str(exported),
        "stdout": completed.stdout[-2000:],
    }


def try_run_omr(asset_path: str, audiveris_path: str, timeout_s: Optional[int] = None) -> Dict[str, Any]:
    return run_audiveris(asset_path, audiveris_path, timeout_s or 180)
