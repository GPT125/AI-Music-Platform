from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from backend.app.core.config import Settings, get_settings


PROVIDER_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "huggingface": "https://router.huggingface.co/v1/chat/completions",
}

DEFAULT_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "deepseek": "deepseek-chat",
    "openrouter": "openai/gpt-4o-mini",
    "openai": "gpt-4o-mini",
    "huggingface": "meta-llama/Llama-3.1-8B-Instruct",
}


def safe_model(provider_id: str, model: str) -> str:
    candidate = (model or "").strip()
    lowered = candidate.lower()
    if not candidate or lowered.startswith(("sk-", "gsk_", "hf_", "or_")) or len(candidate) > 120:
        return DEFAULT_MODELS[provider_id]
    return candidate


def configured_providers(settings: Optional[Settings] = None) -> List[Dict[str, Any]]:
    settings = settings or get_settings()
    candidates = [
        {"id": "groq", "name": "Groq", "api_key": settings.groq_api_key, "model": safe_model("groq", settings.groq_model)},
        {"id": "deepseek", "name": "DeepSeek", "api_key": settings.deepseek_api_key, "model": safe_model("deepseek", settings.deepseek_model)},
        {"id": "openrouter", "name": "OpenRouter", "api_key": settings.openrouter_api_key, "model": safe_model("openrouter", settings.openrouter_model)},
        {"id": "openai", "name": "OpenAI", "api_key": settings.openai_api_key, "model": safe_model("openai", settings.openai_model)},
        {"id": "huggingface", "name": "Hugging Face", "api_key": settings.huggingface_api_key, "model": safe_model("huggingface", settings.huggingface_model)},
    ]
    configured = []
    for item in candidates:
        if item["api_key"] and item["model"]:
            configured.append({key: value for key, value in item.items() if key != "api_key"})
    if settings.ai_provider:
        configured.sort(key=lambda item: 0 if item["id"] == settings.ai_provider else 1)
    return configured


def ai_status(settings: Optional[Settings] = None) -> Dict[str, Any]:
    providers = configured_providers(settings)
    return {
        "configured": bool(providers),
        "active_provider": providers[0]["id"] if providers else None,
        "providers": providers,
        "features": ["score_feedback", "practice_plan", "santoor_technique_review"],
    }


async def chat_json(messages: List[Dict[str, str]], settings: Optional[Settings] = None) -> Dict[str, Any]:
    settings = settings or get_settings()
    providers = configured_providers(settings)
    if not providers:
        raise RuntimeError("No AI provider is configured")

    last_error = "AI provider request failed"
    async with httpx.AsyncClient(timeout=24) as client:
        for provider in providers:
            try:
                parsed = await _chat_json_with_provider(client, provider, messages, settings, json_mode=True)
            except httpx.HTTPStatusError as exc:
                last_error = f"{provider['name']} returned HTTP {exc.response.status_code}"
                if exc.response.status_code not in {400, 422}:
                    continue
                try:
                    parsed = await _chat_json_with_provider(client, provider, messages, settings, json_mode=False)
                except Exception:
                    continue
            except Exception as exc:
                last_error = f"{provider['name']} request failed: {type(exc).__name__}"
                continue
            parsed["_provider"] = provider["id"]
            parsed["_model"] = provider["model"]
            return parsed
    raise RuntimeError(last_error)


async def _chat_json_with_provider(
    client: httpx.AsyncClient,
    provider: Dict[str, Any],
    messages: List[Dict[str, str]],
    settings: Settings,
    json_mode: bool,
) -> Dict[str, Any]:
    key = getattr(settings, f"{provider['id']}_api_key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if provider["id"] == "openrouter":
        headers["HTTP-Referer"] = settings.openrouter_referer or settings.app_base_url
        headers["X-Title"] = "Santoor AI Learning Platform"

    payload: Dict[str, Any] = {
        "model": provider["model"],
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 900,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    response = await client.post(PROVIDER_ENDPOINTS[provider["id"]], headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return parse_json_content(content)


def parse_json_content(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise


def fallback_feedback(score_events: List[Dict[str, Any]], reason: str = "") -> Dict[str, Any]:
    count = len(score_events)
    mapped_errors = [int(event.get("mapping_error_cents", 0)) for event in score_events]
    max_error = max(mapped_errors or [0])
    labels = [event.get("ui_label", event.get("note_name", "note")) for event in score_events[:8]]
    return {
        "summary": f"Score contains {count} mapped Santoor notes. Focus on clean mallet alternation and even resonance.",
        "practice_plan": [
            "Clap the rhythm once before playing.",
            "Practice the first phrase at 60 percent speed with alternating right and left mallets.",
            "Loop the hardest two-note bridge change until it feels relaxed.",
        ],
        "technical_notes": [
            "Keep both wrists loose and let the mallet rebound naturally.",
            "Listen for equal volume between left and right mallet strokes.",
        ],
        "rhythm_notes": ["Use a metronome and only increase tempo after two clean repetitions."],
        "santoor_notes": [
            f"Opening notes: {', '.join(labels) if labels else 'none yet'}.",
            "Check tuning before recording; Persian Santoor quarter-tone notes require careful listening.",
        ],
        "risk_flags": ["AI provider unavailable; showing deterministic coach feedback."] if reason else [],
        "confidence": 0.62 if count else 0.2,
        "_provider": "deterministic",
        "_model": "local-fallback",
    }


async def generate_practice_feedback(project_name: str, score_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not score_events:
        return fallback_feedback(score_events, "No score events are available")
    compact_events = [
        {
            "label": event.get("ui_label"),
            "pitch": event.get("midi_note"),
            "onset_s": event.get("onset_s"),
            "duration_s": event.get("duration_s"),
            "bridge": event.get("bridge_id"),
            "region": event.get("region"),
            "mallet": event.get("technique", {}).get("mallet"),
            "mapping_error_cents": event.get("mapping_error_cents"),
        }
        for event in score_events[:80]
    ]
    messages = [
        {
            "role": "system",
            "content": (
                "You are a Persian Santoor practice coach. Return strict JSON with keys: "
                "summary, practice_plan, technical_notes, rhythm_notes, santoor_notes, risk_flags, confidence. "
                "Be specific to bridges, mallet alternation, rhythm, tuning, and performance readiness."
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"project": project_name, "events": compact_events}, ensure_ascii=True),
        },
    ]
    try:
        feedback = await chat_json(messages)
    except Exception as exc:
        return fallback_feedback(score_events, str(exc))
    return {
        "summary": str(feedback.get("summary", ""))[:1200],
        "practice_plan": list(feedback.get("practice_plan", []))[:8],
        "technical_notes": list(feedback.get("technical_notes", []))[:8],
        "rhythm_notes": list(feedback.get("rhythm_notes", []))[:8],
        "santoor_notes": list(feedback.get("santoor_notes", []))[:8],
        "risk_flags": list(feedback.get("risk_flags", []))[:8],
        "confidence": float(feedback.get("confidence", 0.75)),
        "_provider": feedback.get("_provider", "unknown"),
        "_model": feedback.get("_model", "unknown"),
    }
