# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-29T14:03:21
- Index: `D:\AgentProject\RAG\FictionRag\data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_bm25_weight_8_2_neighbor_2_1_top20`
- Dataset reused: `True`
- Requested sample size: `49`
- Effective sample count: `49`
- Seed: `42`
- Retrieval top_k: `20`
- Embedding model: `qwen3-vl-embedding`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 2.04% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 20.41% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 36.73% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.1914 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 2.04% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 7.89 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 2 | gold chunk 未出现在 Top 20 的样本数量。 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Examples

### 1. 在魔大陆时，是谁发现小偷的痕迹并追上去教训了对方？

- Gold chunk: `book-000079`
- Retrieved top chunks: `book-000001, book-000002, book-000028, book-000029, book-000030`
- Reference answer: 瑞杰路德

### 2. 艾莉丝的外号是什么？

- Gold chunk: `book-000007`
- Retrieved top chunks: `book-000001, book-000002, book-000003, book-000004, book-000005`
- Reference answer: 狂犬

