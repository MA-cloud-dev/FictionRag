# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-28T21:55:52
- Index: `D:\AgentProject\RAG\FictionRag\data\index\chunks.jsonl`
- Output dir: `rag_eval_chunk_optimized`
- Dataset reused: `True`
- Requested sample size: `49`
- Effective sample count: `49`
- Seed: `42`
- Retrieval top_k: `5`
- Embedding model: `qwen3-vl-embedding`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 42.86% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 67.35% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 67.35% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.5442 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 42.86% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 1.42 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 16 | gold chunk 未出现在 Top 5 的样本数量。 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Examples

### 1. 在魔大陆时，是谁发现小偷的痕迹并追上去教训了对方？

- Gold chunk: `book-000079`
- Retrieved top chunks: `book-000001, book-000030, book-000045, book-000051, book-000052`
- Reference answer: 瑞杰路德

### 2. 鲁迪乌斯在船舱中借口去做什么？

- Gold chunk: `book-000073`
- Retrieved top chunks: `book-000074, book-000098, book-000048, book-000101, book-000068`
- Reference answer: 去厕所

### 3. 为什么斯佩路德族的搭船费用特别贵？

- Gold chunk: `book-000009`
- Retrieved top chunks: `book-000011, book-000013, book-000122, book-000014, book-000004`
- Reference answer: 官员推测是防恐对策，为了防止有人把斯佩路德族当成奴隶送到米里斯大陆作乱闹事。

### 4. 魔界大帝奇希莉卡·奇希里斯最让人畏惧的能力是什么？

- Gold chunk: `book-000031`
- Retrieved top chunks: `book-000032, book-000023, book-000024, book-000028, book-000022`
- Reference answer: 她可以把他人的眼睛变成魔眼。

### 5. 在赞特港，鲁迪乌斯他们将魔大陆的货币兑换后，得到了哪些米里斯货币？每种各多少枚？

- Gold chunk: `book-000075`
- Retrieved top chunks: `book-000006, book-000077, book-000013, book-000076, book-000014`
- Reference answer: 米里斯银币三枚、米里斯大铜币七枚、米里斯铜币两枚。

