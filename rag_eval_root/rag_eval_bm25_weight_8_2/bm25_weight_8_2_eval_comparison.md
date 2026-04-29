# BM25 8:2 Weight Retrieval Evaluation Comparison

## Metrics

| Metric | Dense+BM25 9:1 | Dense+BM25 8:2 |
| --- | ---: | ---: |
| Recall@1 | 10.20% | 12.24% |
| Recall@3 | 79.59% | 79.59% |
| Recall@5 | 87.76% | 87.76% |
| MRR | 0.4116 | 0.4320 |
| Missed Count | 6 | 6 |

- Recovered Top5 cases vs 9:1: 1.
- Regressed Top5 cases vs 9:1: 1.

## Recovered Examples vs 9:1

### 1. 艾莉丝为什么突然宣布要回去并离开？

- Gold: `book-000036` / rank 3
- Retrieved: `book-000034, book-000035, book-000036, book-000037, book-000038`


## Regressed Examples vs 9:1

### 1. 菲兹是如何中毒的？

- Gold: `book-000184`
- Retrieved: `book-000175, book-000176, book-000177, book-000178, book-000179`

