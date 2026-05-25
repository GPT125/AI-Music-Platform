# Santoor AI Learning Platform

A free-first MusicXML learning platform for Persian Santoor, with a polished React interface, FastAPI backend, private beta login, Santoor-aware mapping, generated accompaniment, and a browser microphone score follower.

The tutorial-video MVP follows the original research plan without a third-party video-generation service: MusicXML is corrected first, Santoor events drive the notation cursor, bridge/octave overlay, mallet hand, and three camera views, audio is derived from the same timeline, and FFmpeg can mux rendered frames plus WAV into MP4. No video API key is required for this deterministic path.

The app supports Google sign-in and a guest mode. Guest mode creates an isolated temporary account so the upload, demo score, video renderer, and orchestra flows work without configuring Google auth first.

AI Coach uses the first configured OpenAI-compatible provider in this order: Groq, DeepSeek, OpenRouter, OpenAI, then Hugging Face Router. Set `AI_PROVIDER` to force one provider. The app only stores provider names and generated feedback, never API keys.

## Research-backed Santoor Model

- Persian santur is modeled as a hammered dulcimer/struck zither with two rows of nine bridges, 18 courses, and 72 strings in four-string courses.
- The default preset is a practical G/Sol Santoor layout with yellow bass, white middle, and behind-bridge high lanes. It includes Persian quarter-tone slots for koron/sori mapping and exposes `course`, `string_material`, `playable_label`, mallet hand, and resonance metadata per note.
- Printed PDF/image score import uses Audiveris when `OMR_AUDIVERIS_PATH` is configured. The result is marked `needs_correction`, because OMR output must be reviewed before serious performance use.
- The orchestra engine uses free General MIDI SoundFont samples by default. For a pay-quality Santoor sound, provide a licensed recorded santur sample pack at `SANTOOR_SAMPLE_BASE_URL` and `VITE_SANTOOR_SAMPLE_BASE_URL` using note files such as `C4.mp3`, `D#4.mp3`, etc.

References used for the model and implementation direction: Britannica on santoor/santur construction, Vancouver Inter-Cultural Orchestra santur range/tuning notes, Persian Music Academy/Organology summaries of 72 strings and nine bridges per row, and Audiveris CLI documentation for batch MusicXML export.

## Local Setup

1. Create a Python environment and install backend dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```
2. Install frontend dependencies:
   ```bash
   npm install --prefix frontend
   ```
3. Fill `.env` or leave it blank for local SQLite defaults. At minimum for a real private beta, set:
   ```bash
   JWT_SECRET=your-long-random-secret
   INITIAL_ADMIN_EMAIL=you@example.com
   INITIAL_ADMIN_PASSWORD=your-password
   ```
   PDF/image OMR works when Audiveris is installed. Locally, the backend auto-detects `tools/audiveris/Audiveris.app/Contents/MacOS/Audiveris`, `/Applications/Audiveris.app/Contents/MacOS/Audiveris`, or an `audiveris` binary on PATH. You can also set:
   ```bash
   OMR_AUDIVERIS_PATH=tools/audiveris/Audiveris.app/Contents/MacOS/Audiveris
   ```
   AI Coach works when one of these is set:
   ```bash
   GROQ_API_KEY=...
   DEEPSEEK_API_KEY=...
   OPENROUTER_API_KEY=...
   OPENAI_API_KEY=...
   HUGGINGFACE_API_KEY=...
   ```
   For Render, add the same secret variables in the web service's Environment tab. Local `.env` values are not uploaded to Render by Git.
4. Run the API:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```
5. Run the frontend:
   ```bash
   npm run dev --prefix frontend
   ```

## Render

This repo is configured for a single free Render web service and a free Render Postgres database through `render.yaml`. Render deployment requires a GitHub/GitLab/Bitbucket remote. Free Render Postgres expires after 30 days, so move to a paid database or external free-tier Postgres before storing durable user data.

## Verification

```bash
pytest backend/tests
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm run test --prefix frontend
npm run build --prefix frontend
docker build -t santoor-ai-learning-platform .
```




