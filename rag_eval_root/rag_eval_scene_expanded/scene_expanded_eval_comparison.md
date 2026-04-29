# Scene Expanded Retrieval Evaluation

## Setup

- Dataset: `rag_eval_scene_expanded/dataset.jsonl` copied from `rag_eval_chunk_optimized/dataset.jsonl`.
- Retrieval strategy: vector topN=20, aggregate by `scene_id`, select top 3 scenes, add hit neighbors ±1, then fill same-scene chunks, return 5 context chunks ordered by source position.
- Old `rag_eval` and `rag_eval_chunk_optimized` files were not modified by this comparison except this dedicated output directory.

## Metrics

| Metric | New chunk only | Scene-expanded | Delta |
| --- | ---: | ---: | ---: |
| Recall@1 | 42.86% | 8.16% | -34.69% |
| Recall@3 | 67.35% | 77.55% | +10.20% |
| Recall@5 | 67.35% | 83.67% | +16.33% |
| MRR | 0.5442 | 0.3884 | -0.1558 |
| Missed Count | 16 | 8 | -8 |
| Same Scene Recall@5 | 81.63% | 87.76% | +6.12% |

## Notes

- Recall@5 is the main signal for this strategy because retrieval now returns source-ordered context chunks, so the gold chunk may appear after preceding context inside the same scene.
- The strategy recovers exact Top5 hits by using scene structure while still keeping the final context readable in novel order.
- Recovered Top5 cases: 10. Regressed Top5 cases: 2.

## Recovered Examples

### 1. 鲁迪乌斯在船舱中借口去做什么？

- Gold: `book-000073` / rank 3
- Retrieved: `book-000070, book-000071, book-000073, book-000074, book-000075`

### 2. 魔界大帝奇希莉卡·奇希里斯最让人畏惧的能力是什么？

- Gold: `book-000031` / rank 3
- Retrieved: `book-000022, book-000023, book-000031, book-000032, book-000033`

### 3. 被菲兹打倒的刺客在阿斯拉王国被称为什么？

- Gold: `book-000185` / rank 3
- Retrieved: `book-000167, book-000168, book-000185, book-000186, book-000187`

### 4. 在片段中，艾莉丝称呼基列奴为什么？

- Gold: `book-000133` / rank 2
- Retrieved: `book-000132, book-000133, book-000134, book-000135, book-000136`

### 5. 在小说片段中，主角和基斯对话时，注意到了哪些异常现象？

- Gold: `book-000112` / rank 3
- Retrieved: `book-000107, book-000108, book-000112, book-000113, book-000114`

### 6. 菲兹在什么时候拜访了爱丽儿？

- Gold: `book-000180` / rank 1
- Retrieved: `book-000180, book-000181, book-000182, book-000183, book-000184`

### 7. 为什么主角今天要独自行动，并拜托瑞杰路德担任护卫？

- Gold: `book-000018` / rank 1
- Retrieved: `book-000018, book-000019, book-000020, book-000047, book-000048`

### 8. 菲兹最近总是向谁请教各种事情？

- Gold: `book-000176` / rank 2
- Retrieved: `book-000175, book-000176, book-000177, book-000178, book-000179`

## Regressed Examples

### 1. 主角为了烧掉尸体而使用火弹时，发生了什么意外？

- Gold: `book-000090`
- Retrieved: `book-000114, book-000116, book-000117, book-000118, book-000119`

### 2. 艾莉丝平时被要求使用哪种语言说话？

- Gold: `book-000002`
- Retrieved: `book-000133, book-000134, book-000135, book-000138, book-000139`

