# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-30T11:28:00
- Index: `data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_ten_book_book_route3_20260430_1125`
- Dataset reused: `True`
- Requested sample size: `200`
- Samples per book: `{'第一卷': 25, '第二卷': 25, '第三卷': 25, '第四卷': 25, '第五卷': 25, '第六卷': 25, '第七卷': 25, '第八卷': 25, '第九卷': 25, '第十卷': 25}`
- Effective sample count: `197`
- Seed: `42`
- Retrieval top_k: `5`
- Book route count: `3`
- Book result cap: `3`
- Embedding model: `text-embedding-v4`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 65.99% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 75.13% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 78.68% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.7084 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 65.99% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 1.32 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 42 | gold chunk 未出现在 Top 5 的样本数量。 |

## Metrics by Book

| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 第一卷 | 20 | 80.00% | 80.00% | 85.00% | 0.8100 | 3 |
| 第七卷 | 20 | 80.00% | 90.00% | 90.00% | 0.8500 | 2 |
| 第三卷 | 19 | 63.16% | 73.68% | 73.68% | 0.6842 | 5 |
| 第九卷 | 20 | 60.00% | 75.00% | 80.00% | 0.6708 | 4 |
| 第二卷 | 20 | 70.00% | 70.00% | 75.00% | 0.7125 | 5 |
| 第五卷 | 19 | 68.42% | 73.68% | 73.68% | 0.7018 | 5 |
| 第八卷 | 20 | 50.00% | 65.00% | 70.00% | 0.5683 | 6 |
| 第六卷 | 20 | 55.00% | 70.00% | 75.00% | 0.6292 | 5 |
| 第十卷 | 20 | 70.00% | 75.00% | 75.00% | 0.7250 | 5 |
| 第四卷 | 19 | 63.16% | 78.95% | 89.47% | 0.7316 | 2 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Examples

### 1. 保罗在信中称他们现在在哪里？

- Gold chunk: `第十卷-000109`
- Retrieved top chunks: `第五卷-000067, 第五卷-000068, 第五卷-000066, 第八卷-000010, 第三卷-000027`
- Reference answer: 东部港

### 2. 在原文中，普露塞娜给了主角什么？

- Gold chunk: `第九卷-000093`
- Retrieved top chunks: `第八卷-000146, 第八卷-000147, 第七卷-000171, 第七卷-000169, 第九卷-000034`
- Reference answer: 她吃到一半的肉乾

### 3. 诺伦·格雷拉特的父母是谁？

- Gold chunk: `第五卷-000044`
- Retrieved top chunks: `第一卷-000035, 第七卷-000034, 第五卷-000098, 第五卷-000099, 第五卷-000130`
- Reference answer: 保罗和塞妮丝。

### 4. 鲁迪乌斯计划在多久后离开当前的城市？

- Gold chunk: `第五卷-000084`
- Retrieved top chunks: `第六卷-000164, 第七卷-000146, 第六卷-000162, 第六卷-000015, 第一卷-000096`
- Reference answer: 大约一个星期后

### 5. 鲁迪乌斯向洛克斯介绍了哪些个人信息？

- Gold chunk: `第三卷-000032`
- Retrieved top chunks: `第三卷-000027, 第五卷-000056, 第九卷-000171, 第九卷-000170, 第九卷-000020`
- Reference answer: 名字、年龄、职业、先前住处、和艾莉丝的关系、艾莉丝的身分，以及想回去的愿望。

