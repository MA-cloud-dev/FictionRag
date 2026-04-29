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

当前阶段固定使用以下参数：

```python
CHUNK_SIZE = 800
CHUNK_MAX_SIZE = 1000
CHUNK_OVERLAP = 3
TOP_K = 5
VECTOR_TOP_N = 20
TOP_SCENE_COUNT = 3
NEIGHBOR_RADIUS = 1
```

切片策略：

- 使用结构感知切分，而不是固定字符窗口。
- 章节标题作为 metadata，不单独生成可召回 chunk。
- 独立一行的 `★★★` 作为场景边界，不单独生成可召回 chunk。
- 基础单位为非空自然段/行，按原文顺序聚合到目标约 800 字。
- 单个自然段超过 1000 字时，按中文/英文句末标点兜底切分。
- 同一场景内相邻 chunk 默认重叠最后 3 个自然段。
- overlap 不跨章节边界，也不跨 `★★★` 场景边界。

召回策略：

- 先计算所有 chunk 与问题向量的 cosine similarity。
- 取向量分数最高的 `VECTOR_TOP_N = 20` 个候选。
- 按 `scene_id` 聚合候选，选出分数最高的 `TOP_SCENE_COUNT = 3` 个场景。
- 对被选中场景里的命中 chunk 做前后 `NEIGHBOR_RADIUS = 1` 扩展。
- 再补充同 scene 内的其他 chunk 作为上下文兜底。
- 最终按原文 `chunk_index` 顺序返回 `TOP_K = 5` 个上下文片段。

## 4. 数据结构

### 4.1 Chunk

```json
{
  "id": "book-000001",
  "book_name": "book",
  "chunk_index": 1,
  "start": 25,
  "end": 271,
  "text": "小说原文片段",
  "chapter_title": "第四卷 少年期冒险者入门篇 第一话「温恩港」",
  "chapter_index": 1,
  "scene_index": 0,
  "scene_id": "chapter-001-scene-000",
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
- `chapter_title`：该 chunk 所属章节标题。章节标题只作为 metadata，不参与正文 embedding。
- `chapter_index`：章节序号，从 1 开始；未识别章节时为 0。
- `scene_index`：章节内场景序号，章节标题后、首个 `★★★` 前为 0。
- `scene_id`：稳定场景标识，例如 `chapter-001-scene-002`。
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
2. 按章节、场景、自然段进行结构感知切片。
3. 为每个 chunk 的正文 `text` 调用 embedding API。
4. 保存 chunk 正文、chapter/scene metadata 和 embedding 到 `data/index/chunks.jsonl`。
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
4. 取向量 top20 候选，并按 scene 聚合。
5. 对高分 scene 中的命中 chunk 做前后相邻扩展。
6. 返回按原文顺序排列的 top_k 上下文片段。
7. 打印 `chunk_id`、`score` 和片段文本。

### 5.3 ask

用途：执行完整问答流程。

示例：

```bash
python -m src.main ask "主角第一次见到某人是什么时候？"
```

执行步骤：

1. 加载本地索引。
2. 将用户问题向量化。
3. 使用 scene-expanded 召回策略取 top_k 原文片段。
4. 拼接 prompt。
5. 调用 LLM。
6. 输出回答和引用片段。

## 6. RAG 流程设计

### 6.1 文本切片

切片伪代码：

```python
def split_text(text: str, target_size: int = 800, max_size: int = 1000, overlap_paragraphs: int = 3):
    chunks = []
    current = []
    chapter = None
    scene_index = 0

    for unit in iter_non_empty_lines(text):
        if is_chapter_title(unit):
            flush_without_overlap(current)
            chapter = unit.text
            scene_index = 0
            continue

        if unit.text == "★★★":
            flush_without_overlap(current)
            scene_index += 1
            continue

        for paragraph in split_long_paragraph_by_sentence(unit, max_size):
            if current and would_exceed_limit(current, paragraph, target_size, max_size):
                flush_with_tail_overlap(current, overlap_paragraphs)
            current.append(paragraph)

    flush_without_overlap(current)

    return chunks
```

约束：

- `target_size` 必须大于 0，且不能大于 `max_size`。
- `overlap_paragraphs` 必须大于等于 0。
- 空文本不生成 chunk。
- 最后一个 chunk 可以少于目标长度。
- 章节标题和 `★★★` 只用于 metadata 与边界，不进入 chunk 正文。
- 向量化只使用 chunk 正文 `text`，不拼接 chapter/scene metadata。

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

底层相似度仍使用 brute-force cosine similarity：

```python
score = dot(question_embedding, chunk_embedding) / (
    norm(question_embedding) * norm(chunk_embedding)
)
```

召回流程：

1. 问题向量化。
2. 遍历所有 chunk。
3. 计算 cosine similarity。
4. 按分数倒序排序，取 `VECTOR_TOP_N = 20` 个候选。
5. 按候选的 `scene_id` 聚合，scene 分数使用该 scene 内最高 chunk 分数。
6. 选出 top 3 个 scene。
7. 对这些 scene 中进入 vector top20 的命中 chunk 做前后 1 个 chunk 扩展。
8. 再补充同 scene 其他 chunk 作为上下文兜底。
9. 最终按原文 `chunk_index` 顺序输出前 `TOP_K = 5` 个结果。

设计取舍：

- 优点：小说问答通常需要连续上下文，scene 扩展能补齐同一场景内的前因后果。
- 风险：上下文可能更集中于少数 scene，降低跨场景问题的覆盖广度。
- 当前策略更适合局部剧情、人物行动原因、单场景细节问答；跨章节/跨场景对比问题后续可增加 hybrid retrieval 或 rerank。

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
- `target_size > max_size` 或 chunk 参数小于合法范围：提示配置不合法。

## 11. 验收测试场景

### 11.1 建索引

- 准备一本小说纯文本文件。
- 运行 `index`。
- 期望生成 `data/index/chunks.jsonl`。
- 期望 chunk 数量大于 0。
- 期望 chunk 记录包含 chapter/scene metadata。
- 期望章节标题和 `★★★` 不单独生成可召回 chunk。
- 期望同 scene 内相邻 chunk 存在 3 个自然段 overlap。
- 期望 overlap 不跨章节和 scene 边界。

### 11.2 查看召回

- 运行 `retrieve` 并输入一个小说中明确出现的问题。
- 期望返回 top_k 片段。
- 期望至少一个片段与问题相关。
- 期望输出包含 `chunk_id` 和 `score`。
- 期望局部剧情问题能召回同 scene 或相邻 chunk 上下文。

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
- 增强章节解析和章节名引用。
- 增加 chunk overlap、chunk size 的可配置能力。
- 增加 hybrid retrieval，避免上下文过度集中于单一场景。
- 增加同 scene 聚合分数策略，例如 top1/top2/top3 加权，而不是只取 scene 内最高分。
- 增加 rerank 模型。
- 增加前端页面。
- 增加 API 服务层。
- 增加问答日志和人工评测。
- 支持多本文档和多格式导入。
