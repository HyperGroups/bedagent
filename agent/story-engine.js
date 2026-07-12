const STORAGE_KEY = "bedagent.story.session.v1";

const CATEGORY_HINTS = {
  character: ["主角", "角色", "名叫", "性格", "他", "她"],
  plot: ["然后", "突然", "结局", "转折", "冲突", "发现"],
  world: ["世界", "背景", "时代", "设定", "文明", "星球"],
  dialogue: ["\"", "'", "说", "道", "问", "回答"],
  theme: ["主题", "隐喻", "象征", "意义"],
};

const RED_KEYWORDS = ["删除角色", "重写全书", "全部推翻", "改结局", "杀死主角"];
const YELLOW_KEYWORDS = ["改主线", "换主角", "反转", "其实是", "其实", "时间线"];

export function emptyBible(title = "未命名故事") {
  const now = new Date().toISOString();
  return {
    schema_version: "1.0.0",
    title,
    created_at: now,
    updated_at: now,
    main_thread: "（等待第一段口述）",
    characters: [],
    plot_threads: [],
    setting: { time: "", place: "", notes: [] },
    timeline: [],
    open_questions: [],
    resolved_questions: [],
    recent_recap: "",
    fragment_count: 0,
    turn_count: 0,
  };
}

export function emptySession(title = "未命名故事") {
  return {
    title,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    mode: "web_story",
    turn_count: 0,
    turns: [],
  };
}

export function loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { session: emptySession(), bible: emptyBible() };
    const data = JSON.parse(raw);
    return {
      session: data.session || emptySession(),
      bible: data.bible || emptyBible(data.session?.title),
    };
  } catch {
    return { session: emptySession(), bible: emptyBible() };
  }
}

export function saveSession(session, bible) {
  session.updated_at = new Date().toISOString();
  bible.updated_at = session.updated_at;
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ session, bible }));
}

export function resetSession(title = "未命名故事") {
  const session = emptySession(title);
  const bible = emptyBible(title);
  saveSession(session, bible);
  return { session, bible };
}

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function firstSentence(value, maxLen = 140) {
  const text = cleanText(value);
  if (!text) return "（尚未口述）";
  const parts = text.split(/[。！？.!?]/);
  const summary = (parts[0] || text).trim();
  return summary.length <= maxLen ? summary : `${summary.slice(0, maxLen - 3).trim()}...`;
}

function tokenSet(value) {
  const matches = String(value).toLowerCase().match(/[\u4e00-\u9fff]{2,}|[a-zA-Z]{4,}/g);
  return new Set(matches || []);
}

function detectCategory(fragment) {
  const lower = fragment.toLowerCase();
  let best = "misc";
  let bestScore = 0;
  for (const [category, hints] of Object.entries(CATEGORY_HINTS)) {
    let score = 0;
    for (const hint of hints) {
      if (lower.includes(hint.toLowerCase())) score += 1;
    }
    if (score > bestScore) {
      bestScore = score;
      best = category;
    }
  }
  return best;
}

function extractThreads(fragment) {
  const raw = fragment.split(/\n+|[；;]/);
  const cleaned = raw.map(cleanText).filter(Boolean);
  return cleaned.length ? cleaned.slice(0, 8) : [cleanText(fragment) || "（空片段）"];
}

function extractCharacterHints(fragment) {
  const hints = [];
  const patterns = [
    /名叫([\u4e00-\u9fffA-Za-z·]{1,12})/g,
    /叫([\u4e00-\u9fffA-Za-z·]{1,12})/g,
    /([\u4e00-\u9fffA-Za-z·]{1,12})是主角/g,
  ];
  for (const pattern of patterns) {
    for (const match of fragment.matchAll(pattern)) {
      const name = cleanText(match[1]);
      if (name && !hints.includes(name)) hints.push(name);
    }
  }
  return hints.slice(0, 5);
}

function classifyFocusAction(thread, mainThread) {
  const threadL = thread.toLowerCase();
  const mainL = mainThread.toLowerCase();
  if (threadL.length < 8) return "prune";
  if (/也许|可能|或者|maybe|perhaps/.test(threadL)) return "park";
  const shared = [...tokenSet(threadL)].filter((t) => tokenSet(mainL).has(t));
  if (shared.length >= 2) return "expand";
  if (shared.length === 1) return "merge";
  if (/冲突|转折|秘密|真相|twist/.test(threadL)) return "expand";
  return "park";
}

function proposeMainThread(fragment, bible, category) {
  const recap = firstSentence(fragment);
  const current = bible.main_thread || "（等待第一段口述）";
  if (current.startsWith("（等待")) return recap;
  if (["plot", "character", "theme"].includes(category)) return recap;
  return current;
}

