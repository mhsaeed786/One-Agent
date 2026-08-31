// Mind Capture — content script
// Captures YOUR prompts on supported AI chat sites and forwards them to the
// local Mind API (127.0.0.1:8001). Only user-authored text is captured —
// never assistant replies, never page content.

const API = "http://127.0.0.1:8001/mind/capture";
const DEDUPE_KEY = "mind_capture_seen";

function host() { return location.hostname.replace(/^www\./, ""); }

// --- per-site selectors: prompt input / send button -------------------------
const SITES = {
  "chatgpt.com":      { input: "#prompt-textarea", send: "[data-testid='send-button']" },
  "chat.openai.com":  { input: "#prompt-textarea", send: "[data-testid='send-button']" },
  "gemini.google.com":{ input: "div.ql-editor[contenteditable='true']", send: "button.send-button" },
  "claude.ai":        { input: "div[contenteditable='true'].ProseMirror", send: "button[aria-label='Send message']" },
  "www.perplexity.ai":{ input: "textarea[placeholder*='Ask']", send: "button[aria-label='Submit']" },
  "copilot.microsoft.com": { input: "textarea", send: "button[aria-label='Submit']" },
  "chat.mistral.ai":  { input: "textarea", send: "button[aria-label='Send']" },
  "www.kimi.com":     { input: "textarea", send: "button[aria-label='Send']" },
  "chat.deepseek.com":{ input: "textarea", send: "div[role='button']:has(svg)" },
  "x.com":            { input: "textarea[data-testid='grokTextarea']", send: "button[data-testid='grokSendButton']" },
};

const site = SITES[location.hostname.replace(/^www\./, "")] ||
             SITES[location.hostname] || null;

async function seen(id) {
  const d = await chrome.storage.local.get(DEDUPE_KEY);
  const set = new Set(d[DEDUPE_KEY] || []);
  if (set.has(id)) return true;
  set.add(id);
  // keep the set bounded
  if (set.size > 500) set.delete([...set][0]);
  await chrome.storage.local.set({ [DEDUPE_KEY]: [...set] });
  return false;
}

function readInput(el) {
  if (!el) return "";
  if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") return el.value || "";
  return el.innerText || el.textContent || "";   // contenteditable
}

async function capture() {
  if (!site) return;
  const text = readInput(document.querySelector(site.input)).trim();
  if (text.length < 25) return;  // ignore trivial strings
  const id = host() + ":" + text.slice(0, 120);
  if (await seen(id)) return;

  try {
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool: "web:" + host(),
        kind: "instruction",
        title: text.slice(0, 90),
        text: text.slice(0, 4000),
        uri: location.href,
      }),
    });
    if (!res.ok) console.warn("[mind-capture] api returned", res.status);
  } catch (e) {
    // Mind API not running — stay silent, retry next send
  }
}

// Capture at send-time: clicking send OR pressing Enter in the input.
if (site) {
  document.addEventListener("click", (ev) => {
    if (site.send && ev.target.closest && ev.target.closest(site.send)) {
      setTimeout(capture, 150);
    }
  }, true);

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey &&
        document.activeElement &&
        document.activeElement.matches && document.activeElement.matches(site.input)) {
      setTimeout(capture, 150);
    }
  }, true);
}
