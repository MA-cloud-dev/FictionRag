const form = document.querySelector("#composer");
const questionInput = document.querySelector("#question");
const sendButton = document.querySelector("#send-button");
const conversation = document.querySelector("#conversation");
const referenceList = document.querySelector("#reference-list");
const referencesHeading = document.querySelector("#references-heading");
const topKValue = document.querySelector("#top-k-value");
const indexPathValue = document.querySelector("#index-path-value");
const usageStatus = document.querySelector("#usage-status");
const booksHeading = document.querySelector("#books-heading");
const booksList = document.querySelector("#books-list");
const resetButton = document.querySelector("#reset-button");
const exportButton = document.querySelector("#export-button");
const apiKeyInput = document.querySelector("#api-key-input");
const verifyApiKeyButton = document.querySelector("#verify-api-key");
const rememberApiKeyCheckbox = document.querySelector("#remember-api-key");
const apiKeyStatus = document.querySelector("#api-key-status");
const modal = document.querySelector("#reference-modal");
const modalBook = document.querySelector("#modal-book");
const modalTitle = document.querySelector("#modal-title");
const modalMeta = document.querySelector("#modal-meta");
const modalText = document.querySelector("#modal-text");
const modalClose = document.querySelector("#modal-close");

const TOP_K = 5;
const VISITOR_ID_STORAGE_KEY = "fictionrag.visitor_id";
const API_KEY_STORAGE_KEY = "fictionrag.bailian_api_key";
const REFERENCE_PREVIEW_LENGTH = 80;
const INITIAL_ASSISTANT_MESSAGE = `你好，我是你的无职转生 AI 助手，可以基于原文回答关于《无职转生》的各种问题。下面是一些使用说明：

1. 一次只问一个问题，请不要在同一条消息里同时发送多个问题，目前多问题会互相影响。
2. 提问时尽量让人物、时间、地点清晰，尤其人物姓名尽量不要打错。
3. 默认体验次数为每日 5 次；如果需要无限使用，可以申请阿里百炼 API Key，并在左侧填写确认。
4. 刷新页面会丢失当前会话；如需保留内容，可以点击左侧“导出”。
5. 目前系统更适合回答书中明确涉及的局部问题，例如“鲁迪活了多少岁？”“龙神和人神为什么有矛盾？”“一共有几大列强？”。对于“鲁迪一路上的旅程经历了什么？”“龙神经历了什么？”这类范围很宽的综合问题，效果会比较一般。
6. 项目仍在持续优化中，你的每一个问题都是改进系统的重要参考。谢谢！`;
const COPY_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>';
const REGENERATE_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>';

let sessionMessages = [];
let latestReferences = [];
let latestBookStats = null;
let messageIdCounter = 0;
let visitorId = getOrCreateVisitorId();
let verifiedApiKey = "";

initializeApiKeyState();
resetSession({ silent: true });
loadBookStats();
loadVisitorUsage();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();
  if (!question) {
    questionInput.focus();
    return;
  }

  appendMessage("user", question);
  await requestAnswer(question);
  questionInput.value = "";
  questionInput.style.height = "auto";
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

modalClose.addEventListener("click", closeReferenceModal);
modal.addEventListener("click", (event) => {
  if (event.target === modal) {
    closeReferenceModal();
  }
});

resetButton.addEventListener("click", () => {
  resetSession();
  flashAction(resetButton, "已重置");
});

exportButton.addEventListener("click", () => {
  exportSession();
});

verifyApiKeyButton.addEventListener("click", () => {
  verifyApiKey();
});

apiKeyInput.addEventListener("input", () => {
  verifiedApiKey = "";
  apiKeyStatus.textContent = "API Key 修改后需要重新确认。";
  apiKeyStatus.className = "api-key-status";
  if (!rememberApiKeyCheckbox.checked) {
    removeStoredValue(API_KEY_STORAGE_KEY);
  }
  renderUsageStatus();
});

rememberApiKeyCheckbox.addEventListener("change", () => {
  if (rememberApiKeyCheckbox.checked && verifiedApiKey) {
    setStoredValue(API_KEY_STORAGE_KEY, verifiedApiKey);
  }
  if (!rememberApiKeyCheckbox.checked) {
    removeStoredValue(API_KEY_STORAGE_KEY);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !modal.hidden) {
    closeReferenceModal();
  }
});

