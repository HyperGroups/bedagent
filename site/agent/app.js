import {
  buildOutlineMarkdown,
  downloadText,
  loadSession,
  processAnswer,
  processFragment,
  resetSession,
  saveSession,
} from "./story-engine.js";

const API_CANDIDATES = ["http://127.0.0.1:8765", "http://localhost:8765"];

let state = loadSession();
let apiBase = null;
let mediaRecorder = null;
let audioChunks = [];
let recordedBlob = null;
let remoteStoryId = localStorage.getItem("bedagent.story.id") || "";

const els = {
  modeCards: document.querySelectorAll(".mode-card"),
  panelModeLabel: document.getElementById("panel-mode-label"),
  sessionTitle: document.getElementById("session-title"),
  transcript: document.getElementById("transcript"),
  storyControls: document.getElementById("story-controls"),
  mvpControls: document.getElementById("mvp-controls"),
  voiceControls: document.getElementById("voice-controls"),
  fragmentInput: document.getElementById("fragment-input"),
  mvpIdea: document.getElementById("mvp-idea"),
  statTurns: document.getElementById("stat-turns"),
  statOpen: document.getElementById("stat-open"),
  statChars: document.getElementById("stat-chars"),
  bibleMain: document.getElementById("bible-main-thread"),
  bibleCharacters: document.getElementById("bible-characters"),
  bibleThreads: document.getElementById("bible-threads"),
  bibleQuestions: document.getElementById("bible-questions"),
  bibleTimeline: document.getElementById("bible-timeline"),
  sessionPicker: document.getElementById("session-picker"),
  storySearch: document.getElementById("story-search"),
  searchHits: document.getElementById("search-hits"),
  apiStatus: document.getElementById("api-status"),
  apiStatusCard: document.getElementById("api-status-card"),
  apiBaseHint: document.getElementById("api-base-hint"),
  recordStatus: document.getElementById("record-status"),
  playback: document.getElementById("playback"),
};

function renderTranscript() {
  els.transcript.innerHTML = "";
  if (!state.session.turns.length) {
    appendSystem("开始口述你的故事片段。Sage 会追问，Focus 会帮你剪枝。");
    return;
  }
  for (const turn of state.session.turns) {
    if (turn.kind === "fragment") {
      appendMessage("user", "你", turn.fragment);
      appendMessage("agent", "Sage", turn.agent_reply);
    } else if (turn.kind === "answer") {
      appendMessage("user", "对齐", turn.answer);
      appendMessage("agent", "Sage", turn.agent_reply);
    }
  }
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

function appendMessage(role, label, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `<span class="msg-meta">${label}</span><pre></pre>`;
  div.querySelector("pre").textContent = text;
  els.transcript.appendChild(div);
}

function appendSystem(text) {
  const div = document.createElement("div");
  div.className = "msg system";
  div.textContent = text;
  els.transcript.appendChild(div);
}

function renderBible() {
  const { session, bible } = state;
  els.sessionTitle.textContent = bible.title || session.title;
  els.statTurns.textContent = String(session.turn_count);
  els.statOpen.textContent = String(bible.open_questions.length);
  els.statChars.textContent = String(bible.characters.length);
  els.bibleMain.textContent = bible.main_thread;

  els.bibleCharacters.innerHTML = "";
  for (const c of bible.characters) {
    const li = document.createElement("li");
    li.textContent = `${c.name}：${(c.notes || []).slice(0, 2).join("；") || "待补充"}`;
    els.bibleCharacters.appendChild(li);
  }

  els.bibleThreads.innerHTML = "";
  for (const t of bible.plot_threads.filter((x) => x.status === "active")) {
    const li = document.createElement("li");
    li.textContent = t.label;
    els.bibleThreads.appendChild(li);
  }

  els.bibleQuestions.innerHTML = "";
  for (const q of bible.open_questions) {
    const li = document.createElement("li");
    li.textContent = q;
    els.bibleQuestions.appendChild(li);
  }

  els.bibleTimeline.innerHTML = "";
  for (const item of bible.timeline.slice(-8)) {
    const li = document.createElement("li");
    const kind = item.kind === "fragment" ? "口述" : "对齐";
    li.textContent = `[${item.turn}/${kind}] ${item.text}`;
    els.bibleTimeline.appendChild(li);
  }
}

function persist() {
  saveSession(state.session, state.bible);
  renderTranscript();
  renderBible();
}

function setMode(mode) {
  els.modeCards.forEach((card) => {
    const active = card.dataset.mode === mode;
    card.classList.toggle("active", active);
    card.setAttribute("aria-selected", active ? "true" : "false");
  });

  els.storyControls.classList.toggle("hidden", mode !== "story");
  els.mvpControls.classList.toggle("hidden", mode !== "mvp");
  els.voiceControls.classList.toggle("hidden", mode !== "voice");

  const labels = {
    story: "Story · 口述模式",
    mvp: "MVP · 闭环模式",
    voice: "Voice · 语音口述",
  };
  els.panelModeLabel.textContent = labels[mode] || "Agent";
}

async function detectApi() {
  for (const base of API_CANDIDATES) {
    try {
      const res = await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        apiBase = base;
        const health = await res.json();
        const llmNote = health.llm?.usable ? " · LLM 可用" : "";
        els.apiStatus.textContent = `已连接 ${base}${llmNote}`;
        els.apiStatus.className = "api-status-value ok";
        els.apiBaseHint.textContent = `API: ${base}`;
        await refreshRemoteSessions();
        return;
      }
    } catch {
      /* try next */
    }
  }
  apiBase = null;
  els.apiStatus.textContent = "未连接 — 仅 Story 浏览器模式可用";
  els.apiStatus.className = "api-status-value fail";
}

