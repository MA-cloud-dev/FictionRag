# Same Scene Recall Evaluation

- Index: `data\index\chunks.jsonl`
- Results: `rag_eval_chunk_optimized\results.jsonl`
- Sample count: 49
- Same Scene Recall@K means a result is counted as hit if any retrieved chunk in Top K has the same `scene_id` as the gold chunk.

## Metrics

| K | Exact Recall@K | Same Scene Recall@K | Delta |
| ---: | ---: | ---: | ---: |
| 1 | 42.86% | 73.47% | +30.61% |
| 3 | 67.35% | 77.55% | +10.20% |
| 5 | 67.35% | 81.63% | +14.29% |

## Interpretation

- Exact missed but same-scene hit within Top 5: 7 cases.
- Still missed by Same Scene Recall@5: 9 cases.
- This shows how much structure-aware retrieval could recover if vector hits were expanded or accepted at scene granularity.

## Exact Misses Recovered By Same Scene@5

### 1. 鲁迪乌斯在船舱中借口去做什么？

- Gold: `book-000073` / `chapter-005-scene-002` / 第四卷 少年期冒险者入门篇 第四话「船上的贤者」
- Retrieved: book-000074(chapter-005-scene-002), book-000098(chapter-007-scene-003), book-000048(chapter-003-scene-006), book-000101(chapter-007-scene-003), book-000068(chapter-005-scene-001)

### 2. 在赞特港，鲁迪乌斯他们将魔大陆的货币兑换后，得到了哪些米里斯货币？每种各多少枚？

- Gold: `book-000075` / `chapter-005-scene-003` / 第四卷 少年期冒险者入门篇 第四话「船上的贤者」
- Retrieved: book-000006(chapter-001-scene-002), book-000077(chapter-006-scene-000), book-000013(chapter-001-scene-005), book-000076(chapter-005-scene-003), book-000014(chapter-001-scene-005)

### 3. 被菲兹打倒的刺客在阿斯拉王国被称为什么？

- Gold: `book-000185` / `chapter-011-scene-012` / 第四卷 少年期冒险者入门篇 第十话「圣剑大道」
- Retrieved: book-000186(chapter-011-scene-013), book-000168(chapter-011-scene-008), book-000187(chapter-011-scene-014), book-000183(chapter-011-scene-012), book-000184(chapter-011-scene-012)

### 4. 在片段中，艾莉丝称呼基列奴为什么？

- Gold: `book-000133` / `chapter-010-scene-001` / 第四卷 少年期冒险者入门篇 第九话「德路迪亚村的悠哉生活」
- Retrieved: book-000134(chapter-010-scene-001), book-000135(chapter-010-scene-001), book-000140(chapter-010-scene-003), book-000008(chapter-001-scene-002), book-000158(chapter-011-scene-004)

### 5. 在小说片段中，主角和基斯对话时，注意到了哪些异常现象？

- Gold: `book-000112` / `chapter-008-scene-002` / 第四卷 少年期冒险者入门篇 第七话「免费公寓」
- Retrieved: book-000113(chapter-008-scene-002), book-000153(chapter-011-scene-002), book-000108(chapter-008-scene-002), book-000159(chapter-011-scene-004), book-000114(chapter-009-scene-000)

### 6. 菲兹最近总是向谁请教各种事情？

- Gold: `book-000176` / `chapter-011-scene-010` / 第四卷 少年期冒险者入门篇 第十话「圣剑大道」
- Retrieved: book-000177(chapter-011-scene-010), book-000168(chapter-011-scene-008), book-000178(chapter-011-scene-010), book-000169(chapter-011-scene-008), book-000187(chapter-011-scene-014)

### 7. 艾莉丝的外号是什么？

- Gold: `book-000007` / `chapter-001-scene-002` / 第四卷 少年期冒险者入门篇 第一话「温恩港」
- Retrieved: book-000008(chapter-001-scene-002), book-000034(chapter-003-scene-003), book-000148(chapter-011-scene-000), book-000149(chapter-011-scene-000), book-000134(chapter-010-scene-001)

## Same Scene@5 Still Missed

### 1. 在魔大陆时，是谁发现小偷的痕迹并追上去教训了对方？

- Gold: `book-000079` / `chapter-006-scene-000` / 第四卷 少年期冒险者入门篇 第五话「仓库里的恶魔」
- Retrieved: book-000001(chapter-001-scene-000), book-000030(chapter-003-scene-000), book-000045(chapter-003-scene-006), book-000051(chapter-004-scene-000), book-000052(chapter-004-scene-000)

### 2. 为什么斯佩路德族的搭船费用特别贵？

- Gold: `book-000009` / `chapter-001-scene-002` / 第四卷 少年期冒险者入门篇 第一话「温恩港」
- Retrieved: book-000011(chapter-001-scene-003), book-000013(chapter-001-scene-005), book-000122(chapter-009-scene-000), book-000014(chapter-001-scene-005), book-000004(chapter-001-scene-001)

### 3. 魔界大帝奇希莉卡·奇希里斯最让人畏惧的能力是什么？

- Gold: `book-000031` / `chapter-003-scene-000` / 第四卷 少年期冒险者入门篇 第三话「阴错阳差·下篇」
- Retrieved: book-000032(chapter-003-scene-001), book-000023(chapter-002-scene-002), book-000024(chapter-002-scene-002), book-000028(chapter-002-scene-002), book-000022(chapter-002-scene-002)

### 4. 菲兹在什么时候拜访了爱丽儿？

- Gold: `book-000180` / `chapter-011-scene-011` / 第四卷 少年期冒险者入门篇 第十话「圣剑大道」
- Retrieved: book-000181(chapter-011-scene-012), book-000177(chapter-011-scene-010), book-000168(chapter-011-scene-008), book-000178(chapter-011-scene-010), book-000182(chapter-011-scene-012)

### 5. 艾莉丝为什么突然宣布要回去并离开？

- Gold: `book-000036` / `chapter-003-scene-004` / 第四卷 少年期冒险者入门篇 第三话「阴错阳差·下篇」
- Retrieved: book-000149(chapter-011-scene-000), book-000148(chapter-011-scene-000), book-000075(chapter-005-scene-003), book-000040(chapter-003-scene-005), book-000003(chapter-001-scene-001)

### 6. 主角用什么魔法攻击了试图带走少女的凶恶男子？

- Gold: `book-000019` / `chapter-002-scene-001` / 第四卷 少年期冒险者入门篇 第二话「阴错阳差·上篇」
- Retrieved: book-000117(chapter-009-scene-000), book-000020(chapter-002-scene-002), book-000124(chapter-009-scene-000), book-000118(chapter-009-scene-000), book-000184(chapter-011-scene-012)

### 7. 为什么主角今天要独自行动，并拜托瑞杰路德担任护卫？

- Gold: `book-000018` / `chapter-002-scene-000` / 第四卷 少年期冒险者入门篇 第二话「阴错阳差·上篇」
- Retrieved: book-000019(chapter-002-scene-001), book-000048(chapter-003-scene-006), book-000085(chapter-006-scene-001), book-000104(chapter-008-scene-001), book-000043(chapter-003-scene-006)

### 8. 走私组织是如何成功掳走圣兽的？

- Gold: `book-000127` / `chapter-009-scene-000` / 第四卷 少年期冒险者入门篇 第八话「十万火急」
- Retrieved: book-000129(chapter-009-scene-001), book-000130(chapter-009-scene-001), book-000145(chapter-010-scene-004), book-000144(chapter-010-scene-004), book-000146(chapter-010-scene-004)

