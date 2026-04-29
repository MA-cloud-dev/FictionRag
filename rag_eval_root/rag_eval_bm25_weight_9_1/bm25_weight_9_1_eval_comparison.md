# BM25 9:1 Weight Retrieval Evaluation Comparison

## Metrics

| Metric | Scene-expanded | Dense+BM25 9:1 |
| --- | ---: | ---: |
| Recall@1 | 8.16% | 10.20% |
| Recall@3 | 77.55% | 79.59% |
| Recall@5 | 83.67% | 87.76% |
| MRR | 0.3884 | 0.4116 |
| Missed Count | 8 | 6 |

- Recovered Top5 cases: 3.
- Regressed Top5 cases: 1.

## Recovered Examples

### 1. 主角为了烧掉尸体而使用火弹时，发生了什么意外？

- Gold: `book-000090` / rank 4
- Retrieved: `book-000087, book-000088, book-000089, book-000090, book-000091`

### 2. 艾莉丝平时被要求使用哪种语言说话？

- Gold: `book-000002` / rank 2
- Retrieved: `book-000001, book-000002, book-000133, book-000134, book-000135`

### 3. 主角用什么魔法攻击了试图带走少女的凶恶男子？

- Gold: `book-000019` / rank 1
- Retrieved: `book-000019, book-000020, book-000021, book-000022, book-000023`


## Regressed Examples

### 1. 艾莉丝的外号是什么？

- Gold: `book-000007`
- Retrieved: `book-000033, book-000034, book-000035, book-000148, book-000149`

