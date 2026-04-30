# AI 小说问答助手技术实现方案

## 1. 技术定位

本项目 MVP 阶段采用 Python 控制台程序实现，不接前端，不引入复杂服务架构。目标是尽快跑通 RAG 问答主链路：

小说文本/EPUB -> 文本清洗 -> 文本切片 -> 向量化 -> 本地索引 -> 多书召回 -> rerank -> LLM 回答

MVP 优先追求简单、可调试、能验证效果。后续如果需求扩大，再逐步升级为 Web API、向量数据库和前端应用。

## 2. 推荐目录结构

```text
FictionRag/
  data/
    novels/
      第一卷.txt
      第二卷.txt
      ...
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
    epub_importer.py
    index_store.py
    retriever.py
    reranker.py
    llm.py
    prompts.py
```

说明：

- `data/novels/*.txt`：清洗后的小说纯文本，每本书使用卷名作为文件名和 `book_name`。
- `data/index/chunks.jsonl`：本地索引文件，保存 chunk、元数据和 embedding。
- `src/main.py`：控制台入口。
- `src/chunker.py`：负责文本切片。
- `src/embeddings.py`：负责调用 embedding API。
- `src/index_store.py`：负责索引读写。
- `src/epub_importer.py`：负责将 EPUB 清洗为纯文本。
- `src/retriever.py`：负责 dense/BM25 两路召回、多书路由、scene-expanded 后处理和第 5 位 rescue slot。
- `src/reranker.py`：负责调用 qwen3-rerank 对候选 chunk 重新打分。
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
BM25_TOP_N = 20
BOOK_ROUTE_COUNT = 5
BOOK_RESULT_CAP = 3
TOP_SCENE_COUNT = 3
NEIGHBOR_BEFORE = 2
NEIGHBOR_AFTER = 1
VECTOR_SCORE_WEIGHT = 0.8
BM25_SCORE_WEIGHT = 0.2
RESCUE_SLOT_RANK = 5
RERANK_CANDIDATE_TOP_N = 30
RERANK_VECTOR_TOP_N = 100
RERANK_BM25_TOP_N = 100
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

- 先计算所有 chunk 与问题向量的 cosine similarity，得到 dense top20。
- 同时用原始问题文本执行 BM25 sparse 召回，得到 BM25 top20。
- 对 dense 和 BM25 分数分别按本路最大分归一化，按 0.8:0.2 融合。
- 多书索引中先按候选分数选择相关书，默认 `BOOK_ROUTE_COUNT = 5`。
- 在每本候选书内部按 `(book_name, scene_id)` 聚合候选，选出分数最高的 `TOP_SCENE_COUNT = 3` 个场景。
- 对被选中场景里的命中 chunk 做前 2 后 1 扩展。
- 再补充同 scene 内的其他 chunk 作为上下文兜底。
- 最终按相关性合并，默认单本书最多占 `BOOK_RESULT_CAP = 3` 个位置。
- 对 `top_k >= 5` 的 hybrid 召回，启用 rescue slot：锁定当前 Top4，只允许第 5 位被强 BM25/稀有词证据候选替换。

rerank 评测策略：

- rerank 只在 eval 中通过 `--rerank` 启用，不默认影响 `retrieve/ask`。
- 构建候选池时使用更宽的 `RERANK_VECTOR_TOP_N = 100` 和 `RERANK_BM25_TOP_N = 100`。
- 候选池最终保留 `RERANK_CANDIDATE_TOP_N = 30` 个 chunk。
- 使用 qwen3-rerank 对 `query + chunk_text` 批量打分。
- 按 rerank score 排序后输出最终 Top5，并继续执行 `BOOK_RESULT_CAP = 3`。

## 4. 数据结构

### 4.1 Chunk

```json
{
  "id": "book-000001",
  "book_name": "第四卷",
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
- `book_name`：小说名称，当前使用卷名，例如 `第一卷`、`第四卷`、`第十卷`。
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
  "text": "召回到的小说原文片段",
  "book_name": "第四卷",
  "base_score": 0.71,
  "rerank_score": 0.82
}
```

字段说明：

- `chunk_id`：召回片段 ID。
- `score`：最终用于排序的分数；rerank 模式下为 rerank score。
- `text`：召回片段原文。
- `book_name`：召回片段所属书籍。
- `base_score`：rerank 前的 hybrid/scene 候选分数。
- `rerank_score`：qwen3-rerank 返回的相关性分数。

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

