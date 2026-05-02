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
    const text = card.querySelector("p:last-child")?.textContent || "";
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
  booksHeading.textContent = `当前书库 · ${stats.total_books || 0} 本 · ${stats.total_chunks || 0} chunks`;
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

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = role === "user" ? "你" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.append(paragraph);
  article.append(avatar, bubble);
  conversation.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
}

function renderReferences(contexts) {
  referenceList.replaceChildren();
  referencesHeading.textContent = `Top ${TOP_K} 原文依据`;

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
    text.textContent = context.text || "";

    meta.append(bookName, score);
    card.append(meta, chunkId, text);
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

function setLoading(isLoading) {
  sendButton.disabled = isLoading;
  sendButton.classList.toggle("is-loading", isLoading);
  sendButton.querySelector("span:last-child").textContent = isLoading ? "生成中" : "发送";
  topKValue.textContent = String(TOP_K);
}

function formatScore(score) {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return "-";
  }
  return score.toFixed(4);
}
