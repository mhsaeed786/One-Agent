const statusEl = document.getElementById("status");

fetch("http://127.0.0.1:8001/mind/permissions")
  .then((r) => r.json())
  .then((d) => {
    const p = d.permissions || {};
    const web = p["web_ai_chats"];
    if (web === "granted") {
      statusEl.textContent = "✅ Mind is running and capturing";
      statusEl.className = "ok";
    } else {
      statusEl.textContent = "⏸ Mind is running but web_ai_chats sense is " +
        (web || "pending") + " — grant it to start absorbing";
      statusEl.className = "";
    }
  })
  .catch(() => {
    statusEl.textContent = "❌ Mind API not reachable (start the OneAgent API on 127.0.0.1:8001)";
    statusEl.className = "down";
  });