MVP 阶段提供四个主要命令：`index`、`import-epub`、`retrieve`、`ask`，并提供 `eval` 用于离线评测。

### 5.1 index

用途：读取小说文本，切片，生成向量，保存本地索引。

示例：

```bash
python -m src.main index ^
  --book data/novels/第一卷.txt --book-name 第一卷 ^
  --book data/novels/第二卷.txt --book-name 第二卷 ^
  --index-path data/index/chunks.jsonl
```

执行步骤：

1. 读取一个或多个 `.txt` 小说文件。
2. 按章节、场景、自然段进行结构感知切片。
3. 为每个 chunk 的正文 `text` 调用 embedding API。
4. 保存 chunk 正文、chapter/scene metadata 和 embedding 到 `data/index/chunks.jsonl`。
5. 输出每本书的 chunk 数、chunk 总数和索引保存位置。

重复运行 `index` 时，默认覆盖旧的 `chunks.jsonl`，避免重复写入脏数据。

### 5.2 import-epub

用途：将 EPUB 清洗为纯文本，供 `index` 使用。

示例：

```bash
python -m src.main import-epub --epub input.epub --output data/novels/第五卷.txt
```

执行步骤：

1. 按 OPF spine 顺序读取 EPUB 正文。
2. 过滤封面、插图、简介、版权、制作信息等非正文页面。
3. 归一化正文段落和场景分隔符。
4. 输出 UTF-8 纯文本。

### 5.3 retrieve

用途：只查看召回结果，不调用 LLM。

示例：

```bash
python -m src.main retrieve "主角第一次见到某人是什么时候？"
```

执行步骤：

1. 加载本地索引。
2. 将用户问题向量化。
3. 计算问题向量与所有 chunk 向量的 cosine similarity。
4. 使用原始问题文本执行 BM25 sparse 召回。
5. 将 dense top20 与 BM25 top20 归一化融合。
6. 按书籍路由选择候选书，并在书内按 scene 聚合，对高分 scene 中的命中 chunk 做前 2 后 1 相邻扩展。
7. 在强证据存在时，用 rescue slot 替换第 5 位。
8. 返回按原文顺序排列的 top_k 上下文片段。
9. 打印 `chunk_id`、`score` 和片段文本。

### 5.4 ask

用途：执行完整问答流程。

示例：

```bash
python -m src.main ask "主角第一次见到某人是什么时候？"
```

执行步骤：

1. 加载本地索引。
2. 将用户问题向量化。
3. 使用 hybrid dense+BM25、多书路由、scene-expanded 和 rescue slot 策略取 top_k 原文片段。
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

读取索引时，将所有 chunk 加载到内存中。当前十本书规模约 1800+ chunks，本地 JSONL 仍可满足 MVP 评测和调试需求。

### 6.4 召回算法

底层相似度仍使用 brute-force cosine similarity：

```python
score = dot(question_embedding, chunk_embedding) / (
    norm(question_embedding) * norm(chunk_embedding)
)
```

召回流程：

1. 问题向量化。
2. 遍历所有 chunk，计算 cosine similarity，默认在线召回取 dense top20，rerank eval 取 dense top100。
3. 对问题文本和 chunk 正文执行 BM25，默认在线召回取 BM25 top20，rerank eval 取 BM25 top100。
4. 对 dense 分数和 BM25 分数分别按本路最大分归一化。
5. 同一 chunk 的最终融合分数为 `0.8 * normalized_dense + 0.2 * normalized_bm25`。
6. 根据融合候选选择相关书籍，默认 `book_route_count=5`。
7. 在每本候选书内部按 `(book_name, scene_id)` 聚合，scene 分数使用该 scene 内最高 chunk 分数。
8. 每本书选出 top 3 个 scene。
9. 对这些 scene 中的命中 chunk 做前 2 后 1 扩展。
10. 再补充同 scene 其他 chunk 作为上下文兜底。
11. 得到 baseline Top5 后，锁定前 4 位。
12. 第 5 位 rescue slot 从 dense、BM25 及其前 2 后 1 邻居中选择强证据候选。
13. 如果没有候选满足强 BM25 分数、稀有词覆盖率和分数 margin 要求，保留 baseline 第 5 位。

设计取舍：

