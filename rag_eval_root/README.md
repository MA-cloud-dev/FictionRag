# RAG Evaluation Trace

This folder keeps representative evaluation milestones for the FictionRag project.

## Preserved Stages

| Directory | Meaning |
| --- | --- |
| `rag_eval_stage_01_single_book_reference` | Single-book baseline milestone. |
| `rag_eval_stage_02_two_book_mvp_reference` | First two-book merged-index MVP milestone. |
| `rag_eval_stage_03_five_book_mvp_reference` | EPUB import and five-book MVP milestone. |
| `rag_eval_ten_book_mvp_20260429_2326` | Ten-book baseline before book routing. |
| `rag_eval_ten_book_book_route3_20260430_1125` | Current best ten-book route result, `route_count=3`, `cap=3`. |

## Current Recommended Retrieval Parameters

```text
book_route_count = 3
book_result_cap = 3
```

The ten-book route result is the current reference result for the active retrieval strategy.
