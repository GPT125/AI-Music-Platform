import * as Tone from "tone";
import type { ArrangementTrack } from "../types";

const NOTES = ["C3", "D3", "E3", "F3", "G3", "A3", "B3", "C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "G5", "A5", "B5"];

export function midiToNote(midi: number): string {
  const names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  return `${names[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

export class OrchestraEngine {
  private synths = new Map<string, Tone.PolySynth>();
  private parts: Tone.Part[] = [];

  async start() {
    await Tone.start();
    Tone.Transport.bpm.value = 96;
  }

  setTempoRatio(ratio: number) {
    Tone.Transport.bpm.rampTo(96 * ratio, 0.12);
  }

  stop() {
    this.parts.forEach((part) => part.dispose());
    this.parts = [];
    Tone.Transport.stop();
    Tone.Transport.cancel();
  }

  pause() {
    Tone.Transport.pause();
  }

  playFrom(seconds: number) {
    Tone.Transport.seconds = seconds;
    Tone.Transport.start();
  }

  schedule(tracks: ArrangementTrack[]) {
    this.stop();
    tracks
      .filter((track) => track.enabled)
      .forEach((track) => {
        const synth = this.getSynth(track.instrument.id);
        synth.volume.value = Math.round((track.volume - 1) * 18);
        const part = new Tone.Part((time, note: any) => {
          synth.triggerAttackRelease(midiToNote(note.midi_note), note.duration_s, time, note.velocity / 127);
        }, track.notes.map((note) => [note.onset_s, note]));
        part.start(0);
        this.parts.push(part);
      });
  }

  private getSynth(id: string) {
    if (!this.synths.has(id)) {
      const synth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: id.includes("synth") ? "triangle" : "sine" },
        envelope: { attack: 0.015, decay: 0.18, sustain: 0.42, release: 0.8 },
      }).toDestination();
      this.synths.set(id, synth);
    }
    return this.synths.get(id)!;
  }
}

export const playableNoteNames = NOTES;