async function loadBookStats() {
  try {
    const response = await fetch("/api/books");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "书库统计加载失败。");
    }
    renderBooks(payload);
  } catch (error) {
    booksHeading.textContent = "当前书库";
    booksList.replaceChildren(createBookRow("读取失败", error.message));
  }
}

async function loadVisitorUsage() {
  try {
    const response = await fetch("/api/visitor/usage", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ visitor_id: visitorId }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "体验次数加载失败。");
    }
    renderUsageStatus(payload);
  } catch (error) {
    usageStatus.textContent = "读取失败";
  }
}

function renderBooks(stats) {
  latestBookStats = stats;
  indexPathValue.textContent = stats.index_path || "data/index/chunks.jsonl";
  booksHeading.textContent = `${stats.total_books || 0} 本书卷`;
  booksList.replaceChildren();

  (stats.books || []).forEach((book) => {
    booksList.append(createBookRow(book.book_name, `${book.chunk_count} CHUNKS`));
  });
}

function createBookRow(name, countText) {
  const item = document.createElement("li");
  const nameNode = document.createElement("span");
  const countNode = document.createElement("strong");
  nameNode.textContent = name || "未知书籍";
  countNode.textContent = countText || "0 CHUNKS";
  item.append(nameNode, countNode);
  return item;
}

function appendMessage(role, text, options = {}) {
  const message = {
    id: createMessageId(),
    role,
    text: String(text || ""),
    created_at: new Date().toISOString(),
    replay_question: options.replayQuestion || null,
  };
  sessionMessages.push(message);

  const article = document.createElement("article");
  article.className = `message message-${role}`;
  article.dataset.messageId = message.id;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  splitParagraphs(text).forEach((paragraphText) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = paragraphText;
    bubble.append(paragraph);
  });

  if (role === "user") {
    const portrait = document.createElement("div");
    portrait.className = "portrait";
    portrait.textContent = "You";
    article.append(portrait, bubble);
  } else {
    const seal = document.createElement("div");
    seal.className = "assistant-seal";
    seal.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>';

    const tools = document.createElement("div");
    tools.className = "message-tools";
    const copyButton = createMessageTool("复制", "copy", COPY_ICON);
    const regenerateButton = createMessageTool("重新生成", "regenerate", REGENERATE_ICON);
    const time = document.createElement("time");
    time.textContent = formatTime();

    copyButton.addEventListener("click", () => copyMessageText(message.text, copyButton));
    regenerateButton.disabled = !message.replay_question;
    regenerateButton.addEventListener("click", () => regenerateAnswer(message.replay_question, regenerateButton));
    tools.append(copyButton, regenerateButton, time);
    bubble.append(tools);
    article.append(seal, bubble);
  }

  conversation.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
}

function renderReferences(contexts, options = {}) {
  latestReferences = (contexts || []).map((context, index) => ({
    rank: context.rank || index + 1,
    book_name: context.book_name || "未知书卷",
    chunk_id: context.chunk_id || "-",
    score: typeof context.score === "number" ? context.score : null,
    text: context.text || "",
  }));

  referenceList.replaceChildren();
  referencesHeading.textContent = "关联片段";

  if (!latestReferences.length) {
    const empty = document.createElement("article");
    empty.className = "reference-card empty";
    empty.innerHTML = `<p>${options.emptyText || "暂无关联片段。"}</p>`;
    referenceList.append(empty);
    return;
  }

  latestReferences.forEach((context) => {
    const card = document.createElement("article");
    card.className = "reference-card";

    const rank = document.createElement("div");
    rank.className = "reference-rank";
    rank.textContent = String(context.rank || referenceList.children.length + 1);

    const body = document.createElement("div");
    body.className = "reference-body";

    const meta = document.createElement("div");
    meta.className = "reference-meta";

    const bookName = document.createElement("span");
    bookName.textContent = context.book_name || "未知书卷";

    const score = document.createElement("strong");
    score.textContent = `SCORE ${formatScore(context.score)}`;

    const chunkId = document.createElement("p");
    chunkId.className = "chunk-id";
    chunkId.textContent = context.chunk_id || "-";

    const text = document.createElement("p");
    text.textContent = buildPreview(context.text);

    const detail = document.createElement("span");
    detail.className = "detail-link";
    detail.textContent = "查看详情";

    meta.append(bookName, score);
    body.append(meta, chunkId, text, detail);
    card.append(rank, body);
    makeReferenceCardInteractive(card, context);
    referenceList.append(card);
  });
}

// Auto-resize textarea
questionInput.addEventListener("input", () => {
  questionInput.style.height = "auto";
  questionInput.style.height = (questionInput.scrollHeight) + "px";
});

