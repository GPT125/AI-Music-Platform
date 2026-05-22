from __future__ import annotations

import base64
import io
import zipfile
from typing import Any, Dict, List, Tuple
from xml.etree import ElementTree as ET


STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def read_score_payload(raw: bytes, suffix: str) -> Tuple[str, str]:
    suffix = suffix.lower()
    if suffix == ".mxl":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            candidates = [name for name in archive.namelist() if name.endswith((".xml", ".musicxml"))]
            if not candidates:
                raise ValueError("Compressed MusicXML archive has no XML score")
            preferred = next((name for name in candidates if not name.startswith("META-INF/")), candidates[0])
            return archive.read(preferred).decode("utf-8", errors="replace"), "mxl"
    if suffix in {".xml", ".musicxml"}:
        return raw.decode("utf-8", errors="replace"), "musicxml"
    raise ValueError("Unsupported score payload")


def strip_namespace(root: ET.Element) -> None:
    for element in root.iter():
        if "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]


def midi_from_pitch(step: str, octave: int, alter: float) -> int:
    return int(round((octave + 1) * 12 + STEP_TO_SEMITONE[step] + alter))


def accidental_cents(alter: float) -> int:
    return int(round((alter - round(alter)) * 100))


def parse_musicxml_events(musicxml: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(musicxml.encode("utf-8"))
    strip_namespace(root)
    events: List[Dict[str, Any]] = []
    divisions = 1
    current_division_time = 0.0
    tempo = 96.0
    seconds_per_division = 60.0 / tempo / divisions

    for part in root.findall(".//part"):
        current_division_time = 0.0
        for measure in part.findall("measure"):
            attrs = measure.find("attributes")
            if attrs is not None and attrs.findtext("divisions"):
                divisions = max(int(float(attrs.findtext("divisions", "1"))), 1)
                seconds_per_division = 60.0 / tempo / divisions
            for direction in measure.findall("direction"):
                per_minute = direction.findtext(".//per-minute")
                if per_minute:
                    tempo = max(float(per_minute), 20.0)
                    seconds_per_division = 60.0 / tempo / divisions
            for note in measure.findall("note"):
                duration_divs = float(note.findtext("duration", "0") or 0)
                if note.find("rest") is not None:
                    current_division_time += duration_divs
                    continue
                pitch = note.find("pitch")
                if pitch is None:
                    continue
                step = pitch.findtext("step", "C")
                octave = int(pitch.findtext("octave", "4"))
                alter = float(pitch.findtext("alter", "0") or 0)
                midi = midi_from_pitch(step, octave, alter)
                start = current_division_time * seconds_per_division
                duration = max(duration_divs * seconds_per_division, 0.1)
                events.append(
                    {
                        "id": f"n{len(events) + 1}",
                        "note_name": f"{step}{accidental_label(alter)}{octave}",
                        "midi_note": midi,
                        "accidental_cents": accidental_cents(alter),
                        "onset_s": round(start, 4),
                        "duration_s": round(duration, 4),
                        "velocity": 82,
                    }
                )
                if note.find("chord") is None:
                    current_division_time += duration_divs
    return events


def accidental_label(alter: float) -> str:
    if alter == 0:
        return ""
    if alter == 1:
        return "#"
    if alter == -1:
        return "b"
    if alter == 0.5:
        return " quarter-sharp "
    if alter == -0.5:
        return " quarter-flat "
    return f"({alter:+g})"


def placeholder_musicxml_from_events(events: List[Dict[str, Any]]) -> str:
    notes = []
    for event in events[:64]:
        midi = int(event["midi_note"])
        octave = midi // 12 - 1
        step = "C"
        alter = 0
        for candidate, semitone in STEP_TO_SEMITONE.items():
            if semitone == midi % 12:
                step = candidate
                break
        else:
            reverse = {1: ("C", 1), 3: ("D", 1), 6: ("F", 1), 8: ("G", 1), 10: ("A", 1)}
            step, alter = reverse.get(midi % 12, ("C", 0))
        notes.append(
            f"<note><pitch><step>{step}</step><alter>{alter}</alter><octave>{octave}</octave></pitch><duration>1</duration><type>quarter</type></note>"
        )
    body = "".join(notes) or "<note><rest/><duration>1</duration><type>quarter</type></note>"
    return (
        '<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0">'
        '<part-list><score-part id="P1"><part-name>Santoor</part-name></score-part></part-list>'
        f'<part id="P1"><measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>{body}</measure></part>'
        "</score-partwise>"
    )


def encode_musicxml_data_url(musicxml: str) -> str:
    payload = base64.b64encode(musicxml.encode("utf-8")).decode("ascii")
    return f"data:application/vnd.recordare.musicxml+xml;base64,{payload}"

