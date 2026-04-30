# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-30T16:58:34
- Index: `data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_ten_book_qwen3_rerank_route5_v100_b100_top30_20260430_1645`
- Dataset reused: `True`
- Requested sample size: `200`
- Samples per book: `{'第一卷': 25, '第二卷': 25, '第三卷': 25, '第四卷': 25, '第五卷': 25, '第六卷': 25, '第七卷': 25, '第八卷': 25, '第九卷': 25, '第十卷': 25}`
- Effective sample count: `197`
- Seed: `42`
- Retrieval top_k: `5`
- Book route count: `5`
- Book result cap: `3`
- Rerank enabled: `True`
- Reranker model: `qwen3-rerank`
- Rerank candidate top_n: `30`
- Rerank vector top_n: `100`
- Rerank BM25 top_n: `100`
- Rerank cache hits: `0`
- Rerank API scored: `5910`
- Rerank API calls: `197`
- Embedding model: `text-embedding-v4`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 77.16% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 87.82% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 89.34% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.8276 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 77.16% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 1.18 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 21 | gold chunk 未出现在 Top 5 的样本数量。 |
| Candidate Hit@30 | 91.37% | gold chunk 出现在 rerank 前 Top 30 候选池的比例。 |
| Candidate Miss@30 | 17 | gold chunk 未进入 rerank 前 Top 30 候选池的数量。 |
| Rerank Lost Count | 4 | gold chunk 进入候选池但最终没进 Top 5 的数量。 |

## Baseline Comparison

| Metric | Baseline route=3 cap=3 | Current | Delta |
| --- | ---: | ---: | ---: |
| Recall@1 | 65.99% | 77.16% | +11.17% |
| Recall@3 | 75.13% | 87.82% | +12.69% |
| Recall@5 | 78.68% | 89.34% | +10.66% |
| MRR | 0.7084 | 0.8276 | +0.1192 |
| Missed Count | 42 | 21 | -21 |

## Metrics by Book

| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed | Candidate Hit@30 | Rerank Lost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 第一卷 | 20 | 95.00% | 95.00% | 95.00% | 0.9500 | 1 | 95.00% | 0 |
| 第七卷 | 20 | 85.00% | 100.00% | 100.00% | 0.9250 | 0 | 100.00% | 0 |
| 第三卷 | 19 | 68.42% | 73.68% | 78.95% | 0.7211 | 4 | 84.21% | 1 |
| 第九卷 | 20 | 75.00% | 85.00% | 85.00% | 0.8000 | 3 | 85.00% | 0 |
| 第二卷 | 20 | 75.00% | 80.00% | 80.00% | 0.7750 | 4 | 80.00% | 0 |
| 第五卷 | 19 | 63.16% | 78.95% | 78.95% | 0.7105 | 4 | 89.47% | 2 |
| 第八卷 | 20 | 75.00% | 80.00% | 85.00% | 0.7875 | 3 | 90.00% | 1 |
| 第六卷 | 20 | 85.00% | 100.00% | 100.00% | 0.9167 | 0 | 100.00% | 0 |
| 第十卷 | 20 | 70.00% | 85.00% | 90.00% | 0.7875 | 2 | 90.00% | 0 |
| 第四卷 | 19 | 78.95% | 100.00% | 100.00% | 0.8947 | 0 | 100.00% | 0 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Example Analysis

### 1. 鲁迪乌斯计划在多久后离开当前的城市？

- Reason label: `candidate_miss`
- Gold chunk: `第五卷-000084`
- Gold book: `第五卷`
- Candidate rank: `None`
- Retrieved top chunks: `第七卷-000152, 第七卷-000077, 第六卷-000162, 第六卷-000143, 第六卷-000156`
- Top scores: `0.7500, 0.7195, 0.7167, 0.7024, 0.6830`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 大约一个星期后

### 2. 诺伦·格雷拉特的父母是谁？

- Reason label: `rerank_lost`
- Gold chunk: `第五卷-000044`
- Gold book: `第五卷`
- Candidate rank: `10`
- Retrieved top chunks: `第七卷-000034, 第一卷-000035, 第五卷-000098, 第二卷-000005, 第五卷-000080`
- Top scores: `0.8900, 0.8781, 0.7993, 0.7399, 0.6835`
- Gold base score: `0.7335`
- Gold rerank score: `0.6717`
- Reference answer: 保罗和塞妮丝。

### 3. 鲁迪乌斯向洛克斯介绍了哪些个人信息？

- Reason label: `candidate_miss`
- Gold chunk: `第三卷-000032`
- Gold book: `第三卷`
- Candidate rank: `None`
- Retrieved top chunks: `第三卷-000026, 第三卷-000027, 第二卷-000152, 第六卷-000045, 第九卷-000170`
- Top scores: `0.8351, 0.7171, 0.6634, 0.6043, 0.5749`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 名字、年龄、职业、先前住处、和艾莉丝的关系、艾莉丝的身分，以及想回去的愿望。

### 4. 鲁迪乌斯在片段中遇到了哪两个人？

- Reason label: `candidate_miss`
- Gold chunk: `第十卷-000141`
- Gold book: `第十卷`
- Candidate rank: `None`
- Retrieved top chunks: `第七卷-000148, 第九卷-000010, 第六卷-000157, 第六卷-000156, 第九卷-000129`
- Top scores: `0.8639, 0.8520, 0.8385, 0.8277, 0.8265`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 诺伦·格雷拉特和爱夏·格雷拉特。

### 5. 在最初期的构思中，艾丽丝为何前往剑之圣地？

- Reason label: `candidate_miss`
- Gold chunk: `第九卷-000200`
- Gold book: `第九卷`
- Candidate rank: `None`
- Retrieved top chunks: `第六卷-000164, 第九卷-000198, 第九卷-000186, 第九卷-000187, 第十卷-000155`
- Top scores: `0.8179, 0.7388, 0.7083, 0.7062, 0.6747`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 因为卢迪乌斯与艾丽丝对于败给奥尔斯蒂德一事深感力量不足，艾丽丝前往剑之圣地深造。

