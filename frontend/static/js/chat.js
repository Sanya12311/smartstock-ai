let currentSessionId = null;

async function loadSessions() {
  const list = document.getElementById("session-list");
  try {
    const sessions = await apiGet("/chat/sessions");
    if (sessions.length === 0) {
      list.innerHTML = `<div class="loading-text">No conversations yet.</div>`;
      return;
    }
    list.innerHTML = sessions
      .map(
        (s) =>
          `<div class="chat-session-item ${s.id === currentSessionId ? "active" : ""}" onclick="openSession(${s.id})">${escapeHtml(s.title)}</div>`
      )
      .join("");
  } catch (err) {
    list.innerHTML = `<div class="loading-text">Failed to load: ${escapeHtml(err.message)}</div>`;
  }
}

function renderMessage(role, content) {
  const container = document.getElementById("chat-messages");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = content;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

async function openSession(sessionId) {
  currentSessionId = sessionId;
  loadSessions();
  const container = document.getElementById("chat-messages");
  container.innerHTML = `<div class="loading-text">Loading conversation…</div>`;
  try {
    const data = await apiGet(`/chat/sessions/${sessionId}/messages`);
    container.innerHTML = "";
    data.messages.forEach((m) => renderMessage(m.role, m.content));
  } catch (err) {
    container.innerHTML = `<div class="loading-text">Failed to load conversation: ${escapeHtml(err.message)}</div>`;
  }
}

function startNewChat() {
  currentSessionId = null;
  document.getElementById("chat-messages").innerHTML =
    `<div class="loading-text" style="padding:16px;">Ask about your portfolio, a specific stock, or general concepts like "explain RSI".</div>`;
  loadSessions();
}

async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  const container = document.getElementById("chat-messages");
  if (container.querySelector(".loading-text")) container.innerHTML = "";

  renderMessage("user", message);
  input.value = "";

  const thinkingBubble = document.createElement("div");
  thinkingBubble.className = "chat-bubble assistant";
  thinkingBubble.textContent = "Thinking…";
  container.appendChild(thinkingBubble);
  container.scrollTop = container.scrollHeight;

  try {
    const result = await apiPost("/chat", { message, session_id: currentSessionId });
    currentSessionId = result.session_id;
    thinkingBubble.textContent = result.reply;
    loadSessions();
  } catch (err) {
    thinkingBubble.textContent = "Error: " + err.message;
  }
}

loadSessions();