UI / visual design
Create a real landing page hero
Add a clean top section with:
“Learn Santoor with AI”, a short subtitle, a “Start Learning” button, and a preview card showing lessons, audio feedback, or practice stats.
Use a premium music-style theme
Go for a dark navy / charcoal background with warm gold accents, subtle gradients, glassy cards, and Persian-inspired pattern details. This would instantly make it feel less like a basic web app and more like a polished product.
Add a proper navigation bar
Suggested tabs: Home, Lessons, Practice, AI Feedback, Library, Progress, Profile.
Make the homepage explain the app in 3 cards
Example cards:
Learn notes, Practice with AI, Track your progress.
Add screenshots/mock previews inside the site
Even if the features are simple, show fake-looking but realistic dashboard cards: “Today’s practice,” “Accuracy score,” “Recommended lesson.”
Improve spacing and typography
Use large headings, readable body text, consistent card padding, and not too many cramped buttons. This alone can make the app feel 2–3× better.
Create a dashboard instead of dumping features on one page
The logged-in home should show: current lesson, streak, skill level, recent recordings, and next recommended practice.
Add loading skeletons
When the app is waiting for AI/audio/database responses, show nice animated loading cards instead of plain “loading…”
Use icons everywhere
Use icons for lessons, audio, microphone, AI, progress, settings, favorites, etc. It makes the interface easier to scan.
Add empty states
Example: “No recordings yet — upload or record your first santoor practice.” Empty states make unfinished pages feel intentional.
Frontend functionality
Add a real audio recorder
Let users record directly in the browser, then submit the audio for feedback.
Add waveform visualization
Show the recorded audio visually. This makes the app feel much more advanced and music-focused.
Add a built-in metronome
A santoor learning app should have tempo control: 60 BPM, 80 BPM, 100 BPM, etc.
Add playback speed controls
Let users slow lessons down to 0.5×, 0.75×, 1×, and 1.25×.
Add a tuner or pitch helper
Even a simple “too high / too low / correct” pitch detector would make the app way more useful.
Add lesson progress tracking
Each lesson should show: Not started, In progress, Completed, Needs practice.
Add a practice streak
Daily streaks make users come back. Example: “3-day practice streak.”
Add keyboard shortcuts
Space = play/pause, R = record, M = metronome, arrow keys = move between lessons.
Make it mobile-first
A lot of students will open it on phones. Make buttons large, cards stacked, and the recorder easy to use.
Add accessibility improvements
Make sure keyboard focus is visible, buttons have labels, and text contrast is strong. WCAG specifically emphasizes visible focus indicators and text contrast, which helps users navigate without a mouse and improves overall usability.
Backend / AI improvements
Add authentication
Use Firebase Auth, Supabase Auth, or Clerk. Users need accounts so progress, recordings, and lessons are saved.
Create a real database structure
Suggested tables/collections:
users, lessons, recordings, feedback, practice_sessions, achievements.
Store audio recordings safely
Use cloud storage, not the database itself. Save only metadata in the database.
Add file upload protection
If users upload audio files, limit file type, size, and validate uploads. OWASP warns that file uploads can be risky if not properly restricted and validated.
Add an AI feedback queue
If AI analysis takes time, do not make the user wait on one long request. Use a job queue: upload → processing → feedback ready.
Add rate limits
Prevent users from spamming AI requests, recordings, or uploads. This protects your server cost and prevents abuse.
Cache common lesson data
Lessons, exercises, and static audio examples should load fast without refetching every time.
Add error logging
Use something like Sentry or backend logs so you know when users get errors instead of guessing.
Add analytics
Track which lessons people open, where they quit, and which buttons they use. This helps you improve the app based on real behavior.
Improve performance
Optimize loading, interactivity, and layout stability. Google’s Core Web Vitals focus on LCP, INP, and CLS, which measure loading speed, responsiveness, and visual stability.
Extra features that would make it feel “super functional”

Add a Practice Mode where the user chooses a lesson, starts a metronome, records themselves, and receives AI feedback like:

Timing: 82%
Note accuracy: 76%
Rhythm stability: Needs work
Recommended next exercise: Slow practice at 70 BPM

That one feature would make the platform feel like a real AI music tutor, not just a website.

My recommended build order

Start with this order:

Redesign homepage + dashboard
Add lesson cards and progress tracking
Add browser audio recording
Add AI feedback system
Add user accounts
Add database + saved practice history
Add metronome, waveform, and playback speed
Add analytics, upload security, and performance optimization
