# RAG Retrieval Evaluation Summary

- Generated at: 2026-04-30T20:54:09
- Index: `data\index\chunks.jsonl`
- Output dir: `rag_eval_root\rag_eval_26_book_new16_only_qwen3_rerank_route5_v100_b100_top30_20260430_2010`
- Dataset reused: `False`
- Requested sample size: `320`
- Samples per book: `{'第十一卷': 20, '第十二卷': 20, '第十三卷': 20, '第十四卷': 20, '第十五卷': 20, '第十六卷': 20, '第十七卷': 20, '第十八卷': 20, '第十九卷': 20, '第二十卷': 20, '第二十一卷': 20, '第二十二卷': 20, '第二十三卷': 20, '第二十四卷': 20, '第二十五卷': 20, '第二十六卷': 20}`
- Effective sample count: `319`
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
- Rerank API scored: `9570`
- Rerank API calls: `319`
- Embedding model: `text-embedding-v4`
- LLM model for question generation: `deepseek-v4-flash`

## Metrics

| Metric | Value | Meaning |
| --- | ---: | --- |
| Recall@1 | 67.08% | gold chunk 出现在第 1 个召回结果中的比例。 |
| Recall@3 | 85.27% | gold chunk 出现在前 3 个召回结果中的比例。 |
| Recall@5 | 85.89% | gold chunk 出现在前 5 个召回结果中的比例。 |
| MRR | 0.7564 | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |
| Top1 Hit Rate | 67.08% | 与 Recall@1 相同，是最严格的直接命中能力。 |
| Average Gold Rank | 1.28 | 只在命中的样本中计算 gold chunk 的平均排名。 |
| Missed Count | 45 | gold chunk 未出现在 Top 5 的样本数量。 |
| Candidate Hit@30 | 87.15% | gold chunk 出现在 rerank 前 Top 30 候选池的比例。 |
| Candidate Miss@30 | 41 | gold chunk 未进入 rerank 前 Top 30 候选池的数量。 |
| Rerank Lost Count | 4 | gold chunk 进入候选池但最终没进 Top 5 的数量。 |

## Baseline Comparison

| Metric | Baseline route=3 cap=3 | Current | Delta |
| --- | ---: | ---: | ---: |
| Recall@1 | 65.99% | 67.08% | +1.09% |
| Recall@3 | 75.13% | 85.27% | +10.14% |
| Recall@5 | 78.68% | 85.89% | +7.21% |
| MRR | 0.7084 | 0.7564 | +0.0480 |
| Missed Count | 42 | 45 | +3 |

## Metrics by Book

| Book | Samples | Recall@1 | Recall@3 | Recall@5 | MRR | Missed | Candidate Hit@30 | Rerank Lost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 第二十一卷 | 20 | 60.00% | 75.00% | 75.00% | 0.6750 | 5 | 80.00% | 1 |
| 第二十三卷 | 20 | 70.00% | 90.00% | 90.00% | 0.7833 | 2 | 95.00% | 1 |
| 第二十二卷 | 20 | 80.00% | 85.00% | 85.00% | 0.8250 | 3 | 90.00% | 1 |
| 第二十五卷 | 20 | 30.00% | 70.00% | 75.00% | 0.5042 | 5 | 75.00% | 0 |
| 第二十六卷 | 20 | 60.00% | 95.00% | 95.00% | 0.7750 | 1 | 95.00% | 0 |
| 第二十卷 | 20 | 65.00% | 80.00% | 80.00% | 0.7167 | 4 | 85.00% | 1 |
| 第二十四卷 | 20 | 80.00% | 90.00% | 90.00% | 0.8500 | 2 | 90.00% | 0 |
| 第十一卷 | 20 | 65.00% | 90.00% | 90.00% | 0.7583 | 2 | 90.00% | 0 |
| 第十七卷 | 20 | 75.00% | 90.00% | 90.00% | 0.8167 | 2 | 90.00% | 0 |
| 第十三卷 | 20 | 70.00% | 85.00% | 90.00% | 0.7767 | 2 | 90.00% | 0 |
| 第十九卷 | 20 | 70.00% | 90.00% | 90.00% | 0.8000 | 2 | 90.00% | 0 |
| 第十二卷 | 19 | 57.89% | 78.95% | 78.95% | 0.6754 | 4 | 78.95% | 0 |
| 第十五卷 | 20 | 65.00% | 80.00% | 80.00% | 0.7083 | 4 | 80.00% | 0 |
| 第十八卷 | 20 | 85.00% | 95.00% | 95.00% | 0.9000 | 1 | 95.00% | 0 |
| 第十六卷 | 20 | 70.00% | 85.00% | 85.00% | 0.7583 | 3 | 85.00% | 0 |
| 第十四卷 | 20 | 70.00% | 85.00% | 85.00% | 0.7750 | 3 | 85.00% | 0 |

