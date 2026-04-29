# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-29T20:38:08
- Index: `data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_multi_book_mvp_20260429_2033`
- Dataset reused: `False`
- Requested sample size: `50`
- Samples per book: `{'book': 25, '第十卷': 25}`
- Effective sample count: `50`
- Seed: `42`
- Retrieval top_k: `5`
- Embedding model: `qwen3-vl-embedding`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 0.00% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 40.00% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 90.00% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.2557 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 0.00% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 3.67 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 5 | gold chunk 未出现在 Top 5 的样本数量。 |

## Metrics by Book

| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| book | 25 | 0.00% | 44.00% | 96.00% | 0.2727 | 1 |
| 第十卷 | 25 | 0.00% | 36.00% | 84.00% | 0.2387 | 4 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Examples

### 1. 爱丽儿向鲁迪乌斯提出了什么提案？

- Gold chunk: `第十卷-000089`
- Retrieved top chunks: `第十卷-000087, 第十卷-000091, 第十卷-000092, 第十卷-000093, 第十卷-000094`
- Reference answer: 进行一场用石剑的比试（决斗）。

### 2. 保罗在信中说他们现在在哪里？

- Gold chunk: `第十卷-000109`
- Retrieved top chunks: `第十卷-000161, 第十卷-000165, 第十卷-000166, 第十卷-000167, 第十卷-000005`
- Reference answer: 东部港

### 3. 根据片段，希露菲和克里夫被认为是多久一遇的人才？

- Gold chunk: `第十卷-000115`
- Retrieved top chunks: `第十卷-000085, 第十卷-000094, 第十卷-000095, 第十卷-000096, 第十卷-000097`
- Reference answer: 十年一遇

### 4. 主角花了多久时间掌控魔眼？

- Gold chunk: `book-000036`
- Retrieved top chunks: `book-000031, book-000032, book-000033, book-000034, book-000037`
- Reference answer: 一个星期

### 5. 主角决定和谁结婚？

- Gold chunk: `第十卷-000012`
- Retrieved top chunks: `第十卷-000014, 第十卷-000015, 第十卷-000016, 第十卷-000017, 第十卷-000018`
- Reference answer: 希露菲