function detectPivot(oldThread, newThread) {
  if (oldThread.startsWith("（等待")) return false;
  const oldTokens = tokenSet(oldThread);
  const newTokens = tokenSet(newThread);
  if (!oldTokens.size || !newTokens.size) return false;
  const union = new Set([...oldTokens, ...newTokens]);
  let overlap = 0;
  for (const t of oldTokens) if (newTokens.has(t)) overlap += 1;
  return overlap / union.size < 0.25;
}

function classifyBlanket(fragment, bible, proposedMain) {
  const lowered = fragment.toLowerCase();
  const redHits = RED_KEYWORDS.filter((k) => lowered.includes(k.toLowerCase()));
  const yellowHits = YELLOW_KEYWORDS.filter((k) => lowered.includes(k.toLowerCase()));
  const pivot =
    bible.turn_count >= 2 &&
    (detectPivot(bible.main_thread, firstSentence(fragment)) ||
      detectPivot(bible.main_thread, proposedMain));

  if (redHits.length) {
    return { level: "red", reason: `story-breaking: ${redHits.join(", ")}` };
  }
  if (yellowHits.length || pivot) {
    const parts = [];
    if (yellowHits.length) parts.push(`change keywords: ${yellowHits.join(", ")}`);
    if (pivot) parts.push("main thread pivot");
    return { level: "yellow", reason: parts.join("; ") };
  }
  return { level: "green", reason: "routine fragment" };
}

function stageSage(fragment, bible) {
  const category = detectCategory(fragment);
  const recap = firstSentence(fragment);
  const mainThread = proposeMainThread(fragment, bible, category);
  const questions = [
    "这段口述改变了主线冲突吗？",
    "这是现在发生，还是回忆/伏笔？",
    "读者此刻最需要知道的一个细节是什么？",
  ];
  if (category === "character") questions[0] = "这个角色的动机是什么，为什么现在出现？";
  if (category === "world") questions[0] = "这个设定会如何限制或推动人物选择？";
  if (category === "dialogue") questions[0] = "这句对白是在掩饰、试探，还是坦白？";
  return { category, recap, main_thread: mainThread, key_questions: questions };
}

function stageFocus(fragment, sage) {
  return {
    decisions: extractThreads(fragment).map((thread) => ({
      thread,
      category: detectCategory(thread),
      action: classifyFocusAction(thread, sage.main_thread),
    })),
  };
}

function upsertCharacter(bible, name, note) {
  const found = bible.characters.find((c) => c.name === name);
  if (found) {
    if (note && !found.notes.includes(note)) found.notes.push(note);
    return;
  }
  bible.characters.push({ name, notes: note ? [note] : [] });
}

function upsertPlotThread(bible, label, action, note) {
  const status = action === "expand" ? "active" : action === "park" ? "parked" : "merged";
  const found = bible.plot_threads.find((t) => t.label === label);
  if (found) {
    found.status = status;
    if (note && !found.notes.includes(note)) found.notes.push(note);
    return;
  }
  bible.plot_threads.push({ label, status, notes: note ? [note] : [] });
}

function synthesizeBible(fragment, sage, focus, bible, turnNumber) {
  bible.main_thread = sage.main_thread;
  bible.recent_recap = sage.recap;
  bible.fragment_count += 1;
  bible.turn_count = turnNumber;

  for (const name of extractCharacterHints(fragment)) upsertCharacter(bible, name, sage.recap);
  for (const d of focus.decisions) {
    if (d.action !== "prune") upsertPlotThread(bible, d.thread, d.action, sage.recap);
  }
  if (sage.category === "world") {
    if (!bible.setting.place) bible.setting.place = firstSentence(fragment, 80);
    if (!bible.setting.notes.includes(sage.recap)) {
      bible.setting.notes.push(sage.recap);
      bible.setting.notes = bible.setting.notes.slice(-8);
    }
  }
  for (const q of sage.key_questions) {
    if (!bible.open_questions.includes(q)) bible.open_questions.push(q);
  }
  bible.open_questions = bible.open_questions.slice(-12);
  bible.timeline.push({
    turn: turnNumber,
    recorded_at: new Date().toISOString(),
    kind: "fragment",
    category: sage.category,
    text: sage.recap,
  });
  bible.timeline = bible.timeline.slice(-40);
}

function formatFocusLine(focus) {
  const groups = { expand: [], park: [], merge: [], prune: [] };
  for (const d of focus.decisions) {
    groups[d.action].push(`「${firstSentence(d.thread, 36)}」`);
  }
  const parts = [];
  if (groups.expand.length) parts.push(`展开 ${groups.expand.join(" · ")}`);
  if (groups.park.length) parts.push(`暂存 ${groups.park.join(" · ")}`);
  if (groups.merge.length) parts.push(`合并 ${groups.merge.join(" · ")}`);
  if (groups.prune.length) parts.push(`剪掉 ${groups.prune.join(" · ")}`);
  return parts.join(" · ") || "（暂无分支变化）";
}

