import { loadTone } from "./tone-loader.js";
import type { ArrangementTrack, Instrument } from "../types";

let toneRuntime: any = null;

type Voice = {
  volume: { value: number };
  trigger: (midi: number, duration: number, time: number, velocity: number) => void;
  dispose: () => void;
};

export function midiToNote(midi: number): string {
  const names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  return `${names[midi % 12]}${Math.floor(midi / 12) - 1}`;
}

export function soundfontFileForNote(note: string): string {
  return `${note.replace("C#", "Db").replace("D#", "Eb").replace("F#", "Gb").replace("G#", "Ab").replace("A#", "Bb")}.mp3`;
}

function voiceSettings(instrument: Instrument) {
  if (instrument.id === "dulcimer") {
    return {
      oscillator: { type: "triangle8" },
      envelope: { attack: 0.004, decay: 0.26, sustain: 0.12, release: 1.25 },
      delay: { delayTime: 0.08, feedback: 0.22, wet: 0.18 },
    };
  }
  if (instrument.family === "strings") {
    return {
      oscillator: { type: instrument.id === "contrabass" ? "sawtooth4" : "sawtooth8" },
      envelope: { attack: 0.055, decay: 0.25, sustain: 0.68, release: 1.1 },
      delay: { delayTime: 0.03, feedback: 0.12, wet: 0.08 },
    };
  }
  if (instrument.family === "winds") {
    return {
      oscillator: { type: "triangle4" },
      envelope: { attack: 0.04, decay: 0.15, sustain: 0.62, release: 0.45 },
      delay: { delayTime: 0.018, feedback: 0.08, wet: 0.05 },
    };
  }
  if (instrument.family === "brass") {
    return {
      oscillator: { type: "square4" },
      envelope: { attack: 0.025, decay: 0.18, sustain: 0.74, release: 0.38 },
      delay: { delayTime: 0.02, feedback: 0.05, wet: 0.04 },
    };
  }
  if (instrument.family === "mallets" || instrument.family === "plucked") {
    return {
      oscillator: { type: "sine8" },
      envelope: { attack: 0.006, decay: 0.34, sustain: 0.18, release: 0.78 },
      delay: { delayTime: 0.07, feedback: 0.2, wet: 0.13 },
    };
  }
  if (instrument.family === "voice" || instrument.family === "synth") {
    return {
      oscillator: { type: "triangle8" },
      envelope: { attack: 0.18, decay: 0.25, sustain: 0.72, release: 1.5 },
      delay: { delayTime: 0.11, feedback: 0.16, wet: 0.16 },
    };
  }
  return {
    oscillator: { type: instrument.family === "keys" ? "triangle" : "sine" },
    envelope: { attack: 0.01, decay: 0.2, sustain: 0.45, release: 0.65 },
    delay: { delayTime: 0.035, feedback: 0.1, wet: 0.06 },
  };
}

export class OrchestraEngine {
  private voices = new Map<string, Voice>();
  private parts: any[] = [];

  private async tone() {
    if (!toneRuntime) {
      toneRuntime = await loadTone();
    }
    return toneRuntime;
  }

  async start() {
    const Tone = await this.tone();
    await Tone.start();
    if (Tone.getContext().state !== "running") {
      await Tone.getContext().resume();
    }
    Tone.Transport.bpm.value = 96;
  }

  async previewInstrument(instrument: Instrument, midi = 64) {
    const Tone = await this.tone();
    await this.start();
    const voice = this.getVoice(instrument);
    voice.volume.value = -6;
    voice.trigger(midi, instrument.family === "strings" || instrument.family === "voice" ? 1.1 : 0.72, Tone.now() + 0.03, 0.9);
  }

  setTempoRatio(ratio: number) {
    if (!toneRuntime) return;
    toneRuntime.Transport.bpm.rampTo(96 * Math.max(0.45, Math.min(1.8, ratio)), 0.12);
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
    toneRuntime.Transport.seconds = Math.max(0, seconds);
    toneRuntime.Transport.start("+0.02");
  }

  schedule(tracks: ArrangementTrack[]) {
    const Tone = toneRuntime;
    if (!Tone) return;
    this.stop();
    tracks
      .filter((track) => track.enabled && track.notes.length)
      .forEach((track) => {
        const voice = this.getVoice(track.instrument);
        voice.volume.value = Math.round((track.volume - 1) * 18) - 3;
        const part = new Tone.Part((time: number, note: any) => {
          voice.trigger(note.midi_note, Math.max(0.08, note.duration_s), time, note.velocity / 127);
        }, track.notes.map((note) => [Math.max(0, note.onset_s), note]));
        part.start(0);
        this.parts.push(part);
      });
  }

  dispose() {
    this.stop();
    this.voices.forEach((voice) => voice.dispose());
    this.voices.clear();
  }

  private getVoice(instrument: Instrument): Voice {
    const Tone = toneRuntime;
    if (!Tone) throw new Error("Audio engine is not ready");
    const existing = this.voices.get(instrument.id);
    if (existing) return existing;

    const voice = instrument.family === "percussion" ? this.createPercussionVoice(instrument) : this.createTonalVoice(instrument);
    this.voices.set(instrument.id, voice);
    return voice;
  }

  private createTonalVoice(instrument: Instrument): Voice {
    const Tone = toneRuntime;
    const settings = voiceSettings(instrument);
    const volume = new Tone.Volume(-8).toDestination();
    const delay = new Tone.FeedbackDelay(settings.delay).connect(volume);
    const synth = new Tone.PolySynth(Tone.Synth, {
      oscillator: settings.oscillator,
      envelope: settings.envelope,
      maxPolyphony: 12,
    }).connect(delay);
    return {
      volume: volume.volume,
      trigger: (midi, duration, time, velocity) => {
        synth.triggerAttackRelease(midiToNote(Math.max(24, Math.min(96, Math.round(midi)))), duration, time, velocity);
      },
      dispose: () => {
        synth.dispose();
        delay.dispose();
        volume.dispose();
      },
    };
  }

  private createPercussionVoice(instrument: Instrument): Voice {
    const Tone = toneRuntime;
    const volume = new Tone.Volume(instrument.id === "timpani" ? -8 : -10).toDestination();
    const drum = new Tone.MembraneSynth({
      pitchDecay: 0.045,
      octaves: instrument.id === "timpani" ? 2.6 : 5,
      envelope: { attack: 0.001, decay: 0.35, sustain: 0.02, release: 0.35 },
    }).connect(volume);
    const hat = new Tone.NoiseSynth({
      noise: { type: "white" },
      envelope: { attack: 0.001, decay: 0.09, sustain: 0, release: 0.08 },
    }).connect(volume);
    return {
      volume: volume.volume,
      trigger: (midi, duration, time, velocity) => {
        if (instrument.id === "timpani" || midi <= 40) {
          drum.triggerAttackRelease(midiToNote(Math.max(28, Math.min(52, Math.round(midi)))), Math.max(0.08, duration), time, velocity);
        } else {
          hat.triggerAttackRelease(Math.max(0.04, Math.min(0.16, duration)), time, velocity * 0.75);
        }
      },
      dispose: () => {
        drum.dispose();
        hat.dispose();
        volume.dispose();
      },
    };
  }
}
