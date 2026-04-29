# BM25 8:2 Scene Diverse Evaluation Comparison

## Metrics

| Metric | BM25 8:2 + Neighbor 2:1 | BM25 8:2 + Scene Diverse |
| --- | ---: | ---: |
| Recall@1 | 4.08% | 53.06% |
| Recall@3 | 73.47% | 53.06% |
| Recall@5 | 89.80% | 75.51% |
| MRR | 0.3401 | 0.5857 |
| Missed Count | 5 | 12 |

- Recovered Top5 cases vs neighbor 2:1: 1.
- Regressed Top5 cases vs neighbor 2:1: 8.

## Recovered Examples vs Neighbor 2:1

### 1. 在小说片段中，主角和基斯对话时，注意到了哪些异常现象？

- Gold: `book-000112` / rank 5
- Retrieved: `book-000159, book-000113, book-000153, book-000158, book-000112`


## Regressed Examples vs Neighbor 2:1

### 1. 为什么斯佩路德族的搭船费用特别贵？

- Gold: `book-000009`
- Retrieved: `book-000011, book-000013, book-000122, book-000014, book-000121`

### 2. 魔界大帝奇希莉卡·奇希里斯最让人畏惧的能力是什么？

- Gold: `book-000031`
- Retrieved: `book-000032, book-000023, book-000050, book-000022, book-000049`

### 3. 被菲兹打倒的刺客在阿斯拉王国被称为什么？

- Gold: `book-000185`
- Retrieved: `book-000186, book-000184, book-000187, book-000183, book-000168`

### 4. 菲兹在什么时候拜访了爱丽儿？

- Gold: `book-000180`
- Retrieved: `book-000181, book-000177, book-000168, book-000182, book-000176`

### 5. 主角用什么魔法攻击了试图带走少女的凶恶男子？

- Gold: `book-000019`
- Retrieved: `book-000020, book-000117, book-000030, book-000021, book-000116`

### 6. 为什么主角今天要独自行动，并拜托瑞杰路德担任护卫？

- Gold: `book-000018`
- Retrieved: `book-000019, book-000043, book-000085, book-000042, book-000084`

### 7. 走私组织是如何成功掳走圣兽的？

- Gold: `book-000127`
- Retrieved: `book-000129, book-000145, book-000092, book-000130, book-000144`

### 8. 鲁迪乌斯在房间里制作谁的人偶模型？

- Gold: `book-000143`
- Retrieved: `book-000144, book-000068, book-000158, book-000145, book-000067`