function buildAgentReply(sage, focus, bible, blanket, applied) {
  const lines = [`我听懂了：${sage.recap}`, ""];
  if (blanket.level !== "green" && !applied) {
    lines.push(`Blanket：${blanket.level} — ${blanket.reason}`);
    lines.push("（改动未写入 bible，请确认后重试）");
    return lines.join("\n");
  }
  lines.push("Sage 想和你对齐：");
  sage.key_questions.forEach((q, i) => lines.push(`  ${i + 1}. ${q}`));
  lines.push("", `Focus：${formatFocusLine(focus)}`, "", `当前主线：${bible.main_thread}`);
  if (bible.characters.length) {
    lines.push(`人物卡：${bible.characters.map((c) => c.name).slice(0, 6).join("、")}`);
  }
  if (bible.open_questions.length) {
    lines.push(`待回答：${bible.open_questions.length} 条`);
  }
  return lines.join("\n");
}

export function processFragment(session, bible, fragment, autoConfirm = true) {
  const text = fragment
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .join("\n");
  if (!text) throw new Error("口述片段不能为空");

  const sage = stageSage(text, bible);
  const focus = stageFocus(text, sage);
  const blanket = classifyBlanket(text, bible, sage.main_thread);
  const needsConfirm = blanket.level !== "green";
  const applied = !needsConfirm || autoConfirm;

  const turnNumber = session.turn_count + 1;
  const bibleCopy = structuredClone(bible);

  if (applied) synthesizeBible(text, sage, focus, bibleCopy, turnNumber);

  const agentReply = buildAgentReply(sage, focus, bibleCopy, blanket, applied);
  const turn = {
    turn: turnNumber,
    kind: "fragment",
    fragment: text,
    sage,
    focus,
    blanket,
    applied,
    agent_reply: agentReply,
    recorded_at: new Date().toISOString(),
  };

  session.turn_count = turnNumber;
  session.turns.push(turn);

  return { session, bible: bibleCopy, turn, agent_reply: agentReply, applied };
}

export function processAnswer(session, bible, answer) {
  const text = cleanText(answer.replace(/\n+/g, " "));
  if (!text) throw new Error("对齐回答不能为空");
  if (!bible.open_questions.length) throw new Error("当前没有待对齐问题");

  const toResolve = bible.open_questions.slice(-3);
  for (const q of toResolve) {
    bible.resolved_questions.push({
      question: q,
      answer: text,
      resolved_at: new Date().toISOString(),
    });
  }
  bible.resolved_questions = bible.resolved_questions.slice(-30);
  bible.open_questions = bible.open_questions.filter((q) => !toResolve.includes(q));
  bible.recent_recap = firstSentence(text);

  for (const name of extractCharacterHints(text)) upsertCharacter(bible, name, text);

  const turnNumber = session.turn_count + 1;
  bible.timeline.push({
    turn: turnNumber,
    kind: "answer",
    category: "alignment",
    text: firstSentence(text),
    recorded_at: new Date().toISOString(),
  });
  bible.timeline = bible.timeline.slice(-40);
  bible.turn_count = turnNumber;

  const agentReply = [
    `收到对齐：${firstSentence(text)}`,
    "",
    `已消化 ${toResolve.length} 条待对齐问题。`,
    `剩余待回答：${bible.open_questions.length} 条`,
    "",
    `当前主线：${bible.main_thread}`,
  ].join("\n");

  session.turn_count = turnNumber;
  session.turns.push({
    turn: turnNumber,
    kind: "answer",
    answer: text,
    agent_reply: agentReply,
    recorded_at: new Date().toISOString(),
  });

  return { session, bible, agent_reply: agentReply };
}

export function buildOutlineMarkdown(session, bible) {
  const lines = [
    `# ${bible.title} — 故事大纲`,
    "",
    `- 回合：${session.turn_count}`,
    `- 更新：${bible.updated_at}`,
    "",
    "## 主线",
    bible.main_thread,
    "",
  ];
  if (bible.characters.length) {
    lines.push("## 人物", "");
    for (const c of bible.characters) {
      lines.push(`- **${c.name}**：${(c.notes || []).join("；") || "待补充"}`);
    }
    lines.push("");
  }
  const active = bible.plot_threads.filter((t) => t.status === "active");
  if (active.length) {
    lines.push("## 活跃线索", "");
    active.forEach((t) => lines.push(`- ${t.label}`));
    lines.push("");
  }
  if (bible.open_questions.length) {
    lines.push("## 待对齐", "");
    bible.open_questions.forEach((q) => lines.push(`- ${q}`));
  }
  return `${lines.join("\n")}\n`;
}

export function downloadText(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
