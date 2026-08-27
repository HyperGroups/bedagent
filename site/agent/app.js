import {
  buildChapterProse,
  buildChapterSketch,
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
let recordAnalyser = null;
let recordContext = null;
let autoStopRaf = 0;

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
  quiet: document.getElementById("chk-quiet"),
};

function quietEnabled() {
  return Boolean(els.quiet?.checked);
}

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
    const role = c.role === "protagonist" ? "主角" : c.role === "antagonist" ? "对手" : c.role === "ally" ? "同伴" : "";
    const extra = [role, c.desire ? `想要${c.desire}` : ""].filter(Boolean).join(" · ");
    li.textContent = `${c.name}${extra ? `（${extra}）` : ""}：${(c.notes || []).slice(0, 2).join("；") || "待补充"}`;
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
        const quietNote = quietEnabled() ? " · 夜间" : "";
        els.apiStatus.textContent = `已连接 ${base} · ${health.product_milestone || "v0.12"}${llmNote}${quietNote}`;
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

function stopPlayback() {
  if (!els.playback) return;
  try {
    els.playback.pause();
    els.playback.currentTime = 0;
  } catch {
    /* ignore */
  }
}

function showPartials(partials) {
  const box = document.getElementById("voice-partials");
  if (!box) return;
  if (!partials?.length) {
    box.textContent = "";
    return;
  }
  box.textContent = partials.map((p) => p.text).join(" → ");
}

function voiceLoopEnabled() {
  return document.getElementById("chk-voice-loop")?.checked !== false;
}

function autoStopEnabled() {
  return document.getElementById("chk-auto-stop")?.checked !== false;
}

function vadEnabled() {
  return document.getElementById("chk-vad")?.checked !== false;
}

function stopRecordMeter() {
  if (autoStopRaf) {
    cancelAnimationFrame(autoStopRaf);
    autoStopRaf = 0;
  }
  try {
    recordContext?.close();
  } catch {
    /* ignore */
  }
  recordContext = null;
  recordAnalyser = null;
}

function startSilenceWatch(stream) {
  if (!autoStopEnabled() || !window.AudioContext) return;
  try {
    recordContext = new AudioContext();
    const source = recordContext.createMediaStreamSource(stream);
    recordAnalyser = recordContext.createAnalyser();
    recordAnalyser.fftSize = 2048;
    source.connect(recordAnalyser);
    const data = new Uint8Array(recordAnalyser.fftSize);
    let heardSpeech = false;
    let silentMs = 0;
    let last = performance.now();
    const tick = () => {
      if (mediaRecorder?.state !== "recording") return;
      recordAnalyser.getByteTimeDomainData(data);
      let sum = 0;
      for (const value of data) {
        const n = (value - 128) / 128;
        sum += n * n;
      }
      const rms = Math.sqrt(sum / data.length);
      const now = performance.now();
      const dt = now - last;
      last = now;
      if (rms > 0.045) {
        heardSpeech = true;
        silentMs = 0;
        els.recordStatus.textContent = "录音中… 检测到语音";
      } else if (heardSpeech) {
        silentMs += dt;
        els.recordStatus.textContent = `录音中… 静音 ${Math.round(silentMs)}ms`;
        if (silentMs > 1200) {
          mediaRecorder.stop();
          return;
        }
      }
      autoStopRaf = requestAnimationFrame(tick);
    };
    autoStopRaf = requestAnimationFrame(tick);
  } catch {
    /* analyser optional */
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
  stopPlayback();
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
  mediaRecorder.onstop = () => {
    stopRecordMeter();
    recordedBlob = new Blob(audioChunks, { type: "audio/webm" });
    els.playback.src = URL.createObjectURL(recordedBlob);
    els.playback.classList.remove("hidden");
    els.recordStatus.textContent = "录音完成";
    els.recordStatus.classList.remove("recording");
    stream.getTracks().forEach((t) => t.stop());
    if (voiceLoopEnabled()) {
      handleVoiceClosedLoop().catch((err) => appendSystem(err.message || String(err)));
    }
  };
  mediaRecorder.start();
  startSilenceWatch(stream);
  els.recordStatus.textContent = autoStopEnabled()
    ? "录音中… 说完停顿即自动停止"
    : "录音中… 松开或再次点击停止";
  els.recordStatus.classList.add("recording");
}

async function handleVoiceClosedLoop() {
  if (!apiBase) {
    appendSystem("语音闭环需要本地 API");
    return;
  }
  if (!recordedBlob) {
    appendSystem("请先录音");
    return;
  }
  appendSystem("语音闭环：转写 → Sage → TTS…");
  const form = new FormData();
  form.append("audio", recordedBlob, "recording.webm");
  form.append("title", state.bible.title || "未命名故事");
  if (remoteStoryId) form.append("story_id", remoteStoryId);
  form.append("quiet", quietEnabled() ? "1" : "0");
  form.append("auto_confirm", "1");
  form.append("include_audio", "1");
  form.append("vad", vadEnabled() ? "1" : "0");
  const res = await fetch(`${apiBase}/api/voice/story`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "voice story failed");
  showPartials(data.partials || []);
  if ((data.turns || []).length > 1) {
    appendSystem(`VAD 分成 ${data.turns.length} 轮口述`);
  }
  if (data.skipped) {
    appendSystem(`已跳过：${data.skip_reason || data.command || "silence"}`);
    if (data.command === "/recap" || data.command === "/resume") {
      handleResumeLatest();
    }
    return;
  }
  remoteStoryId = data.story_id;
  localStorage.setItem("bedagent.story.id", remoteStoryId);
  state.session = data.session;
  state.session.turns = state.session.turns || [];
  if (data.transcript && data.agent_reply) {
    state.session.turns.push({
      kind: "fragment",
      fragment: data.transcript,
      agent_reply: data.agent_reply,
    });
  }
  state.bible = data.bible;
  persist();
  refreshRemoteSessions();
  if (data.reply_audio_base64) {
    const bytes = Uint8Array.from(atob(data.reply_audio_base64), (c) => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: data.reply_audio_mime || "audio/wav" });
    els.playback.src = URL.createObjectURL(blob);
    els.playback.classList.remove("hidden");
    if (!quietEnabled()) {
      els.playback.play().catch(() => {});
    }
  }
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
  if (voiceLoopEnabled()) {
    await handleVoiceClosedLoop();
    return;
  }
  appendSystem("正在转写…");
  const form = new FormData();
  form.append("audio", recordedBlob, "recording.webm");
  form.append("stream", "1");
  form.append("vad", vadEnabled() ? "1" : "0");
  try {
    const res = await fetch(`${apiBase}/api/voice/transcribe`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "transcribe failed");
    showPartials(data.partials || []);
    els.fragmentInput.value = data.text;
    setMode("story");
    handleSendFragment();
  } catch (err) {
    appendSystem(err.message || String(err));
  }
}

