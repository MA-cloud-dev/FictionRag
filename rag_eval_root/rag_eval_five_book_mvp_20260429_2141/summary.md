# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-29T21:55:53
- Index: `data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_five_book_mvp_20260429_2141`
- Dataset reused: `False`
- Requested sample size: `125`
- Samples per book: `{'第一卷': 25, '第二卷': 25, '第三卷': 25, '第四卷': 25, '第十卷': 25}`
- Effective sample count: `125`
- Seed: `42`
- Retrieval top_k: `5`
- Embedding model: `qwen3-vl-embedding`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 0.00% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 42.40% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 86.40% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.2524 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 0.00% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 3.53 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 17 | gold chunk 未出现在 Top 5 的样本数量。 |

## Metrics by Book

| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 第一卷 | 25 | 0.00% | 56.00% | 92.00% | 0.2767 | 2 |
| 第三卷 | 25 | 0.00% | 32.00% | 80.00% | 0.2313 | 5 |
| 第二卷 | 25 | 0.00% | 40.00% | 88.00% | 0.2580 | 3 |
| 第十卷 | 25 | 0.00% | 52.00% | 84.00% | 0.2513 | 4 |
| 第四卷 | 25 | 0.00% | 32.00% | 88.00% | 0.2447 | 3 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Examples

### 1. 主角决定成为什么？

- Gold chunk: `第一卷-000115`
- Retrieved top chunks: `第二卷-000127, 第二卷-000129, 第二卷-000130, 第二卷-000131, 第一卷-000128`
- Reference answer: 迟钝系男主角

### 2. 根据片段，说话者用什么来说服对方？

- Gold chunk: `第三卷-000091`
- Retrieved top chunks: `第三卷-000002, 第三卷-000005, 第三卷-000006, 第三卷-000007, 第十卷-000139`
- Reference answer: 魔大陆平原热带草原上的帕克斯郊狼狮子

### 3. 艾莉丝为什么从房间里冲出来？

- Gold chunk: `第二卷-000072`
- Retrieved top chunks: `第四卷-000060, 第四卷-000149, 第四卷-000150, 第四卷-000151, 第二卷-000076`
- Reference answer: 因为跳舞练习不顺利，她逃跑了。

### 4. 艾莉丝·Ｂ·格雷拉特的职业是什么？

- Gold chunk: `第二卷-000089`
- Retrieved top chunks: `第二卷-000030, 第二卷-000067, 第二卷-000068, 第二卷-000069, 第二卷-000032`
- Reference answer: 菲托亚领主的孙女。

### 5. 老婆婆认为威丝凯尔是什么种族？

- Gold chunk: `第三卷-000159`
- Retrieved top chunks: `第三卷-000134, 第三卷-000135, 第三卷-000136, 第三卷-000137, 第三卷-000160`
- Reference answer: 兹梅巴族

