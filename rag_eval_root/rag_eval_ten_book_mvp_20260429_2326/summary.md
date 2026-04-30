# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-30T10:47:36
- Index: `data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_ten_book_mvp_20260429_2326`
- Dataset reused: `True`
- Requested sample size: `200`
- Samples per book: `{}`
- Effective sample count: `197`
- Seed: `42`
- Retrieval top_k: `5`
- Embedding model: `text-embedding-v4`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 0.51% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 35.53% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 75.13% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.2192 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 0.51% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 3.59 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 49 | gold chunk 未出现在 Top 5 的样本数量。 |

## Metrics by Book

| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 第一卷 | 20 | 0.00% | 65.00% | 85.00% | 0.2642 | 3 |
| 第七卷 | 20 | 0.00% | 50.00% | 80.00% | 0.2417 | 4 |
| 第三卷 | 19 | 0.00% | 36.84% | 73.68% | 0.2149 | 5 |
| 第九卷 | 20 | 5.00% | 35.00% | 75.00% | 0.2425 | 5 |
| 第二卷 | 20 | 0.00% | 35.00% | 80.00% | 0.2325 | 4 |
| 第五卷 | 19 | 0.00% | 26.32% | 73.68% | 0.2035 | 5 |
| 第八卷 | 20 | 0.00% | 30.00% | 60.00% | 0.1725 | 8 |
| 第六卷 | 20 | 0.00% | 15.00% | 70.00% | 0.1825 | 6 |
| 第十卷 | 20 | 0.00% | 35.00% | 75.00% | 0.2117 | 5 |
| 第四卷 | 19 | 0.00% | 26.32% | 78.95% | 0.2254 | 4 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Examples

### 1. 保罗在信中称他们现在在哪里？

- Gold chunk: `第十卷-000109`
- Retrieved top chunks: `第五卷-000065, 第五卷-000066, 第五卷-000067, 第五卷-000068, 第八卷-000010`
- Reference answer: 东部港

### 2. 在原文中，普露塞娜给了主角什么？

- Gold chunk: `第九卷-000093`
- Retrieved top chunks: `第八卷-000144, 第八卷-000145, 第八卷-000146, 第八卷-000147, 第八卷-000167`
- Reference answer: 她吃到一半的肉乾

### 3. 诺伦·格雷拉特的父母是谁？

- Gold chunk: `第五卷-000044`
- Retrieved top chunks: `第一卷-000033, 第一卷-000034, 第一卷-000035, 第一卷-000036, 第七卷-000034`
- Reference answer: 保罗和塞妮丝。

### 4. 鲁迪乌斯计划在多久后离开当前的城市？

- Gold chunk: `第五卷-000084`
- Retrieved top chunks: `第六卷-000154, 第六卷-000162, 第六卷-000163, 第六卷-000164, 第六卷-000015`
- Reference answer: 大约一个星期后

### 5. 鲁迪乌斯向洛克斯介绍了哪些个人信息？

- Gold chunk: `第三卷-000032`
- Retrieved top chunks: `第三卷-000024, 第三卷-000025, 第三卷-000026, 第三卷-000027, 第九卷-000020`
- Reference answer: 名字、年龄、职业、先前住处、和艾莉丝的关系、艾莉丝的身分，以及想回去的愿望。