async function handleResumeLatest() {
  if (!apiBase) {
    appendSystem("恢复最近会话需要本地 API");
    return;
  }
  try {
    const res = await fetch(`${apiBase}/api/story/latest`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "没有可恢复的故事");
    await loadRemoteStory(data.story_id);
    appendSystem(`已恢复 ${data.story_id}`);
    refreshRemoteSessions();
  } catch (err) {
    appendSystem(err.message || String(err));
  }
}

async function handleDraft(expand = false) {
  try {
    if (apiBase && remoteStoryId) {
      const res = await fetch(`${apiBase}/api/story/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          story_id: remoteStoryId,
          expand,
          night: quietEnabled(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "draft failed");
      const text = expand ? data.prose || data.sketch : data.sketch || data.outline;
      appendMessage("agent", expand ? "扩写" : "草稿", text);
      els.transcript.scrollTop = els.transcript.scrollHeight;
      return;
    }
    const text = expand ? buildChapterProse(state.session, state.bible) : buildChapterSketch(state.session, state.bible);
    appendMessage("agent", expand ? "扩写" : "草稿", text);
    downloadText(`${state.bible.title || "story"}-${expand ? "prose" : "sketch"}.md`, text);
  } catch (err) {
    appendSystem(err.message || String(err));
  }
}

async function handleSpeak() {
  const last = [...(state.session.turns || [])].reverse().find((t) => t.agent_reply);
  const text = last?.agent_reply || state.bible.main_thread || "";
  if (!text) {
    appendSystem("还没有可朗读的内容");
    return;
  }
  if (!apiBase) {
    appendSystem("朗读需要本地 API");
    return;
  }
  appendSystem(quietEnabled() ? "夜间朗读中…" : "朗读中…");
  try {
    const res = await fetch(`${apiBase}/api/voice/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, quiet: quietEnabled() }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "speak failed");
    }
    const blob = await res.blob();
    els.playback.src = URL.createObjectURL(blob);
    els.playback.classList.remove("hidden");
    if (!quietEnabled()) {
      els.playback.play().catch(() => {});
    }
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
  const recordBtn = document.getElementById("btn-record");
  let usedPointerHold = false;
  recordBtn.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    usedPointerHold = true;
    try {
      recordBtn.setPointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    if (mediaRecorder?.state !== "recording") {
      startRecording().catch(console.error);
    }
  });
  const stopIfRecording = () => {
    if (mediaRecorder?.state === "recording") mediaRecorder.stop();
  };
  recordBtn.addEventListener("pointerup", stopIfRecording);
  recordBtn.addEventListener("pointercancel", stopIfRecording);
  recordBtn.addEventListener("click", (e) => {
    if (usedPointerHold) {
      e.preventDefault();
      usedPointerHold = false;
      return;
    }
    startRecording().catch(console.error);
  });
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

  document.getElementById("btn-resume")?.addEventListener("click", () => {
    handleResumeLatest().catch((err) => appendSystem(err.message || String(err)));
  });
  document.getElementById("btn-draft")?.addEventListener("click", () => handleDraft(false));
  document.getElementById("btn-expand")?.addEventListener("click", () => handleDraft(true));
  document.getElementById("btn-speak")?.addEventListener("click", () => handleSpeak());
  els.quiet?.addEventListener("change", () => {
    localStorage.setItem("bedagent.quiet", quietEnabled() ? "1" : "0");
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
if (localStorage.getItem("bedagent.quiet") === "1" && els.quiet) {
  els.quiet.checked = true;
}
persist();
detectApi();