async function refreshRemoteSessions() {
  if (!apiBase || !els.sessionPicker) return;
  try {
    const res = await fetch(`${apiBase}/api/story/list`);
    const data = await res.json();
    const items = data.items || [];
    els.sessionPicker.innerHTML = '<option value="">本机草稿</option>';
    for (const item of items) {
      const opt = document.createElement("option");
      opt.value = item.story_id;
      opt.textContent = `${item.title} (${item.turn_count} 回合)`;
      if (item.story_id === remoteStoryId) opt.selected = true;
      els.sessionPicker.appendChild(opt);
    }
  } catch {
    /* ignore */
  }
}

async function loadRemoteStory(storyId) {
  if (!apiBase || !storyId) return;
  const res = await fetch(`${apiBase}/api/story/${encodeURIComponent(storyId)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "load story failed");
  remoteStoryId = storyId;
  localStorage.setItem("bedagent.story.id", storyId);
  state.session = data.session;
  state.session.turns = state.session.turns || [];
  state.bible = data.bible;
  persist();
}

async function handleSendFragment() {
  const text = els.fragmentInput.value.trim();
  if (!text) return;
  try {
    if (apiBase) {
      const res = await fetch(`${apiBase}/api/story/fragment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fragment: text,
          title: state.bible.title,
          story_id: remoteStoryId || undefined,
          auto_confirm: true,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "story fragment failed");
      remoteStoryId = data.story_id;
      localStorage.setItem("bedagent.story.id", remoteStoryId);
      state.session = data.session;
      state.session.turns = state.session.turns || [];
      if (data.agent_reply) {
        state.session.turns.push({
          kind: "fragment",
          fragment: text,
          agent_reply: data.agent_reply,
        });
      }
      state.bible = data.bible;
      els.fragmentInput.value = "";
      persist();
      refreshRemoteSessions();
      return;
    }
    const result = processFragment(state.session, state.bible, text, true);
    state.session = result.session;
    state.bible = result.bible;
    els.fragmentInput.value = "";
    persist();
  } catch (err) {
    appendSystem(err.message || String(err));
  }
}