## Interpretation

- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。
- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。
- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。
- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。

## Failed Example Analysis

### 1. 这名男子是谁？

- Reason label: `candidate_miss`
- Gold chunk: `第十五卷-000163`
- Gold book: `第十五卷`
- Candidate rank: `None`
- Retrieved top chunks: `第十八卷-000007, 第二十一卷-000147, 第十七卷-000100, 第二十一卷-000038, 第二十三卷-000166`
- Top scores: `0.7995, 0.7561, 0.7277, 0.7239, 0.6986`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 他是魔法大学的校长盖奥尔格。

### 2. 根据片段，妮娜与艾莉丝之间是什么关系？

- Reason label: `rerank_lost`
- Gold chunk: `第二十三卷-000087`
- Gold book: `第二十三卷`
- Candidate rank: `22`
- Retrieved top chunks: `第九卷-000192, 第二十卷-000076, 第九卷-000193, 第二十三卷-000088, 第二十卷-000083`
- Top scores: `0.9534, 0.9360, 0.9287, 0.9254, 0.9148`
- Gold base score: `0.7252`
- Gold rerank score: `0.8691`
- Reference answer: 妮娜是敢跟艾莉丝正面吵架的危险人物。

### 3. 主角最后对神子做了什么动作？

- Reason label: `book_cap_filtered`
- Gold chunk: `第二十一卷-000052`
- Gold book: `第二十一卷`
- Candidate rank: `9`
- Retrieved top chunks: `第二十一卷-000138, 第二十一卷-000068, 第二十一卷-000139, 第二十卷-000173, 第二十卷-000167`
- Top scores: `0.8398, 0.8293, 0.8187, 0.6624, 0.5854`
- Gold base score: `0.7790`
- Gold rerank score: `0.8013`
- Reference answer: 绑架了神子

### 4. 谁跪倒在地？

- Reason label: `candidate_miss`
- Gold chunk: `第二十五卷-000074`
- Gold book: `第二十五卷`
- Candidate rank: `None`
- Retrieved top chunks: `第十七卷-000131, 第二卷-000147, 第十四卷-000133, 第四卷-000021, 第十二卷-000153`
- Top scores: `0.8863, 0.8668, 0.8480, 0.8445, 0.7692`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 香杜尔

### 5. 洛琪希发现自己犯了什么错误？

- Reason label: `candidate_miss`
- Gold chunk: `第十三卷-000027`
- Gold book: `第十三卷`
- Candidate rank: `None`
- Retrieved top chunks: `第十九卷-000145, 第四卷-000061, 第十九卷-000083, 第十九卷-000080, 第十二卷-000137`
- Top scores: `0.9643, 0.9585, 0.9530, 0.9488, 0.9468`
- Gold base score: `N/A`
- Gold rerank score: `N/A`
- Reference answer: 她记错了时间，今天开学第一天教师们要一大早开会，而她却迟到了。

## Generation Errors

1 chunk(s) failed during question generation.

- 第十二卷-000002: LLM API request failed: HTTPSConnectionPool(host='api.deepseek.com', port=443): Max retries exceeded with url: /chat/completions (Caused by SSLError(SSLEOFError(8, 'EOF occurred in violation of protocol (_ssl.c:997)')))
