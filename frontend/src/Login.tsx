import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { AudioLines, Globe2, Music2, RadioTower, Sparkles } from "./icons";

function Login() {
  const [error, setError] = useState("");
  const [guestBusy, setGuestBusy] = useState(false);
  const [fallbackReady, setFallbackReady] = useState(true);
  const buttonRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function setupGoogle() {
      try {
        const config = await api.googleConfig();
        if (!config.configured || !config.client_id) {
          setFallbackReady(true);
          return;
        }
        await loadGoogleScript();
        if (cancelled || !buttonRef.current || !window.google) return;
        setFallbackReady(false);
        window.google.accounts.id.initialize({
          client_id: config.client_id,
          callback: async (response) => {
            if (!response.credential) {
              setError("Google did not return a sign-in credential.");
              return;
            }
            try {
              await api.googleCredential(response.credential);
              window.location.assign("/");
            } catch (loginError) {
              setError(loginError instanceof Error ? loginError.message : "Google sign-in failed");
            }
          },
          auto_select: false,
          cancel_on_tap_outside: true,
        });
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          type: "standard",
          shape: "rectangular",
          text: "signin_with",
          width: 320,
        });
      } catch {
        setFallbackReady(true);
      }
    }

    setupGoogle();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="login-screen">
      <div className="login-beams" />
      <section className="login-panel">
        <div className="brand large">
          <div className="brand-mark"><Music2 size={26} /></div>
          <div>
            <strong>Santoor AI</strong>
            <span>Learning platform</span>
          </div>
        </div>
        <h1>Practice with an orchestra that follows you</h1>
        <p>Sign in with Google to keep your scores, mappings, and live accompaniment sessions private.</p>
        {error && <p className="form-error">{error}</p>}
        <div className="google-button-wrap" ref={buttonRef} />
        {fallbackReady && (
          <button
            className="google-button"
            onClick={() => {
              setError("");
              try {
                window.location.href = api.googleStartUrl();
              } catch (loginError) {
                setError(loginError instanceof Error ? loginError.message : "Google sign-in failed");
              }
            }}
          >
            <Globe2 size={20} /> Sign in or sign up with Google
          </button>
        )}
        <button
          className="guest-button"
          disabled={guestBusy}
          onClick={async () => {
            setError("");
            setGuestBusy(true);
            try {
              await api.guestLogin();
              window.location.assign("/");
            } catch (guestError) {
              setError(guestError instanceof Error ? guestError.message : "Guest session failed");
              setGuestBusy(false);
            }
          }}
        >
          <Music2 size={20} /> {guestBusy ? "Starting guest session" : "Continue as guest"}
        </button>
        <p className="guest-note">Guest projects stay in this browser session. Use Google when you want a saved account.</p>
        <div className="login-stats">
          <span><Sparkles size={16} /> MusicXML</span>
          <span><RadioTower size={16} /> Live mic sync</span>
          <span><AudioLines size={16} /> 20+ instruments</span>
        </div>
      </section>
    </div>
  );
}

function loadGoogleScript() {
  return new Promise<void>((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>('script[src="https://accounts.google.com/gsi/client"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Google sign-in script failed to load")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Google sign-in script failed to load"));
    document.head.appendChild(script);
  });
}

export default Login;
