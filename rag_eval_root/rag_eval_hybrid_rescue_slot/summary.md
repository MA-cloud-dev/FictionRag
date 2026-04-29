# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-29T14:28:25
- Index: `D:\AgentProject\RAG\FictionRag\data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_hybrid_rescue_slot`
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
| Recall@1 | 4.08% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 73.47% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 91.84% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.3442 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 4.08% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 2.96 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 4 | gold chunk 未出现在 Top 5 的样本数量。 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Examples

### 1. 在赞特港，鲁迪乌斯他们将魔大陆的货币兑换后，得到了哪些米里斯货币？每种各多少枚？

- Gold chunk: `book-000075`
- Retrieved top chunks: `book-000004, book-000005, book-000006, book-000007, book-000077`
- Reference answer: 米里斯银币三枚、米里斯大铜币七枚、米里斯铜币两枚。

### 2. 在小说片段中，主角和基斯对话时，注意到了哪些异常现象？

- Gold chunk: `book-000112`
- Retrieved top chunks: `book-000157, book-000158, book-000159, book-000160, book-000170`
- Reference answer: 看守小姐没来、外面有点吵、有点热、空气里有呛人的烟。

### 3. 艾莉丝的外号是什么？

- Gold chunk: `book-000007`
- Retrieved top chunks: `book-000032, book-000033, book-000034, book-000035, book-000009`
- Reference answer: 狂犬

### 4. 菲兹是如何中毒的？

- Gold chunk: `book-000184`
- Retrieved top chunks: `book-000175, book-000176, book-000177, book-000178, book-000168`
- Reference answer: 他的指尖被刺客射出的小刀割出伤口，毒从伤口侵入。

