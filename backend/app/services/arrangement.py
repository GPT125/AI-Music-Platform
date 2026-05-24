from __future__ import annotations

from typing import Any, Dict, List


INSTRUMENTS: List[Dict[str, Any]] = [
    {"id": "acoustic_grand_piano", "name": "Piano", "family": "keys", "program": 0},
    {"id": "electric_piano_1", "name": "Electric Piano", "family": "keys", "program": 4},
    {"id": "violin", "name": "Violin", "family": "strings", "program": 40},
    {"id": "viola", "name": "Viola", "family": "strings", "program": 41},
    {"id": "cello", "name": "Cello", "family": "strings", "program": 42},
    {"id": "contrabass", "name": "Contrabass", "family": "strings", "program": 43},
    {"id": "orchestral_harp", "name": "Harp", "family": "strings", "program": 46},
    {"id": "acoustic_guitar_nylon", "name": "Classical Guitar", "family": "plucked", "program": 24},
    {"id": "flute", "name": "Flute", "family": "winds", "program": 73},
    {"id": "clarinet", "name": "Clarinet", "family": "winds", "program": 71},
    {"id": "oboe", "name": "Oboe", "family": "winds", "program": 68},
    {"id": "bassoon", "name": "Bassoon", "family": "winds", "program": 70},
    {"id": "trumpet", "name": "Trumpet", "family": "brass", "program": 56},
    {"id": "french_horn", "name": "French Horn", "family": "brass", "program": 60},
    {"id": "trombone", "name": "Trombone", "family": "brass", "program": 57},
    {"id": "alto_sax", "name": "Alto Sax", "family": "winds", "program": 65},
    {"id": "marimba", "name": "Marimba", "family": "mallets", "program": 12},
    {"id": "vibraphone", "name": "Vibraphone", "family": "mallets", "program": 11},
    {"id": "choir_aahs", "name": "Choir", "family": "voice", "program": 52},
    {"id": "string_ensemble_1", "name": "String Ensemble", "family": "strings", "program": 48},
    {"id": "pad_2_warm", "name": "Synth Pad", "family": "synth", "program": 89},
    {"id": "timpani", "name": "Timpani", "family": "percussion", "program": 47},
    {"id": "standard_kit", "name": "Percussion Kit", "family": "percussion", "program": 128},
    {"id": "dulcimer", "name": "Dulcimer / Santur", "family": "plucked", "program": 15},
]


def instrument_catalog() -> List[Dict[str, Any]]:
    return INSTRUMENTS


def generate_arrangement(score_events: List[Dict[str, Any]], instrument_ids: List[str], style: str = "balanced") -> List[Dict[str, Any]]:
    selected = instrument_ids or ["string_ensemble_1", "flute", "cello", "acoustic_grand_piano"]
    known = {item["id"]: item for item in INSTRUMENTS}
    tracks = []
    for track_index, instrument_id in enumerate(selected):
        instrument = known.get(instrument_id)
        if not instrument:
            continue
        notes = []
        for event_index, event in enumerate(score_events):
            midi = int(event.get("midi_note", 60))
            onset = float(event.get("onset_s", 0))
            duration = float(event.get("duration_s", 0.5))
            if instrument["family"] in {"strings", "synth", "voice"}:
                note = midi - 12 if track_index % 2 else midi
                note_duration = max(duration * 1.5, 0.8)
            elif instrument["family"] == "brass":
                if event_index % 2:
                    continue
                note = midi - 12
                note_duration = max(duration, 0.45)
            elif instrument["family"] == "percussion":
                note = 36 if event_index % 4 == 0 else 42
                note_duration = 0.12
            elif instrument["family"] == "keys":
                note = midi if event_index % 2 == 0 else midi - 5
                note_duration = max(duration * 0.85, 0.25)
            else:
                note = midi + (12 if track_index % 3 == 0 else 0)
                note_duration = max(duration * 0.9, 0.25)
            humanized_onset = onset + ((event_index % 3) - 1) * 0.012
            if instrument["id"] == "dulcimer":
                note = int(event.get("playable_midi_note", midi))
                note_duration = max(duration * 1.15, 0.35)
            notes.append(
                {
                    "midi_note": max(24, min(96, note)),
                    "onset_s": round(max(0, humanized_onset), 4),
                    "duration_s": round(note_duration, 4),
                    "velocity": 58 if instrument["family"] in {"strings", "voice", "synth"} else 72,
                    "follow_event_id": event.get("id"),
                }
            )
        tracks.append(
            {
                "instrument": instrument,
                "style": style,
                "notes": notes,
                "enabled": True,
                "volume": 0.68 if instrument["family"] in {"brass", "percussion"} else 0.74,
                "sample_policy": "General MIDI SoundFont by default; set SANTOOR_SAMPLE_BASE_URL/VITE_SANTOOR_SAMPLE_BASE_URL for a recorded santur sample pack.",
            }
        )
    return tracks