function makeReferenceCardInteractive(card, context) {
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-label", `查看 ${context.chunk_id || "原文片段"} 完整内容`);
  card.addEventListener("click", () => openReferenceModal(context));
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openReferenceModal(context);
    }
  });
}

function openReferenceModal(context) {
  modalBook.textContent = context.book_name || "原文依据";
  modalTitle.textContent = context.chunk_id || "内容详情";
  modalMeta.textContent = `RANK ${context.rank || "-"} · SCORE ${formatScore(context.score)}`;
  modalText.replaceChildren(); // Clear existing
  splitParagraphs(context.text).forEach(pText => {
    const p = document.createElement("p");
    p.textContent = pText;
    modalText.appendChild(p);
  });
  modal.hidden = false;
  modalClose.focus();
}

function closeReferenceModal() {
  modal.hidden = true;
}

async function requestAnswer(question, options = {}) {
  setLoading(true);
  renderReferences([]);

  try {
    const payload = await askQuestion(question);
    appendMessage("assistant", payload.answer || "原文中没有足够信息确认。", {
      replayQuestion: question,
    });
    renderReferences(payload.contexts || []);
    return payload;
  } catch (error) {
    if (error.payload?.usage) {
      renderUsageStatus(error.payload.usage);
    }
    appendMessage("assistant", `请求失败：${error.message}`, {
      replayQuestion: question,
    });
    return null;
  } finally {
    setLoading(false);
    if (options.toolButton) {
      options.toolButton.disabled = false;
    }
  }
}

async function askQuestion(question) {
  const response = await fetch("/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      top_k: TOP_K,
      visitor_id: visitorId,
      api_key: verifiedApiKey || undefined,
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || "请求失败，请检查后端日志。");
    error.payload = payload;
    throw error;
  }
  if (payload.usage) {
    renderUsageStatus(payload.usage);
  }
  return payload;
}

async function verifyApiKey() {
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) {
    apiKeyStatus.textContent = "请先填写阿里百炼 API Key。";
    apiKeyStatus.className = "api-key-status is-error";
    apiKeyInput.focus();
    return;
  }

  verifyApiKeyButton.disabled = true;
  verifyApiKeyButton.textContent = "验证中";
  apiKeyStatus.textContent = "正在测试 LLM、Embedding 和 Rerank 可用性...";
  apiKeyStatus.className = "api-key-status";

  try {
    const response = await fetch("/api/custom-key/test", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ api_key: apiKey }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "API Key 不可用。");
    }
    verifiedApiKey = apiKey;
    if (rememberApiKeyCheckbox.checked) {
      setStoredValue(API_KEY_STORAGE_KEY, apiKey);
    }
    apiKeyStatus.textContent = "自定义 API Key 已启用。";
    apiKeyStatus.className = "api-key-status is-success";
    renderUsageStatus();
  } catch (error) {
    verifiedApiKey = "";
    removeStoredValue(API_KEY_STORAGE_KEY);
    apiKeyStatus.textContent = `验证失败：${error.message}`;
    apiKeyStatus.className = "api-key-status is-error";
    renderUsageStatus();
  } finally {
    verifyApiKeyButton.disabled = false;
    verifyApiKeyButton.textContent = "确认";
  }
}

async function regenerateAnswer(question, button) {
  if (!question || sendButton.disabled) {
    return;
  }

  button.disabled = true;
  flashInlineTool(button, "生成中");
  await requestAnswer(question, { toolButton: button });
}

async function copyMessageText(text, button) {
  try {
    await writeClipboardText(text);
    flashInlineTool(button, "已复制");
  } catch (error) {
    flashInlineTool(button, "复制失败");
  }
}

async function writeClipboardText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  document.body.append(textArea);
  textArea.select();
  const ok = document.execCommand("copy");
  textArea.remove();
  if (!ok) {
    throw new Error("copy command failed");
  }
}

function resetSession(options = {}) {
  sessionMessages = [];
  latestReferences = [];
  messageIdCounter = 0;

  closeReferenceModal();
  setLoading(false);
  conversation.replaceChildren();
  questionInput.value = "";
  questionInput.style.height = "auto";
  appendMessage("assistant", INITIAL_ASSISTANT_MESSAGE);
  renderReferences([], { emptyText: "召回片段将在此处显示" });

  if (!options.silent) {
    questionInput.focus();
  }
}

