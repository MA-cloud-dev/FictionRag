# BM25 8:2 Neighbor 2:1 Evaluation Comparison

## Metrics

| Metric | BM25 8:2 | BM25 8:2 + Neighbor 2:1 |
| --- | ---: | ---: |
| Recall@1 | 12.24% | 4.08% |
| Recall@3 | 79.59% | 73.47% |
| Recall@5 | 87.76% | 89.80% |
| MRR | 0.4320 | 0.3401 |
| Missed Count | 6 | 5 |

- Recovered Top5 cases vs 8:2: 2.
- Regressed Top5 cases vs 8:2: 1.

## Recovered Examples vs 8:2

### 1. 为什么斯佩路德族的搭船费用特别贵？

- Gold: `book-000009` / rank 1
- Retrieved: `book-000009, book-000010, book-000011, book-000012, book-000013`

### 2. 走私组织是如何成功掳走圣兽的？

- Gold: `book-000127` / rank 1
- Retrieved: `book-000127, book-000128, book-000129, book-000130, book-000131`


## Regressed Examples vs 8:2

### 1. 在小说片段中，主角和基斯对话时，注意到了哪些异常现象？

- Gold: `book-000112`
- Retrieved: `book-000157, book-000158, book-000159, book-000160, book-000161`