- 优点：dense 保留语义泛化，BM25 补充精确关键词，scene 扩展补齐局部剧情上下文。
- 风险：scene 扩展会挤压 Top5 空间，因此 rescue slot 只替换第 5 位，避免破坏已命中的高置信 Top4。
- 当前策略更适合局部剧情、人物行动原因、单场景细节问答；跨章节/跨场景对比问题后续可增加章节级摘要。

### 6.5 Rerank 评测链路

rerank 只在离线评测中启用：

```text
wide dense/BM25 recall
-> book route
-> book-aware scene expansion
-> candidate top30
-> qwen3-rerank
-> book capped final top5
```

当前默认参数：

```text
book_route_count = 5
book_result_cap = 3
rerank_candidate_top_n = 30
rerank_vector_top_n = 100
rerank_bm25_top_n = 100
```

评测会额外输出：

- `Candidate Hit@30`：gold chunk 是否进入 rerank 前候选池。
- `Candidate Miss@30`：gold chunk 未进入候选池的数量。
- `Rerank Lost Count`：gold 进入候选池但最终未进入 Top5 的数量。
- `rerank_scores.jsonl`：rerank 分数缓存，避免重复评测时再次调用 API。

### 6.6 BM25 分词与 rescue slot

BM25 不引入第三方依赖，直接在 `src/retriever.py` 中实现。

- 中文文本按连续 CJK 字符生成 2-4 gram。
- 英文和数字按连续 token 保留并转小写。
- BM25 参数固定为 `k1=1.5`、`b=0.75`。
- BM25 只索引 `chunk.text`，不拼接 chapter/scene metadata。

rescue slot 的目标不是全局重排，而是低风险补救：

- 只在 `query_text` 非空且 `top_k >= 5` 时启用。
- baseline Top4 完全保留。
- 第 5 位候选来自 dense top20、BM25 top20 及其邻居。
- 候选必须同时满足 BM25 归一化分数、稀有词覆盖率和相对 baseline 第 5 位的分数 margin。

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
RERANKER_BASE_URL=https://dashscope.aliyuncs.com/compatible-api/v1
RERANKER_MODEL=qwen3-rerank
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

- 准备一本或多本小说纯文本文件。
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
- 期望精确关键词问题能通过 BM25 进入候选池。
- 期望 rescue slot 不改变 baseline Top4。
- 期望多书场景中相同 `scene_id` 或 `chunk_index` 不跨书扩展。

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

### 11.6 Rerank 评测

- 复用现有十本书 dataset 和 question embedding cache。
- 运行 `eval --rerank`。
- 期望输出 `dataset.jsonl`、`results.jsonl`、`summary.md`、`rerank_scores.jsonl`。
- 期望 `summary.md` 包含 Recall@1/3/5、MRR、Candidate Hit@30、Candidate Miss@30、Rerank Lost Count 和失败案例分析。

### 11.7 当前评测基线

当前保留以下评测目录：

- `rag_eval_ten_book_mvp_20260429_2326`：十本书无 rerank 基线，Recall@5 75.13%，Missed Count 49。
- `rag_eval_ten_book_book_route3_20260430_1125`：十本书 book route 基线，Recall@5 78.68%，Missed Count 42。
- `rag_eval_ten_book_qwen3_rerank_20260430_1530`：qwen3-rerank 初版，Recall@5 85.79%，Missed Count 28，Candidate Hit@30 86.29%。
- `rag_eval_ten_book_qwen3_rerank_route5_v100_b100_top30_20260430_1645`：当前最佳十本书 rerank 结果，Recall@5 89.34%，MRR 0.8276，Missed Count 21，Candidate Hit@30 91.37%。

## 12. 后续技术优化

MVP 后可以逐步增加：

- 使用向量数据库，例如 FAISS、Chroma、Milvus。
- 增强章节解析和章节名引用。
- 增加 chunk overlap、chunk size 的可配置能力。
- 继续优化 hybrid retrieval，避免上下文过度集中于单一场景。
- 增加同 scene 聚合分数策略，例如 top1/top2/top3 加权，而不是只取 scene 内最高分。
- 继续降低 Candidate Miss@30，优先优化候选池召回。
- 评估 `rerank_candidate_top_n=50` 的高召回模式。
- 增加前端页面。
- 增加 API 服务层。
- 增加问答日志和人工评测。
- 支持多本文档和多格式导入。
