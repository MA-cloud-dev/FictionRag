# AI 小说问答助手技术实现方案

## 1. 技术定位

本项目 MVP 阶段采用 Python 控制台程序实现，不接前端，不引入复杂服务架构。目标是尽快跑通 RAG 问答主链路：

小说文本 -> 文本切片 -> 向量化 -> 本地索引 -> 问题召回 -> LLM 回答

MVP 优先追求简单、可调试、能验证效果。后续如果需求扩大，再逐步升级为 Web API、向量数据库和前端应用。

## 2. 推荐目录结构

```text
FictionRag/
  data/
    novels/
      book.txt
    index/
      chunks.jsonl
  doc/
    requirement.md
    spec.md
  src/
    main.py
    config.py
    chunker.py
    embeddings.py
    index_store.py
    retriever.py
    llm.py
    prompts.py
```

说明：

- `data/novels/book.txt`：MVP 阶段唯一一本小说原文。
- `data/index/chunks.jsonl`：本地索引文件，保存 chunk、元数据和 embedding。
- `src/main.py`：控制台入口。
- `src/chunker.py`：负责文本切片。
- `src/embeddings.py`：负责调用 embedding API。
- `src/index_store.py`：负责索引读写。
- `src/retriever.py`：负责相似度召回。
- `src/llm.py`：负责调用 LLM API。
- `src/prompts.py`：维护问答 prompt。

## 3. 核心参数

MVP 阶段固定使用以下参数：

```python
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5
```

切片策略：

- 每个 chunk 约 1000 字。
- 相邻 chunk 保留 200 字重叠内容。
- 步长为 `CHUNK_SIZE - CHUNK_OVERLAP`，即 800 字。
- 暂不做章节识别、语义切分或标点边界优化。

## 4. 数据结构

### 4.1 Chunk

```json
{
  "id": "book-000001",
  "book_name": "book",
  "chunk_index": 1,
  "start": 0,
  "end": 1000,
  "text": "小说原文片段",
  "embedding": [0.01, 0.02, 0.03]
}
```

字段说明：

- `id`：chunk 唯一标识。
- `book_name`：小说名称，MVP 可直接使用文件名。
- `chunk_index`：chunk 序号。
- `start`：该 chunk 在原文中的开始位置。
- `end`：该 chunk 在原文中的结束位置。
- `text`：chunk 原文。
- `embedding`：向量模型返回的向量。

### 4.2 RetrievalResult

```json
{
  "chunk_id": "book-000001",
  "score": 0.82,
  "text": "召回到的小说原文片段"
}
```

字段说明：

- `chunk_id`：召回片段 ID。
- `score`：问题向量和 chunk 向量的相似度分数。
- `text`：召回片段原文。

### 4.3 Answer

```json
{
  "question": "用户问题",
  "answer": "基于原文生成的回答",
  "references": [
    {
      "chunk_id": "book-000001",
      "score": 0.82,
      "text": "引用片段"
    }
  ]
}
```

## 5. 控制台命令设计

MVP 阶段提供三个命令：`index`、`retrieve`、`ask`。

### 5.1 index

用途：读取小说文本，切片，生成向量，保存本地索引。

示例：

```bash
python -m src.main index --book data/novels/book.txt
```

执行步骤：

1. 读取 `book.txt`。
2. 按 `chunk_size = 1000`、`overlap = 200` 切片。
3. 为每个 chunk 调用 embedding API。
4. 保存到 `data/index/chunks.jsonl`。
5. 输出 chunk 总数和索引保存位置。

重复运行 `index` 时，默认覆盖旧的 `chunks.jsonl`，避免重复写入脏数据。

### 5.2 retrieve

用途：只查看召回结果，不调用 LLM。

示例：

```bash
python -m src.main retrieve "主角第一次见到某人是什么时候？"
```

执行步骤：

1. 加载本地索引。
2. 将用户问题向量化。
3. 计算问题向量与所有 chunk 向量的 cosine similarity。
4. 返回 top_k 结果。
5. 打印 `chunk_id`、`score` 和片段文本。

### 5.3 ask

用途：执行完整问答流程。

示例：

```bash
python -m src.main ask "主角第一次见到某人是什么时候？"
```

执行步骤：

1. 加载本地索引。
2. 将用户问题向量化。
3. 召回 top_k 原文片段。
4. 拼接 prompt。
5. 调用 LLM。
6. 输出回答和引用片段。

## 6. RAG 流程设计

### 6.1 文本切片

切片伪代码：

```python
def split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    chunks = []
    step = chunk_size - overlap
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += step

    return chunks
```

约束：