async function handleSendAnswer() {
  const text = els.fragmentInput.value.trim();
  if (!text) return;
  try {
    if (apiBase && remoteStoryId) {
      const res = await fetch(`${apiBase}/api/story/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: text, story_id: remoteStoryId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "story answer failed");
      state.session = data.session;
      state.session.turns = state.session.turns || [];
      state.session.turns.push({ kind: "answer", answer: text, agent_reply: data.agent_reply });
      state.bible = data.bible;
      els.fragmentInput.value = "";
      persist();
      return;
    }
    const result = processAnswer(state.session, state.bible, text);
    state.session = result.session;
    state.bible = result.bible;
    els.fragmentInput.value = "";
    persist();
  } catch (err) {
    appendSystem(err.message || String(err));
  }
}

async function handleStorySearch() {
  const query = (els.storySearch?.value || "").trim();
  if (!query || !els.searchHits) return;
  els.searchHits.innerHTML = "";
  if (!apiBase) {
    appendSystem("故事检索需要本地 API");
    return;
  }
  try {
    const res = await fetch(`${apiBase}/api/story/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "search failed");
    for (const hit of data.hits || []) {
      const li = document.createElement("li");
      li.textContent = `${hit.score.toFixed(2)} ${hit.entry.title}: ${hit.entry.main_thread}`;
      li.style.cursor = "pointer";
      li.addEventListener("click", () => loadRemoteStory(hit.entry.story_id).catch((err) => appendSystem(err.message)));
      els.searchHits.appendChild(li);
    }
    if (!(data.hits || []).length) {
      const li = document.createElement("li");
      li.textContent = "没有匹配";
      els.searchHits.appendChild(li);
    }
  } catch (err) {
    appendSystem(err.message || String(err));
  }
}

async function handleMvpRun() {
  if (!apiBase) {
    appendSystem("请先启动本地 API: python3 mvp/bedagent_web.py");
    setMode("mvp");
    return;
  }
  const idea = els.mvpIdea.value.trim();
  if (!idea) return;
  appendSystem("正在调用 MVP run…");
  try {
    const res = await fetch(`${apiBase}/api/mvp/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea, auto_confirm: true }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "MVP run failed");
    appendMessage("agent", "MVP", [
      `run_id: ${data.run_id}`,
      `risk: ${data.risk}`,
      `pillow_note: ${data.pillow_note}`,
    ].join("\n"));
    els.transcript.scrollTop = els.transcript.scrollHeight;
  } catch (err) {
    appendSystem(err.message || String(err));
  }
}

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia) {
    els.recordStatus.textContent = "浏览器不支持录音";
    return;
  }
  if (mediaRecorder?.state === "recording") {
    mediaRecorder.stop();
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
  mediaRecorder.onstop = () => {
    recordedBlob = new Blob(audioChunks, { type: "audio/webm" });
    els.playback.src = URL.createObjectURL(recordedBlob);
    els.playback.classList.remove("hidden");
    els.recordStatus.textContent = "录音完成";
    els.recordStatus.classList.remove("recording");
    stream.getTracks().forEach((t) => t.stop());
  };
  mediaRecorder.start();
  els.recordStatus.textContent = "录音中… 再次点击停止";
  els.recordStatus.classList.add("recording");
}

async function handleVoiceTranscribe() {
  if (!apiBase) {
    appendSystem("语音转写需要本地 API 与 DASHSCOPE_API_KEY");
    return;
  }
  if (!recordedBlob) {
    appendSystem("请先录音");
    return;
  }
  appendSystem("正在转写…");
  const form = new FormData();
  form.append("audio", recordedBlob, "recording.webm");
  try {
    const res = await fetch(`${apiBase}/api/voice/transcribe`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "transcribe failed");
    els.fragmentInput.value = data.text;
    setMode("story");
    handleSendFragment();
  } catch (err) {
    appendSystem(err.message || String(err));
  }
}

function bindEvents() {
  els.modeCards.forEach((card) => {
    card.addEventListener("click", () => setMode(card.dataset.mode));
  });

  document.getElementById("btn-send-fragment").addEventListener("click", handleSendFragment);
  document.getElementById("btn-send-answer").addEventListener("click", handleSendAnswer);
  document.getElementById("btn-mvp-run").addEventListener("click", handleMvpRun);
  document.getElementById("btn-record").addEventListener("click", () => startRecording().catch(console.error));
  document.getElementById("btn-voice-transcribe").addEventListener("click", handleVoiceTranscribe);

  document.getElementById("btn-new-session").addEventListener("click", () => {
    const title = prompt("故事标题", state.bible.title || "未命名故事");
    if (title === null) return;
    remoteStoryId = "";
    localStorage.removeItem("bedagent.story.id");
    state = resetSession(title || "未命名故事");
    persist();
  });

  els.sessionPicker?.addEventListener("change", () => {
    const id = els.sessionPicker.value;
    if (!id) return;
    loadRemoteStory(id).catch((err) => appendSystem(err.message || String(err)));
  });

  document.getElementById("btn-story-search")?.addEventListener("click", handleStorySearch);
  els.storySearch?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleStorySearch();
    }
  });

  document.getElementById("btn-export-md").addEventListener("click", () => {
    downloadText(`${state.bible.title || "story"}.md`, buildOutlineMarkdown(state.session, state.bible));
  });

  document.getElementById("btn-export-json").addEventListener("click", () => {
    downloadText(
      `${state.bible.title || "story"}.json`,
      JSON.stringify({ session: state.session, bible: state.bible }, null, 2),
    );
  });

  els.fragmentInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSendFragment();
    }
  });
}

bindEvents();
setMode("story");
persist();
detectApi();
