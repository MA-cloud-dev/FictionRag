# Hybrid Rescue Slot Evaluation Comparison

## Metrics

| Run | Dataset | Recall@1 | Recall@3 | Recall@5 | MRR | Missed Count |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Best before rescue | original | 4.08% | 34.69% | 89.80% | 0.3401 | 5 |
| Corrected gold before rescue | corrected | 4.08% | 73.47% | 89.80% | 0.3401 | 5 |
| Rescue slot | original | 4.08% | 73.47% | 91.84% | 0.3442 | 4 |
| Rescue slot | corrected | 4.08% | 73.47% | 95.92% | 0.3524 | 2 |

## Verification

- Corrected-gold dataset keeps 49 items and changes only the 3 known shifted gold labels.
- Original dataset Recall@5 improves from 89.80% to 91.84%, so it does not regress from the prior best.
- Corrected-gold Recall@5 improves from 89.80% to 95.92%.
- Prior rank1-4 hits were checked against the rescue-slot original run; regression count is 0.

## Remaining Misses

Original dataset still misses 4 items, including 3 known gold-shifted samples:

- `book-000075`: corrected answer chunk `book-000077` is now retrieved at rank5, but original gold remains `book-000075`.
- `book-000112`: corrected answer chunk still not rescued.
- `book-000007`: corrected answer chunk `book-000009` is now retrieved at rank5, but original gold remains `book-000007`.
- `book-000184`: not rescued by current lexical evidence rule.

Corrected-gold dataset still misses 2 items:

- `book-000113`: the query is vague and BM25 evidence is weak.
- `book-000184`: the rescue rule currently selects a stronger lexical background chunk, not the gold action chunk.
