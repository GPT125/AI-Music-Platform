import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AudioLines,
  FileMusic,
  Gauge,
  KeyRound,
  Loader2,
  LogOut,
  Mic,
  Music2,
  Pause,
  Play,
  Plus,
  SlidersHorizontal,
  UploadCloud,
  Wand2,
} from "lucide-react";
import { api } from "./api";
import { detectPitch, midiToFrequency, updateFollower, type FollowerState } from "./audio/follower";
import { OrchestraEngine } from "./audio/orchestra";
import type { ArrangementPayload, Instrument, Project, ScorePayload, User } from "./types";

const initialFollower: FollowerState = {
  index: 0,
  confidence: 0,
  detectedPitch: null,
  energy: 0,
  tempoRatio: 1,
  isPaused: true,
};

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [score, setScore] = useState<ScorePayload | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [selectedInstruments, setSelectedInstruments] = useState<string[]>(["string_ensemble_1", "flute", "cello", "acoustic_grand_piano"]);
  const [arrangement, setArrangement] = useState<ArrangementPayload | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const selectedProject = projects.find((project) => project.id === selectedId) ?? null;

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true));
    api.instruments().then((payload) => setInstruments(payload.instruments)).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!user) return;
    refreshProjects();
  }, [user]);

  useEffect(() => {
    if (!selectedId) return;
    api.score(selectedId).then(setScore).catch((error) => setNotice(error.message));
  }, [selectedId]);

  async function refreshProjects() {
    const items = await api.projects();
    setProjects(items);
    setSelectedId((current) => current ?? items[0]?.id ?? null);
  }

  if (!authChecked) {
    return <ShellLoader />;
  }
  if (!user) {
    return <Login onLogin={setUser} />;
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Music2 size={22} /></div>
          <div>
            <strong>Santoor AI</strong>
            <span>Private beta</span>
          </div>
        </div>
        <ProjectCreator
          onCreate={async (name) => {
            const project = await api.createProject(name);
            await refreshProjects();
            setSelectedId(project.id);
          }}
        />
        <nav className="project-list">
          {projects.map((project) => (
            <button
              key={project.id}
              className={project.id === selectedId ? "active" : ""}
              onClick={() => setSelectedId(project.id)}
            >
              <FileMusic size={17} />
              <span>{project.name}</span>
              <small>{project.score_status ?? "empty"}</small>
            </button>
          ))}
        </nav>
        <button
          className="logout"
          onClick={async () => {
            await api.logout();
            setUser(null);
          }}
        >
          <LogOut size={17} /> Sign out
        </button>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">MusicXML-first Santoor learning workspace</p>
            <h1>{selectedProject?.name ?? "Create a project"}</h1>
          </div>
          <div className="status-pills">
            <span><Activity size={15} /> {score?.status ?? "no score"}</span>
            <span><AudioLines size={15} /> {arrangement ? "orchestra ready" : "arrangement pending"}</span>
          </div>
        </header>

        {notice && <div className="notice">{notice}</div>}

        {selectedProject ? (
          <div className="grid">
            <UploadPanel
              projectId={selectedProject.id}
              onUploaded={async (message) => {
                setNotice(message);
                await refreshProjects();
                setScore(await api.score(selectedProject.id));
              }}
            />
            <ScorePanel score={score} projectId={selectedProject.id} onUpdated={setScore} />
            <SantoorPanel score={score} activeIndex={0} />
            <OrchestraPanel
              busy={busy}
              instruments={instruments}
              selected={selectedInstruments}
              setSelected={setSelectedInstruments}
              arrangement={arrangement}
              onGenerate={async () => {
                setBusy(true);
                try {
                  setArrangement(await api.arrange(selectedProject.id, selectedInstruments));
                } catch (error) {
                  setNotice(error instanceof Error ? error.message : "Could not generate arrangement");
                } finally {
                  setBusy(false);
                }
              }}
            />
            <LiveOrchestraPanel score={score} arrangement={arrangement} />
          </div>
        ) : (
          <div className="empty-state">
            <Music2 size={44} />
            <h2>No projects yet</h2>
            <p>Create your first Santoor learning project to upload a MusicXML score and start the live orchestra workflow.</p>
          </div>
        )}
      </main>
    </div>
  );
}