function initializeApiKeyState() {
  const storedKey = getStoredValue(API_KEY_STORAGE_KEY);
  if (!storedKey) {
    return;
  }
  apiKeyInput.value = storedKey;
  rememberApiKeyCheckbox.checked = true;
  verifiedApiKey = storedKey;
  apiKeyStatus.textContent = "已使用本地保存的自定义 API Key。";
  apiKeyStatus.className = "api-key-status is-success";
}

function renderUsageStatus(usage = null) {
  if (verifiedApiKey) {
    usageStatus.textContent = "自定义 Key";
    return;
  }
  if (!usage) {
    return;
  }
  usageStatus.textContent = `${usage.remaining}/${usage.quota}`;
}

function getOrCreateVisitorId() {
  const existing = getStoredValue(VISITOR_ID_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const created = createVisitorId();
  setStoredValue(VISITOR_ID_STORAGE_KEY, created);
  return created;
}

function createVisitorId() {
  const cryptoApi = window.crypto;
  if (cryptoApi?.randomUUID) {
    return cryptoApi.randomUUID();
  }
  const random = new Uint8Array(16);
  if (cryptoApi?.getRandomValues) {
    cryptoApi.getRandomValues(random);
    return Array.from(random, (value) => value.toString(16).padStart(2, "0")).join("");
  }
  return `visitor-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function getStoredValue(key) {
  try {
    return window.localStorage.getItem(key) || "";
  } catch (error) {
    return "";
  }
}

function setStoredValue(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch (error) {
    // Local storage can be unavailable in private browsing modes.
  }
}

function removeStoredValue(key) {
  try {
    window.localStorage.removeItem(key);
  } catch (error) {
    // Local storage can be unavailable in private browsing modes.
  }
}

function exportSession() {
  const payload = {
    exported_at: new Date().toISOString(),
    app: "FictionRAG",
    top_k: TOP_K,
    knowledge_base: latestBookStats
      ? {
          index_path: latestBookStats.index_path || "data/index/chunks.jsonl",
          total_books: latestBookStats.total_books || 0,
          total_chunks: latestBookStats.total_chunks || 0,
          books: latestBookStats.books || [],
        }
      : null,
    messages: sessionMessages,
    references: latestReferences,
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `fictionrag-session-${formatFileTimestamp(new Date())}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  flashAction(exportButton, "已导出");
}

function splitParagraphs(text) {
  return String(text || "")
    .split(/\n+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function formatTime() {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

function formatFileTimestamp(date) {
  const parts = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
    String(date.getHours()).padStart(2, "0"),
    String(date.getMinutes()).padStart(2, "0"),
    String(date.getSeconds()).padStart(2, "0"),
  ];
  return `${parts[0]}${parts[1]}${parts[2]}-${parts[3]}${parts[4]}${parts[5]}`;
}

function flashAction(button, label) {
  const textNode = button.querySelector("span");
  if (!textNode) {
    return;
  }

  const originalText = textNode.textContent;
  button.classList.add("is-confirmed");
  textNode.textContent = label;
  window.setTimeout(() => {
    textNode.textContent = originalText;
    button.classList.remove("is-confirmed");
  }, 1200);
}

function flashInlineTool(button, label) {
  const labelNode = button.querySelector(".tool-label");
  if (!labelNode) {
    return;
  }

  const originalText = button.dataset.label || labelNode.textContent;
  button.dataset.label = originalText;
  button.classList.add("is-confirmed");
  labelNode.textContent = label;
  window.setTimeout(() => {
    labelNode.textContent = originalText;
    button.classList.remove("is-confirmed");
  }, 1200);
}

function createMessageTool(label, action, icon) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "message-tool";
  button.dataset.action = action;
  button.dataset.label = label;
  button.innerHTML = `${icon}<span class="tool-label">${label}</span>`;
  return button;
}

function createMessageId() {
  messageIdCounter += 1;
  return `message-${messageIdCounter}`;
}

function buildPreview(text) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  if (normalized.length <= REFERENCE_PREVIEW_LENGTH) {
    return normalized;
  }
  return `${normalized.slice(0, REFERENCE_PREVIEW_LENGTH)}...`;
}

function setLoading(isLoading) {
  sendButton.disabled = isLoading;
  sendButton.classList.toggle("is-loading", isLoading);
  
  if (isLoading) {
    sendButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="spinner"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>';
  } else {
    sendButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>';
  }
  
  topKValue.textContent = String(TOP_K);
}

function formatScore(score) {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return "-";
  }
  return score.toFixed(4);
}
