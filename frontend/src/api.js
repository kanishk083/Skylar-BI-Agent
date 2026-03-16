// api.js — SSE streaming + REST calls
// Patch 6: pingBackend() warmup + AbortController 70s timeout + onError callback

const BASE = import.meta.env.VITE_BACKEND_URL;
const KEY  = import.meta.env.VITE_API_KEY;

// Patch 6: warmup ping — called on app mount
export async function pingBackend() {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 5000);
    const r = await fetch(`${BASE}/health`, { signal: ctrl.signal });
    return r.ok;
  } catch {
    return false;
  }
}

// Patch 6: 70s timeout, onError callback for AbortError
export async function streamChat(sessionId, query, onChunk, onDone, onError) {
  const ctrl = new AbortController();
  const timeout = setTimeout(() => ctrl.abort(), 70000);

  try {
    const resp = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": KEY,
      },
      body: JSON.stringify({ session_id: sessionId, query }),
      signal: ctrl.signal,
    });

    if (!resp.ok) {
      onError(`Server error ${resp.status} — please retry.`);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split("\n");
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") {
          onDone();
          return;
        }
        try {
          const { chunk } = JSON.parse(payload);
          if (chunk) onChunk(chunk);
        } catch {
          // malformed SSE frame — skip
        }
      }
    }
    onDone();
  } catch (e) {
    if (e.name === "AbortError") {
      onError("Request timed out. Backend may be waking up — please retry in a moment.");
    } else {
      onError(`Connection error: ${e.message}`);
    }
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchBriefing(onChunk, onDone, onError) {
  const ctrl = new AbortController();
  const timeout = setTimeout(() => ctrl.abort(), 70000);

  try {
    const resp = await fetch(`${BASE}/briefing`, {
      headers: { "x-api-key": KEY },
      signal: ctrl.signal,
    });

    if (!resp.ok) {
      onError(`Briefing error ${resp.status}`);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split("\n");
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") { onDone(); return; }
        try {
          const { chunk } = JSON.parse(payload);
          if (chunk) onChunk(chunk);
        } catch { /* skip */ }
      }
    }
    onDone();
  } catch (e) {
    onError(e.name === "AbortError" ? "Briefing timed out — retry." : e.message);
  } finally {
    clearTimeout(timeout);
  }
}
