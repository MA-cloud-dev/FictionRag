# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-30T19:05:13
- Index: `data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_26_book_regression_old_ten_qwen3_rerank_route5_v100_b100_top30_20260430_1850`
- Dataset reused: `True`
- Requested sample size: `200`
- Samples per book: `{}`
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
- Rerank cache hits: `2947`
- Rerank API scored: `2963`
- Rerank API calls: `196`
- Embedding model: `text-embedding-v4`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 72.08% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 81.22% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 82.23% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.7640 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 72.08% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 1.19 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 35 | gold chunk 未出现在 Top 5 的样本数量。 |
| Candidate Hit@30 | 83.25% | gold chunk 出现在 rerank 前 Top 30 候选池的比例。 |
| Candidate Miss@30 | 33 | gold chunk 未进入 rerank 前 Top 30 候选池的数量。 |
| Rerank Lost Count | 2 | gold chunk 进入候选池但最终没进 Top 5 的数量。 |

## Baseline Comparison

| Metric | Baseline route=3 cap=3 | Current | Delta |
| --- | ---: | ---: | ---: |
| Recall@1 | 65.99% | 72.08% | +6.09% |
| Recall@3 | 75.13% | 81.22% | +6.09% |
| Recall@5 | 78.68% | 82.23% | +3.55% |
| MRR | 0.7084 | 0.7640 | +0.0556 |
| Missed Count | 42 | 35 | -7 |

## Metrics by Book

| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed | Candidate Hit@30 | Rerank Lost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 第一卷 | 20 | 90.00% | 90.00% | 90.00% | 0.9000 | 2 | 90.00% | 0 |
| 第七卷 | 20 | 85.00% | 100.00% | 100.00% | 0.9167 | 0 | 100.00% | 0 |
| 第三卷 | 19 | 68.42% | 73.68% | 73.68% | 0.7105 | 5 | 73.68% | 0 |
| 第九卷 | 20 | 70.00% | 80.00% | 80.00% | 0.7500 | 4 | 80.00% | 0 |
| 第二卷 | 20 | 70.00% | 75.00% | 75.00% | 0.7250 | 5 | 75.00% | 0 |
| 第五卷 | 19 | 57.89% | 68.42% | 73.68% | 0.6272 | 5 | 78.95% | 1 |
| 第八卷 | 20 | 65.00% | 75.00% | 75.00% | 0.7000 | 5 | 80.00% | 1 |
| 第六卷 | 20 | 75.00% | 85.00% | 85.00% | 0.7917 | 3 | 85.00% | 0 |
| 第十卷 | 20 | 65.00% | 70.00% | 75.00% | 0.6792 | 5 | 75.00% | 0 |
| 第四卷 | 19 | 73.68% | 94.74% | 94.74% | 0.8333 | 1 | 94.74% | 0 |

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
- Retrieved top chunks: `第十二卷-000009, 第十二卷-000007, 第五卷-000067, 第十二卷-000010, 第五卷-000104`
- Top scores: `0.7546, 0.7217, 0.6785, 0.6762, 0.6300`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 东部港

### 2. 在片段中，主角自称是什么人？

- Reason label: `rerank_lost`
- Gold chunk: `第五卷-000017`
- Gold book: `第五卷`
- Candidate rank: `1`
- Retrieved top chunks: `第二十三卷-000128, 第六卷-000029, 第六卷-000054, 第六卷-000056, 第二十三卷-000127`
- Top scores: `0.8414, 0.8301, 0.8056, 0.7456, 0.7274`
- Gold base score: `0.9165`
- Gold rerank score: `0.6874`
- Reference answer: 『Dead End』的瑞杰路德

### 3. 在原文中，普露塞娜给了主角什么？

- Reason label: `candidate_miss`
- Gold chunk: `第九卷-000093`
- Gold book: `第九卷`
- Candidate rank: `None`
- Retrieved top chunks: `第十八卷-000120, 第十一卷-000055, 第十三卷-000176, 第十八卷-000165, 第十八卷-000129`
- Top scores: `0.9113, 0.9092, 0.9091, 0.9062, 0.9058`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 她吃到一半的肉乾

### 4. 诺伦·格雷拉特的父母是谁？

- Reason label: `candidate_miss`
- Gold chunk: `第五卷-000044`
- Gold book: `第五卷`
- Candidate rank: `None`
- Retrieved top chunks: `第二十六卷-000124, 第七卷-000034, 第一卷-000035, 第二十六卷-000125, 第二十卷-000123`
- Top scores: `0.9332, 0.8900, 0.8781, 0.8356, 0.8356`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 保罗和塞妮丝。

### 5. 鲁迪乌斯计划在多久后离开当前的城市？

- Reason label: `candidate_miss`
- Gold chunk: `第五卷-000084`
- Gold book: `第五卷`
- Candidate rank: `None`
- Retrieved top chunks: `第二十二卷-000014, 第七卷-000152, 第六卷-000162, 第六卷-000143, 第六卷-000156`
- Top scores: `0.8405, 0.7500, 0.7167, 0.7024, 0.6830`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 大约一个星期后

