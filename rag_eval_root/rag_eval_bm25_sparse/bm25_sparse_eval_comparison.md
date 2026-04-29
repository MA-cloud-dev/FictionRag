# BM25 Sparse Retrieval Evaluation Comparison

## Metrics

| Metric | Scene-expanded | Dense+BM25 |
| --- | ---: | ---: |
| Recall@1 | 8.16% | 12.24% |
| Recall@3 | 77.55% | 71.43% |
| Recall@5 | 83.67% | 77.55% |
| MRR | 0.3884 | 0.3861 |
| Missed Count | 8 | 11 |

- Recovered Top5 cases: 3.
- Regressed Top5 cases: 6.

## Recovered Examples

### 1. 艾莉丝平时被要求使用哪种语言说话？

- Gold: `book-000002` / rank 2
- Retrieved: `book-000001, book-000002, book-000003, book-000004, book-000005`

### 2. 艾莉丝为什么突然宣布要回去并离开？

- Gold: `book-000036` / rank 3
- Retrieved: `book-000034, book-000035, book-000036, book-000037, book-000038`

### 3. 主角用什么魔法攻击了试图带走少女的凶恶男子？

- Gold: `book-000019` / rank 1
- Retrieved: `book-000019, book-000020, book-000021, book-000022, book-000023`


## Regressed Examples

### 1. 鲁迪乌斯使用什么方法来帮助艾莉丝缓解晕船？

- Gold: `book-000071`
- Retrieved: `book-000138, book-000139, book-000140, book-000141, book-000142`

### 2. 在走私任务中，艾莉丝被要求做什么？

- Gold: `book-000065`
- Retrieved: `book-000033, book-000034, book-000035, book-000074, book-000075`

### 3. 根据该片段，兽族是什么？

- Gold: `book-000141`
- Retrieved: `book-000115, book-000116, book-000117, book-000118, book-000119`

### 4. 在小说片段中，主角和基斯对话时，注意到了哪些异常现象？

- Gold: `book-000112`
- Retrieved: `book-000116, book-000158, book-000159, book-000160, book-000161`

### 5. 艾莉丝的外号是什么？

- Gold: `book-000007`
- Retrieved: `book-000002, book-000003, book-000033, book-000034, book-000035`

### 6. 菲兹是如何中毒的？

- Gold: `book-000184`
- Retrieved: `book-000175, book-000176, book-000177, book-000178, book-000179`