- `overlap` 必须小于 `chunk_size`。
- 空文本不生成 chunk。
- 最后一个 chunk 可以少于 1000 字。

### 6.2 向量化

向量化统一通过外部 embedding API 完成。

MVP 阶段只需要封装两个能力：

- `embed_text(text: str) -> list[float]`
- `embed_texts(texts: list[str]) -> list[list[float]]`

批量 embedding 可作为优化项。第一版可以逐条调用，优先保证流程清晰可用。

### 6.3 本地索引

索引文件使用 JSONL，每行一个 chunk。

优点：

- 实现简单。
- 易于人工查看。
- 方便后续迁移到向量数据库。

读取索引时，将所有 chunk 加载到内存中。MVP 只支持一本小说，数据量可控，不需要额外数据库。

### 6.4 召回算法

MVP 使用 brute-force cosine similarity：

```python
score = dot(question_embedding, chunk_embedding) / (
    norm(question_embedding) * norm(chunk_embedding)
)
```

召回流程：

1. 问题向量化。
2. 遍历所有 chunk。
3. 计算 cosine similarity。
4. 按分数倒序排序。
5. 取前 `TOP_K = 5` 个结果。

## 7. Prompt 设计

问答 prompt 必须明确约束 LLM 只能基于给定原文回答。

推荐模板：

```text
你是一个小说问答助手。你只能根据下面提供的小说原文片段回答问题。

要求：
1. 只能使用“小说原文片段”中的信息。
2. 不要使用常识、猜测或其他作品的信息补充答案。
3. 如果原文片段中没有足够信息回答，请明确回答：“原文中没有足够信息确认。”
4. 回答应简洁，并尽量指出依据来自哪些片段编号。

小说原文片段：
{context}

用户问题：
{question}

请给出回答：
```

上下文拼接格式：

```text
[片段 1 | chunk_id=book-000001 | score=0.82]
原文内容...

[片段 2 | chunk_id=book-000002 | score=0.78]
原文内容...
```

## 8. 输出格式

### 8.1 retrieve 输出

```text
Top 5 retrieval results:

[1] chunk_id=book-000001 score=0.82
原文片段...

[2] chunk_id=book-000002 score=0.78
原文片段...
```

### 8.2 ask 输出

```text
Question:
用户问题

Answer:
基于小说原文的回答

References:
[1] chunk_id=book-000001 score=0.82
原文片段...
```

## 9. 配置项

MVP 阶段推荐通过环境变量配置 API：

```text
EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_MODEL=your_embedding_model
LLM_API_KEY=your_llm_api_key
LLM_MODEL=your_llm_model
```

实现时可以在 `src/config.py` 中读取这些环境变量。

## 10. 错误处理

MVP 阶段只需要处理关键错误：

- 小说文件不存在：提示用户检查路径。
- 小说文件为空：提示无法生成索引。
- embedding API 调用失败：输出错误信息并停止索引或召回。
- 本地索引不存在：提示先运行 `index`。
- 本地索引为空：提示重新生成索引。
- LLM API 调用失败：输出错误信息，并保留召回片段供排查。
- `overlap >= chunk_size`：提示配置不合法。

## 11. 验收测试场景

### 11.1 建索引

- 准备一本小说纯文本文件。
- 运行 `index`。
- 期望生成 `data/index/chunks.jsonl`。
- 期望 chunk 数量大于 0。
- 期望相邻 chunk 存在 200 字重叠内容。

### 11.2 查看召回

- 运行 `retrieve` 并输入一个小说中明确出现的问题。
- 期望返回 top_k 片段。
- 期望至少一个片段与问题相关。
- 期望输出包含 `chunk_id` 和 `score`。

### 11.3 完整问答

- 运行 `ask` 并输入一个小说中明确有答案的问题。
- 期望返回基于原文的答案。
- 期望输出引用片段。
- 期望答案不包含召回片段以外的事实。

### 11.4 无依据问题

- 运行 `ask` 并输入一个小说中没有依据的问题。
- 期望回答“原文中没有足够信息确认”或等价表达。
- 期望系统不编造情节。

### 11.5 重复建索引

- 连续运行两次 `index`。
- 期望第二次运行覆盖旧索引。
- 期望索引文件中不会出现重复数据累积。

## 12. 后续技术优化

MVP 后可以逐步增加：

- 使用向量数据库，例如 FAISS、Chroma、Milvus。
- 增加章节解析和章节名引用。
- 增加 chunk overlap、chunk size 的可配置能力。
- 增加 rerank 模型。
- 增加前端页面。
- 增加 API 服务层。
- 增加问答日志和人工评测。
- 支持多本文档和多格式导入。