function ShellLoader() {
  return (
    <div className="center-screen">
      <Loader2 className="spin" size={28} />
      <span>Loading workspace</span>
    </div>
  );
}

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login-screen">
      <section className="login-panel">
        <div className="brand large">
          <div className="brand-mark"><Music2 size={26} /></div>
          <div>
            <strong>Santoor AI</strong>
            <span>Learning platform</span>
          </div>
        </div>
        <h1>Private beta login</h1>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError("");
            try {
              onLogin(await api.login(email, password));
            } catch (loginError) {
              setError(loginError instanceof Error ? loginError.message : "Login failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary" disabled={busy}><KeyRound size={18} /> {busy ? "Signing in" : "Sign in"}</button>
        </form>
      </section>
    </div>
  );
}

function ProjectCreator({ onCreate }: { onCreate: (name: string) => Promise<void> }) {
  const [name, setName] = useState("");
  return (
    <form
      className="project-create"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!name.trim()) return;
        await onCreate(name.trim());
        setName("");
      }}
    >
      <input value={name} onChange={(event) => setName(event.target.value)} placeholder="New project" />
      <button title="Create project"><Plus size={18} /></button>
    </form>
  );
}

function UploadPanel({ projectId, onUploaded }: { projectId: string; onUploaded: (message: string) => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  return (
    <section className="panel upload-panel">
      <div className="panel-title"><UploadCloud size={18} /><h2>Score Upload</h2></div>
      <p>Import MusicXML for full notation, Santoor mapping, and orchestra following. PDF and image uploads are saved for OMR/correction.</p>
      <label className="drop-zone">
        <input
          type="file"
          accept=".musicxml,.xml,.mxl,.mid,.midi,.pdf,.png,.jpg,.jpeg"
          onChange={async (event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            setBusy(true);
            try {
              const result = await api.uploadAsset(projectId, file);
              await onUploaded(result.message);
            } finally {
              setBusy(false);
              event.target.value = "";
            }
          }}
        />
        <UploadCloud size={32} />
        <strong>{busy ? "Processing upload" : "Choose score file"}</strong>
        <span>MusicXML, MXL, MIDI, PDF, PNG, or JPG</span>
      </label>
    </section>
  );
}

function ScorePanel({ score, projectId, onUpdated }: { score: ScorePayload | null; projectId: string; onUpdated: (score: ScorePayload) => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  useEffect(() => setText(score?.musicxml ?? ""), [score?.musicxml]);
  return (
    <section className="panel score-panel">
      <div className="panel-title"><FileMusic size={18} /><h2>Score & Correction</h2></div>
      {score?.events?.length ? (
        <div className="notation-strip">
          {score.events.slice(0, 48).map((event, index) => (
            <span key={`${event.id}-${index}`}>{event.ui_label}</span>
          ))}
        </div>
      ) : (
        <div className="soft-empty">No parsed notes yet. Upload MusicXML or paste corrected MusicXML.</div>
      )}
      <div className="score-actions">
        <button onClick={() => setEditing((value) => !value)}><SlidersHorizontal size={16} /> {editing ? "Close editor" : "Edit MusicXML"}</button>
        <button
          className="primary"
          onClick={async () => {
            await api.updateScore(projectId, text);
            onUpdated(await api.score(projectId));
          }}
        >
          <Wand2 size={16} /> Normalize
        </button>
      </div>
      {editing && <textarea value={text} onChange={(event) => setText(event.target.value)} spellCheck={false} />}
    </section>
  );
}

function SantoorPanel({ score, activeIndex }: { score: ScorePayload | null; activeIndex: number }) {
  const events = score?.events ?? [];
  const active = events[activeIndex];
  return (
    <section className="panel santoor-panel">
      <div className="panel-title"><Gauge size={18} /><h2>Santoor Lane View</h2></div>
      <div className="santoor-map">
        {Array.from({ length: 9 }).map((_, index) => (
          <div className="bridge" key={index} style={{ left: `${8 + index * 10.5}%` }}>
            <span>{index + 1}</span>
          </div>
        ))}
        {events.slice(0, 36).map((event, index) => (
          <div
            key={`${event.id}-${index}`}
            className={`note-dot lane-${event.octave_lane} ${active?.id === event.id ? "active" : ""}`}
            style={{ left: `${8 + Number(event.bridge_id.slice(1)) * 10.2}%`, top: `${24 + event.octave_lane * 24}%` }}
            title={`${event.ui_label} ${event.region}`}
          />
        ))}
      </div>
      <div className="event-table">
        {events.slice(0, 8).map((event) => (
          <div key={event.id}>
            <strong>{event.ui_label}</strong>
            <span>{event.bridge_id} · {event.region} · lane {event.octave_lane + 1}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function OrchestraPanel({
  instruments,
  selected,
  setSelected,
  arrangement,
  onGenerate,
  busy,
}: {
  instruments: Instrument[];
  selected: string[];
  setSelected: (selected: string[]) => void;
  arrangement: ArrangementPayload | null;
  onGenerate: () => Promise<void>;
  busy: boolean;
}) {
  return (
    <section className="panel orchestra-panel">
      <div className="panel-title"><AudioLines size={18} /><h2>Orchestra Builder</h2></div>
      <div className="instrument-grid">
        {instruments.map((instrument) => (
          <label key={instrument.id} className={selected.includes(instrument.id) ? "selected" : ""}>
            <input
              type="checkbox"
              checked={selected.includes(instrument.id)}
              onChange={() =>
                setSelected(
                  selected.includes(instrument.id)
                    ? selected.filter((id) => id !== instrument.id)
                    : [...selected, instrument.id],
                )
              }
            />
            <span>{instrument.name}</span>
            <small>{instrument.family}</small>
          </label>
        ))}
      </div>
      <button className="primary" onClick={onGenerate} disabled={busy || selected.length === 0}>
        <Wand2 size={17} /> {busy ? "Generating" : "Generate arrangement"}
      </button>
      {arrangement && <p className="success">{arrangement.tracks.length} playable tracks ready for live following.</p>}
    </section>
  );
}

function LiveOrchestraPanel({ score, arrangement }: { score: ScorePayload | null; arrangement: ArrangementPayload | null }) {
  const [follower, setFollower] = useState<FollowerState>(initialFollower);
  const [micState, setMicState] = useState("Not connected");
  const [playing, setPlaying] = useState(false);
  const engineRef = useRef<OrchestraEngine | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const lastTickRef = useRef(performance.now());
  const events = useMemo(() => score?.events ?? [], [score?.events]);

  const currentEvent = events[follower.index];
  const targetFrequency = currentEvent ? midiToFrequency(currentEvent.midi_note) : null;

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const analyser = analyserRef.current;
      const audioContext = audioContextRef.current;
      if (analyser && audioContext && events.length) {
        const buffer = new Float32Array(analyser.fftSize);
        analyser.getFloatTimeDomainData(buffer);
        const result = detectPitch(buffer, audioContext.sampleRate);
        const now = performance.now();
        setFollower((previous) => {
          const next = updateFollower(previous, events, result.frequency, result.energy, now - lastTickRef.current);
          lastTickRef.current = now;
          engineRef.current?.setTempoRatio(next.tempoRatio);
          if (next.isPaused) engineRef.current?.pause();
          else if (playing) engineRef.current?.playFrom(events[next.index]?.onset_s ?? 0);
          return next;
        });
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [events, playing]);

  async function connectMicrophone() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false }, video: false });
    const context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    audioContextRef.current = context;
    analyserRef.current = analyser;
    setMicState("Listening");
  }

  async function start() {
    if (!arrangement) return;
    const engine = engineRef.current ?? new OrchestraEngine();
    engineRef.current = engine;
    await engine.start();
    engine.schedule(arrangement.tracks);
    engine.playFrom(currentEvent?.onset_s ?? 0);
    setPlaying(true);
  }

  function stop() {
    engineRef.current?.stop();
    setPlaying(false);
  }

  return (
    <section className="panel live-panel">
      <div className="panel-title"><Mic size={18} /><h2>Live Orchestra</h2></div>
      <div className="live-readout">
        <div><small>Mic</small><strong>{micState}</strong></div>
        <div><small>Current note</small><strong>{currentEvent?.ui_label ?? "No score"}</strong></div>
        <div><small>Detected</small><strong>{follower.detectedPitch ? `MIDI ${follower.detectedPitch}` : "silent"}</strong></div>
        <div><small>Target Hz</small><strong>{targetFrequency ? targetFrequency.toFixed(1) : "-"}</strong></div>
        <div><small>Tempo</small><strong>{follower.tempoRatio.toFixed(2)}x</strong></div>
        <div><small>Confidence</small><strong>{Math.round(follower.confidence * 100)}%</strong></div>
      </div>
      <div className="confidence"><span style={{ width: `${Math.round(follower.confidence * 100)}%` }} /></div>
      <div className="transport">
        <button onClick={connectMicrophone}><Mic size={17} /> Allow microphone</button>
        <button className="primary" onClick={start} disabled={!arrangement || !events.length}><Play size={17} /> Follow & play</button>
        <button onClick={stop}><Pause size={17} /> Stop</button>
      </div>
      <p className="small-note">The follower uses the uploaded score as the source of truth, then listens for pitch and onset landmarks to keep the accompaniment synced to your timing.</p>
    </section>
  );
}

export default App;
