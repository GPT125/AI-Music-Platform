import type { ArrangementTrack } from "../types";

const NOTES = ["C3", "D#3", "F#3", "A3", "C4", "D#4", "F#4", "A4", "C5", "D#5", "F#5", "A5", "C6"];
const SOUNDFONT_BASE_URL = import.meta.env.VITE_SOUNDFONT_BASE_URL || "https://gleitz.github.io/midi-js-soundfonts/FluidR3_GM/";
let toneRuntime: any = null;

export function midiToNote(midi: number): string {
  const names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  return `${names[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

export class OrchestraEngine {
  private players = new Map<string, any>();
  private parts: any[] = [];

  private async tone() {
    if (!toneRuntime) {
      const dynamicImport = new Function("specifier", "return import(specifier)") as (specifier: string) => Promise<any>;
      toneRuntime = await dynamicImport("tone");
    }
    return toneRuntime;
  }

  async start() {
    const Tone = await this.tone();
    await Tone.start();
    Tone.Transport.bpm.value = 96;
  }

  setTempoRatio(ratio: number) {
    if (!toneRuntime) return;
    toneRuntime.Transport.bpm.rampTo(96 * ratio, 0.12);
  }

  stop() {
    this.parts.forEach((part) => part.dispose());
    this.parts = [];
    if (!toneRuntime) return;
    toneRuntime.Transport.stop();
    toneRuntime.Transport.cancel();
  }

  pause() {
    toneRuntime?.Transport.pause();
  }

  playFrom(seconds: number) {
    if (!toneRuntime) return;
    toneRuntime.Transport.seconds = seconds;
    toneRuntime.Transport.start();
  }

  schedule(tracks: ArrangementTrack[]) {
    const Tone = toneRuntime;
    if (!Tone) return;
    this.stop();
    tracks
      .filter((track) => track.enabled)
      .forEach((track) => {
        const player = this.getPlayer(track.instrument.id);
        player.volume.value = Math.round((track.volume - 1) * 18);
        const part = new Tone.Part((time: number, note: any) => {
          player.triggerAttackRelease(midiToNote(note.midi_note), note.duration_s, time, note.velocity / 127);
        }, track.notes.map((note) => [note.onset_s, note]));
        part.start(0);
        this.parts.push(part);
      });
  }

  private getPlayer(id: string) {
    const Tone = toneRuntime;
    if (!Tone) throw new Error("Audio engine is not ready");
    if (!this.players.has(id)) {
      try {
        const sampler = new Tone.Sampler({
          urls: Object.fromEntries(NOTES.map((note) => [note, `${note}.mp3`])),
          baseUrl: `${SOUNDFONT_BASE_URL.replace(/\/$/, "")}/${id}-mp3/`,
          release: 1,
        }).toDestination();
        this.players.set(id, sampler);
      } catch {
        const synth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: id.includes("synth") ? "triangle" : "sine" },
        envelope: { attack: 0.015, decay: 0.18, sustain: 0.42, release: 0.8 },
      }).toDestination();
        this.players.set(id, synth);
      }
    }
    return this.players.get(id)!;
  }
}

export const playableNoteNames = NOTES;
