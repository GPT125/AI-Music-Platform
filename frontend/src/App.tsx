import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { detectPitch, midiToFrequency, updateFollower, type FollowerState } from "./audio/follower";
import { OrchestraEngine } from "./audio/orchestra";
import {
  Activity,
  AudioLines,
  FileMusic,
  Gauge,
  Loader2,
  LogOut,
  Mic,
  Music2,
  Pause,
  Play,
  Plus,
  Projector,
  ShieldCheck,
  SlidersHorizontal,
  UploadCloud,
  Wand2,
} from "./icons";
import Login from "./Login";
import type { AIFeedback, AIStatus, ArrangementPayload, Instrument, Project, ScorePayload, TutorialVideoPlan, User } from "./types";

type WorkspaceTab = "score" | "video" | "orchestra" | "ai";

const demoMusicXml = `<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Santoor</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>2</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <direction><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>84</per-minute></metronome></direction-type></direction>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>
      <note><pitch><step>B</step><alter>-0.5</alter><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type></note>
    </measure>
    <measure number="2">
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration><type>eighth</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>eighth</type></note>
      <note><pitch><step>B</step><alter>-0.5</alter><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>`;

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
  const [videoPlan, setVideoPlan] = useState<TutorialVideoPlan | null>(null);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [aiFeedback, setAiFeedback] = useState<AIFeedback | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeFollowerIndex, setActiveFollowerIndex] = useState(0);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("video");

  const selectedProject = projects.find((project) => project.id === selectedId) ?? null;

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true));
    api.instruments().then((payload) => setInstruments(payload.instruments)).catch(() => undefined);
    api.aiStatus().then(setAiStatus).catch(() => undefined);
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

  async function createDemoProject() {
    setBusy(true);
    try {
      const project = await api.createProject("Santoor demo");
      setSelectedId(project.id);
      await api.updateScore(project.id, demoMusicXml);
      const nextScore = await api.score(project.id);
      setScore(nextScore);
      await refreshProjects();
      setSelectedId(project.id);
      setArrangement(await api.arrange(project.id, selectedInstruments));
      setNotice("Demo score loaded. Open Performance Video or Live Orchestra.");
      setActiveTab("video");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not create demo project");
    } finally {
      setBusy(false);
    }
  }

  if (!authChecked) {
    return <ShellLoader />;
  }
  if (!user) {
    return <Login />;
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Music2 size={22} /></div>
          <div>
            <strong>Santoor AI</strong>
            <span>{user.name || user.email}</span>
          </div>
        </div>
        <ProjectCreator
          onCreate={async (name) => {
            const project = await api.createProject(name);
            await refreshProjects();
            setSelectedId(project.id);
          }}
        />
        <button className="demo-button" onClick={createDemoProject} disabled={busy}>
          <Play size={17} /> Try working demo
        </button>
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
            <p className="eyebrow">Performance workspace</p>
            <h1>{selectedProject?.name ?? "Create a project"}</h1>
          </div>
          <div className="status-pills">
            <span><ShieldCheck size={15} /> {user.auth_provider === "guest" ? "Guest session" : "Saved account"}</span>
            <span><Activity size={15} /> {score?.status ?? "no score"}</span>
            <span><AudioLines size={15} /> {arrangement ? "orchestra ready" : "arrangement pending"}</span>
          </div>
        </header>

        {notice && <div className="notice">{notice}</div>}

        {selectedProject ? (
          <>
            <HeroConsole score={score} arrangement={arrangement} followerIndex={activeFollowerIndex} />
            <div className="studio-tabs" role="tablist" aria-label="Workspace sections">
              {[
                ["video", "Performance Video", Projector],
                ["orchestra", "Live Orchestra", AudioLines],
                ["ai", "AI Coach", Wand2],
                ["score", "Score Setup", FileMusic],
              ].map(([id, label, Icon]) => (
                <button key={id as string} className={activeTab === id ? "active" : ""} onClick={() => setActiveTab(id as WorkspaceTab)}>
                  <Icon size={17} /> {label as string}
                </button>
              ))}
            </div>

            {activeTab === "video" && (
              <div className="studio-layout video-layout">
                <TutorialVideoPanel
                  score={score}
                  arrangement={arrangement}
                  plan={videoPlan}
                  onCreate={async () => {
                    setBusy(true);
                    try {
                      const result = await api.tutorialVideo(selectedProject.id, arrangement?.id);
                      setVideoPlan(result.render_plan);
                      setNotice("Video generated. Use the player in Performance Video to review the lesson.");
                    } catch (error) {
                      setNotice(error instanceof Error ? error.message : "Could not create tutorial video plan");
                    } finally {
                      setBusy(false);
                    }
                  }}
                  busy={busy}
                />
                <SantoorPanel score={score} activeIndex={activeFollowerIndex} />
              </div>
            )}

            {activeTab === "orchestra" && (
              <div className="studio-layout">
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
                <LiveOrchestraPanel score={score} arrangement={arrangement} onFollowerIndex={setActiveFollowerIndex} />
              </div>
            )}

            {activeTab === "ai" && (
              <div className="studio-layout ai-layout">
                <AICoachPanel
                  score={score}
                  status={aiStatus}
                  feedback={aiFeedback}
                  busy={busy}
                  onGenerate={async () => {
                    setBusy(true);
                    try {
                      const result = await api.aiFeedback(selectedProject.id);
                      setAiFeedback(result.feedback);
                      setAiStatus(result.ai);
                      setNotice(`AI Coach used ${result.feedback._provider} (${result.feedback._model}).`);
                    } catch (error) {
                      setNotice(error instanceof Error ? error.message : "AI Coach could not generate feedback");
                    } finally {
                      setBusy(false);
                    }
                  }}
                />
                <SantoorPanel score={score} activeIndex={activeFollowerIndex} />
              </div>
            )}

            {activeTab === "score" && (
              <div className="studio-layout">
                <UploadPanel
                  projectId={selectedProject.id}
                  onUploaded={async (message) => {
                    setNotice(message);
                    await refreshProjects();
                    setScore(await api.score(selectedProject.id));
                    setVideoPlan(null);
                    setArrangement(null);
                  }}
                />
                <ScorePanel score={score} projectId={selectedProject.id} onUpdated={setScore} />
              </div>
            )}
          </>
        ) : (
          <div className="empty-state">
            <Music2 size={44} />
            <h2>No projects yet</h2>
            <p>Create a project or load the demo score to see the video renderer and orchestra flow immediately.</p>
            <button className="primary" onClick={createDemoProject} disabled={busy}><Play size={17} /> Load demo score</button>
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

function HeroConsole({
  score,
  arrangement,
  followerIndex,
}: {
  score: ScorePayload | null;
  arrangement: ArrangementPayload | null;
  followerIndex: number;
}) {
  const events = score?.events ?? [];
  const current = events[followerIndex];
  const duration = events.length
    ? Math.max(...events.map((event) => event.onset_s + event.duration_s))
    : 0;
  const progress = events.length ? Math.round((followerIndex / Math.max(events.length - 1, 1)) * 100) : 0;
  return (
    <section className="hero-console">
      <div className="wave-stack" aria-hidden="true">
        {Array.from({ length: 18 }).map((_, index) => (
          <span key={index} style={{ height: `${22 + ((index * 19) % 58)}px` }} />
        ))}
      </div>
      <div className="hero-copy">
        <p className="eyebrow">Santoor lesson renderer</p>
        <h2>{current ? `${current.ui_label} on ${current.bridge_id}` : "Load a score to generate a playable lesson video"}</h2>
        <p>Generate a performer-view video with mallet strikes, bridge position, octave lane, beat timing, and synthesized guide audio.</p>
      </div>
      <div className="hero-metrics">
        <div><strong>{events.length}</strong><span>mapped notes</span></div>
        <div><strong>{arrangement?.tracks.length ?? 0}</strong><span>orchestra tracks</span></div>
        <div><strong>{duration ? `${duration.toFixed(1)}s` : "-"}</strong><span>score time</span></div>
      </div>
      <div className="timeline-rail"><span style={{ width: `${progress}%` }} /></div>
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

function TutorialVideoPanel({
  score,
  arrangement,
  plan,
  onCreate,
  busy,
}: {
  score: ScorePayload | null;
  arrangement: ArrangementPayload | null;
  plan: TutorialVideoPlan | null;
  onCreate: () => Promise<void>;
  busy: boolean;
}) {
  const [view, setView] = useState<"overhead" | "right_side" | "left_side">("left_side");
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewTime, setPreviewTime] = useState(0);
  const cues = plan?.cues.slice(0, 6) ?? score?.events.slice(0, 6).map((event) => ({
    event_id: event.id,
    label: event.ui_label,
    start_frame: Math.round(event.onset_s * 30),
    end_frame: Math.round((event.onset_s + event.duration_s) * 30),
    onset_s: event.onset_s,
    duration_s: event.duration_s,
    bridge_id: event.bridge_id,
    region: event.region,
    octave_lane: event.octave_lane,
    highlight: event.highlight,
    string_material: event.string_material,
    course: event.course,
    mallet: event.technique?.mallet ?? "right",
    resonance_s: event.technique?.resonance_s ?? 2,
    playable_label: event.playable_label,
  })) ?? [];
  const fullCues = plan?.cues ?? cues;
  const activeCue = fullCues.find((cue) => previewTime >= cue.onset_s && previewTime <= cue.onset_s + Math.max(cue.duration_s, 0.16)) ?? fullCues[0];
  const duration = plan?.duration_s || Math.max(...fullCues.map((cue) => cue.onset_s + cue.duration_s), 1);
  const viewSpec = plan?.views.find((item) => item.id === view);

  useEffect(() => {
    if (!isPreviewing) return;
    let frame = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const delta = (now - last) / 1000;
      last = now;
      setPreviewTime((time) => {
        const next = time + delta;
        if (next >= duration) {
          setIsPreviewing(false);
          return 0;
        }
        return next;
      });
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [duration, isPreviewing]);

  return (
    <section className="panel video-panel feature-panel">
      <div className="panel-title split-title">
        <div><Projector size={18} /><h2>Performance Video</h2></div>
        <span>{activeCue ? `${activeCue.playable_label} · ${activeCue.bridge_id}` : "Waiting for score"}</span>
      </div>
      <div className="view-tabs" role="tablist" aria-label="Santoor video camera view">
        {(["overhead", "right_side", "left_side"] as const).map((item) => (
          <button key={item} className={view === item ? "active" : ""} onClick={() => setView(item)}>
            {item === "overhead" ? "High hands" : item === "right_side" ? "Right angle" : "Left angle"}
          </button>
        ))}
      </div>
      {plan?.video_url ? (
        <video className="rendered-video" src={plan.video_url} controls playsInline />
      ) : (
      <div className="video-stage">
        <div className={`performer-view ${view}`}>
          <div className="camera-label">
            <strong>{viewSpec?.label ?? "High hand view"}</strong>
            <span>{activeCue?.label ?? "No cue"}</span>
          </div>
          <div className="santoor-body" style={{ transform: `scale(${viewSpec?.camera.zoom ?? 1}) rotate(${viewSpec?.camera.rotation ?? 0}deg)` }}>
            {Array.from({ length: 18 }).map((_, index) => (
              <span key={index} className="string-course" style={{ left: `${5 + index * 5.25}%` }} />
            ))}
            {activeCue && (
              <>
                <b
                  className={`mallet right ${activeCue.mallet === "right" ? "strike" : ""}`}
                  style={{ left: `${12 + Number(activeCue.bridge_id.slice(1) || 1) * 8.5}%`, top: `${28 + activeCue.octave_lane * 14}%` }}
                />
                <b
                  className={`mallet left ${activeCue.mallet === "left" ? "strike" : ""}`}
                  style={{ left: `${10 + Number(activeCue.bridge_id.slice(1) || 1) * 8.5}%`, top: `${36 + activeCue.octave_lane * 14}%` }}
                />
                <i
                  className="strike-glow"
                  style={{ left: `${11 + Number(activeCue.bridge_id.slice(1) || 1) * 8.5}%`, top: `${36 + activeCue.octave_lane * 15}%` }}
                />
              </>
            )}
          </div>
        </div>
        <div className="video-score">
          {cues.map((cue) => (
            <span key={cue.event_id} className={activeCue?.event_id === cue.event_id ? "active" : ""}>{cue.label}</span>
          ))}
        </div>
        <div className="video-santoor">
          {cues.slice(0, 4).map((cue) => (
            <i
              key={`${cue.event_id}-dot`}
              className={`lane-${cue.octave_lane}`}
              style={{ left: `${10 + Number(cue.bridge_id.slice(1) || 1) * 8.8}%`, top: `${32 + cue.octave_lane * 20}%` }}
            />
          ))}
        </div>
      </div>
      )}
      <div className="video-meta">
        <span><strong>{activeCue?.mallet ?? "-"}</strong> mallet</span>
        <span><strong>{activeCue?.region?.replace(/_/g, " ") ?? "-"}</strong> string row</span>
        <span><strong>{plan ? `${plan.duration_s.toFixed(1)}s` : `${score?.events.length ?? 0} notes`}</strong> timeline</span>
      </div>
      <div className="transport compact">
        <button onClick={() => setIsPreviewing((value) => !value)} disabled={!fullCues.length}>
          {isPreviewing ? <Pause size={17} /> : <Play size={17} />} {isPreviewing ? "Pause preview" : "Preview timing"}
        </button>
        <input
          type="range"
          min="0"
          max={duration}
          step="0.01"
          value={previewTime}
          onChange={(event) => setPreviewTime(Number(event.target.value))}
        />
      </div>
      <button className="primary" onClick={onCreate} disabled={busy || !score?.events.length}>
        <Projector size={17} /> {busy ? "Rendering MP4" : "Generate lesson video"}
      </button>
      <p className="small-note">This creates a real MP4 from the score timeline. The left-side camera is the default because it shows the player hands and Santoor courses clearly.</p>
      {arrangement && <p className="success">Video plan can use the current {arrangement.tracks.length}-track arrangement as its audio source.</p>}
    </section>
  );
}

function AICoachPanel({
  score,
  status,
  feedback,
  busy,
  onGenerate,
}: {
  score: ScorePayload | null;
  status: AIStatus | null;
  feedback: AIFeedback | null;
  busy: boolean;
  onGenerate: () => Promise<void>;
}) {
  const providerLabel = status?.configured
    ? `${status.providers[0]?.name ?? status.active_provider} · ${status.providers[0]?.model ?? "model"}`
    : "Local fallback";
  return (
    <section className="panel ai-coach-panel feature-panel">
      <div className="panel-title split-title">
        <div><Wand2 size={18} /><h2>AI Coach</h2></div>
        <span>{providerLabel}</span>
      </div>
      <div className="ai-hero">
        <p className="eyebrow">Score-aware Santoor feedback</p>
        <h3>{feedback?.summary ?? "Generate a practice plan from the uploaded score."}</h3>
        <p>
          The coach reads mapped notes, bridges, mallet alternation, timing, and Santoor rows. It uses your configured LLM keys when available and falls back to deterministic guidance when providers are unavailable.
        </p>
      </div>
      <button className="primary" onClick={onGenerate} disabled={busy || !score?.events.length}>
        <Wand2 size={17} /> {busy ? "Asking AI Coach" : "Generate AI feedback"}
      </button>
      {!score?.events.length && <p className="small-note">Load the demo or upload MusicXML before asking for AI feedback.</p>}
      {feedback && (
        <div className="ai-feedback-grid">
          <FeedbackList title="Practice Plan" items={feedback.practice_plan} />
          <FeedbackList title="Technique" items={feedback.technical_notes} />
          <FeedbackList title="Rhythm" items={feedback.rhythm_notes} />
          <FeedbackList title="Santoor Notes" items={feedback.santoor_notes} />
          {feedback.risk_flags.length > 0 && <FeedbackList title="Warnings" items={feedback.risk_flags} />}
        </div>
      )}
    </section>
  );
}

function FeedbackList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="feedback-list">
      <strong>{title}</strong>
      {items.length ? (
        <ul>
          {items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
        </ul>
      ) : (
        <span>No notes returned.</span>
      )}
    </div>
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

function LiveOrchestraPanel({
  score,
  arrangement,
  onFollowerIndex,
}: {
  score: ScorePayload | null;
  arrangement: ArrangementPayload | null;
  onFollowerIndex: (index: number) => void;
}) {
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
          else if (playing && previous.isPaused) engineRef.current?.playFrom(events[next.index]?.onset_s ?? 0);
          onFollowerIndex(next.index);
          return next;
        });
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [events, onFollowerIndex, playing]);

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
    setFollower((previous) => ({ ...previous, isPaused: false }));
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
