const form = document.querySelector("#composer");
const questionInput = document.querySelector("#question");
const sendButton = document.querySelector("#send-button");
const conversation = document.querySelector("#conversation");
const referenceList = document.querySelector("#reference-list");
const referencesHeading = document.querySelector("#references-heading");
const topKValue = document.querySelector("#top-k-value");
const indexPathValue = document.querySelector("#index-path-value");
const booksHeading = document.querySelector("#books-heading");
const booksList = document.querySelector("#books-list");
const modal = document.querySelector("#reference-modal");
const modalBook = document.querySelector("#modal-book");
const modalTitle = document.querySelector("#modal-title");
const modalMeta = document.querySelector("#modal-meta");
const modalText = document.querySelector("#modal-text");
const modalClose = document.querySelector("#modal-close");

const TOP_K = 5;
const REFERENCE_PREVIEW_LENGTH = 80;

initializeStaticReferenceCards();
loadBookStats();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();
  if (!question) {
    questionInput.focus();
    return;
  }

  appendMessage("user", question);
  setLoading(true);
  renderReferences([]);

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        top_k: TOP_K,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "请求失败，请检查后端日志。");
    }

    appendMessage("assistant", payload.answer || "原文中没有足够信息确认。");
    renderReferences(payload.contexts || []);
    questionInput.value = "";
  } catch (error) {
    appendMessage("assistant", `联调请求失败：${error.message}`);
  } finally {
    setLoading(false);
  }
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    form.requestSubmit();
  }
});

modalClose.addEventListener("click", closeReferenceModal);
modal.addEventListener("click", (event) => {
  if (event.target === modal) {
    closeReferenceModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !modal.hidden) {
    closeReferenceModal();
  }
});

function initializeStaticReferenceCards() {
  referenceList.querySelectorAll(".reference-card:not(.empty)").forEach((card, index) => {
    const bookName = card.querySelector(".reference-meta span")?.textContent || "原文依据";
    const scoreText = card.querySelector(".reference-meta strong")?.textContent || "";
    const chunkId = card.querySelector(".chunk-id")?.textContent.replace("chunk_id:", "").trim() || "-";
    const text = card.querySelector(".reference-body p:not(.chunk-id)")?.textContent || "";
    const score = Number(scoreText.replace("score", "").trim());
    const context = {
      rank: index + 1,
      book_name: bookName,
      chunk_id: chunkId,
      score,
      text,
    };
    makeReferenceCardInteractive(card, context);
  });
}

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

function renderBooks(stats) {
  indexPathValue.textContent = stats.index_path || "data/index/chunks.jsonl";
  booksHeading.textContent = `${stats.total_books || 0} 本书卷 · ${stats.total_chunks || 0} chunks`;
  booksList.replaceChildren();

  (stats.books || []).forEach((book) => {
    booksList.append(createBookRow(book.book_name, `${book.chunk_count} chunks`));
  });
}

function createBookRow(name, countText) {
  const item = document.createElement("li");
  const nameNode = document.createElement("span");
  const countNode = document.createElement("strong");
  nameNode.textContent = name || "未知书籍";
  countNode.textContent = countText || "0 chunks";
  item.append(nameNode, countNode);
  return item;
}

function appendMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message message-${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  splitParagraphs(text).forEach((paragraphText) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = paragraphText;
    bubble.append(paragraph);
  });

  if (role === "user") {
    const portrait = document.createElement("div");
    portrait.className = "portrait user-portrait";
    portrait.setAttribute("aria-hidden", "true");
    portrait.textContent = "你";

    const time = document.createElement("time");
    time.textContent = `${formatTime()} ✓`;
    article.append(bubble, portrait, time);
  } else {
    const seal = document.createElement("div");
    seal.className = "assistant-seal";
    seal.setAttribute("aria-hidden", "true");
    seal.textContent = "AI";

    const tools = document.createElement("div");
    tools.className = "message-tools";
    tools.setAttribute("aria-hidden", "true");
    tools.innerHTML = `<span>♡ 复制</span><span>↻ 重新生成</span><time>${formatTime()}</time>`;
    bubble.append(tools);
    article.append(seal, bubble);
  }

  conversation.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
}

function renderReferences(contexts) {
  referenceList.replaceChildren();
  referencesHeading.textContent = "召回文本";

  if (!contexts.length) {
    const empty = document.createElement("article");
    empty.className = "reference-card empty";
    empty.textContent = "等待后端返回召回片段。";
    referenceList.append(empty);
    return;
  }

  contexts.forEach((context) => {
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
    bookName.textContent = context.book_name || "未知书籍";

    const score = document.createElement("strong");
    score.textContent = `score ${formatScore(context.score)}`;

    const chunkId = document.createElement("p");
    chunkId.className = "chunk-id";
    chunkId.textContent = `chunk_id: ${context.chunk_id || "-"}`;

    const text = document.createElement("p");
    text.textContent = buildPreview(context.text);

    const detail = document.createElement("span");
    detail.className = "detail-link";
    detail.textContent = "查看详细";

    meta.append(bookName, score);
    body.append(meta, chunkId, text, detail);
    card.append(rank, body);
    makeReferenceCardInteractive(card, context);
    referenceList.append(card);
  });
}

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
  modalTitle.textContent = context.chunk_id || "chunk_id";
  modalMeta.textContent = `rank ${context.rank || "-"} · score ${formatScore(context.score)}`;
  modalText.textContent = context.text || "";
  modal.hidden = false;
  modalClose.focus();
}

function closeReferenceModal() {
  modal.hidden = true;
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
  sendButton.querySelector("span:last-child").textContent = isLoading ? "..." : "➤";
  topKValue.textContent = String(TOP_K);
}

function formatScore(score) {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return "-";
  }
  return score.toFixed(4);
}
