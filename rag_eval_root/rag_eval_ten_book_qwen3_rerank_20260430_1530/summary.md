# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-30T15:49:18
- Index: `data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_ten_book_qwen3_rerank_20260430_1530`
- Dataset reused: `True`
- Requested sample size: `200`
- Samples per book: `{'第一卷': 25, '第二卷': 25, '第三卷': 25, '第四卷': 25, '第五卷': 25, '第六卷': 25, '第七卷': 25, '第八卷': 25, '第九卷': 25, '第十卷': 25}`
- Effective sample count: `197`
- Seed: `42`
- Retrieval top_k: `5`
- Book route count: `3`
- Book result cap: `3`
- Rerank enabled: `True`
- Reranker model: `qwen3-rerank`
- Rerank candidate top_n: `30`
- Rerank vector top_n: `50`
- Rerank BM25 top_n: `50`
- Rerank cache hits: `5910`
- Rerank API scored: `0`
- Rerank API calls: `0`
- Embedding model: `text-embedding-v4`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 75.63% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 84.77% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 85.79% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.8026 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 75.63% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 1.16 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 28 | gold chunk 未出现在 Top 5 的样本数量。 |
| Candidate Hit@30 | 86.29% | gold chunk 出现在 rerank 前 Top 30 候选池的比例。 |
| Candidate Miss@30 | 27 | gold chunk 未进入 rerank 前 Top 30 候选池的数量。 |
| Rerank Lost Count | 1 | gold chunk 进入候选池但最终没进 Top 5 的数量。 |

## Baseline Comparison

| Metric | Baseline route=3 cap=3 | Current | Delta |
| --- | ---: | ---: | ---: |
| Recall@1 | 65.99% | 75.63% | +9.64% |
| Recall@3 | 75.13% | 84.77% | +9.64% |
| Recall@5 | 78.68% | 85.79% | +7.11% |
| MRR | 0.7084 | 0.8026 | +0.0942 |
| Missed Count | 42 | 28 | -14 |

## Metrics by Book

| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed | Candidate Hit@30 | Rerank Lost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 第一卷 | 20 | 95.00% | 95.00% | 95.00% | 0.9500 | 1 | 95.00% | 0 |
| 第七卷 | 20 | 85.00% | 100.00% | 100.00% | 0.9250 | 0 | 100.00% | 0 |
| 第三卷 | 19 | 68.42% | 73.68% | 73.68% | 0.7105 | 5 | 73.68% | 0 |
| 第九卷 | 20 | 85.00% | 95.00% | 95.00% | 0.9000 | 1 | 95.00% | 0 |
| 第二卷 | 20 | 75.00% | 80.00% | 80.00% | 0.7750 | 4 | 80.00% | 0 |
| 第五卷 | 19 | 63.16% | 78.95% | 84.21% | 0.7237 | 3 | 84.21% | 0 |
| 第八卷 | 20 | 70.00% | 75.00% | 75.00% | 0.7250 | 5 | 80.00% | 1 |
| 第六卷 | 20 | 70.00% | 75.00% | 75.00% | 0.7167 | 5 | 75.00% | 0 |
| 第十卷 | 20 | 70.00% | 80.00% | 85.00% | 0.7517 | 3 | 85.00% | 0 |
| 第四卷 | 19 | 73.68% | 94.74% | 94.74% | 0.8421 | 1 | 94.74% | 0 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Example Analysis

### 1. 保罗在信中称他们现在在哪里？

- Reason label: `candidate_miss`
- Gold chunk: `第十卷-000109`
- Gold book: `第十卷`
- Candidate rank: `None`
- Retrieved top chunks: `第八卷-000123, 第五卷-000067, 第五卷-000104, 第五卷-000069, 第八卷-000029`
- Top scores: `0.7084, 0.6785, 0.6300, 0.5749, 0.5277`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 东部港

### 2. 根据该片段，莉妮亚和普露塞娜的战斗方式是什么？

- Reason label: `rerank_lost`
- Gold chunk: `第八卷-000142`
- Gold book: `第八卷`
- Candidate rank: `6`
- Retrieved top chunks: `第七卷-000171, 第八卷-000146, 第八卷-000143, 第七卷-000172, 第七卷-000169`
- Top scores: `0.9668, 0.9612, 0.9199, 0.9191, 0.9039`
- Gold base score: `0.8079`
- Gold rerank score: `0.8592`
- Reference answer: 其中之一会以高速移动并同时利用魔术等方式来扰乱敌人，另一个则趁这个时候使出声音魔术让敌人无法使出力量。

### 3. 诺伦·格雷拉特的父母是谁？

- Reason label: `candidate_miss`
- Gold chunk: `第五卷-000044`
- Gold book: `第五卷`
- Candidate rank: `None`
- Retrieved top chunks: `第七卷-000034, 第一卷-000035, 第五卷-000134, 第五卷-000098, 第五卷-000080`
- Top scores: `0.8900, 0.8781, 0.8226, 0.7993, 0.6835`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 保罗和塞妮丝。

### 4. 鲁迪乌斯计划在多久后离开当前的城市？

- Reason label: `candidate_miss`
- Gold chunk: `第五卷-000084`
- Gold book: `第五卷`
- Candidate rank: `None`
- Retrieved top chunks: `第七卷-000152, 第七卷-000077, 第六卷-000162, 第六卷-000143, 第六卷-000156`
- Top scores: `0.7500, 0.7195, 0.7167, 0.7024, 0.6830`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 大约一个星期后

### 5. 鲁迪乌斯向洛克斯介绍了哪些个人信息？

- Reason label: `candidate_miss`
- Gold chunk: `第三卷-000032`
- Gold book: `第三卷`
- Candidate rank: `None`
- Retrieved top chunks: `第三卷-000026, 第三卷-000027, 第五卷-000089, 第九卷-000170, 第三卷-000098`
- Top scores: `0.8351, 0.7171, 0.6069, 0.5749, 0.5547`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 名字、年龄、职业、先前住处、和艾莉丝的关系、艾莉丝的身分，以及想回去的愿望。

