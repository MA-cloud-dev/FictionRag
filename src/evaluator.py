"""Quantitative retrieval evaluation for the FictionRag MVP."""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .chunker import Chunk
from .config import PROJECT_ROOT
from .embeddings import EmbeddingClient
from .eval_prompts import EVAL_QUESTION_SYSTEM_PROMPT, build_question_generation_prompt
from .index_store import load_chunks
from .llm import LLMClient
from .retriever import RetrievalResult, retrieve


DEFAULT_EVAL_DIR = PROJECT_ROOT / "rag_eval"
DEFAULT_SAMPLE_SIZE = 50
DEFAULT_SEED = 42
DEFAULT_TOP_KS = (1, 3, 5)


@dataclass(frozen=True)
class EvalItem:
    question: str
    gold_chunk_id: str
    reference_answer: str
    gold_text_preview: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    score: float
    text_preview: str


@dataclass(frozen=True)
class EvalResult:
    question: str
    gold_chunk_id: str
    reference_answer: str
    retrieved_chunks: list[RetrievedChunk]
    gold_rank: int | None
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    reciprocal_rank: float


def run_evaluation(
    index_path: Path,
    output_dir: Path,
    sample_size: int,
    seed: int,
    top_k: int,
    force_generate: bool,
    llm_client: LLMClient,
    embedding_client: EmbeddingClient,
) -> dict[str, Any]:
    if sample_size <= 0:
        raise ValueError("sample_size must be greater than 0")
    if top_k < max(DEFAULT_TOP_KS):
        raise ValueError(f"top_k must be at least {max(DEFAULT_TOP_KS)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "dataset.jsonl"
    results_path = output_dir / "results.jsonl"
    summary_path = output_dir / "summary.md"

    chunks = load_chunks(index_path)
    generation_errors: list[str] = []
    dataset_reused = dataset_path.exists() and not force_generate
    if dataset_reused:
        dataset = load_dataset(dataset_path)
    else:
        dataset, generation_errors = generate_dataset(
            chunks=chunks,
            llm_client=llm_client,
            sample_size=sample_size,
            seed=seed,
        )
        if not dataset:
            raise ValueError("No valid eval items were generated.")
        save_dataset(dataset, dataset_path)

    results = evaluate_dataset(
        dataset=dataset,
        chunks=chunks,
        embedding_client=embedding_client,
        top_k=top_k,
    )
    save_results(results, results_path)

    metrics = compute_metrics(results, DEFAULT_TOP_KS)
    summary_markdown = build_summary_markdown(
        metrics=metrics,
        dataset=dataset,
        results=results,
        generation_errors=generation_errors,
        index_path=index_path,
        output_dir=output_dir,
        sample_size=sample_size,
        seed=seed,
        top_k=top_k,
        dataset_reused=dataset_reused,
        embedding_model=embedding_client.config.model,
        llm_model=llm_client.config.model,
    )
    summary_path.write_text(summary_markdown, encoding="utf-8")

    return {
        "dataset_path": dataset_path,
        "results_path": results_path,
        "summary_path": summary_path,
        "metrics": metrics,
        "dataset_count": len(dataset),
        "dataset_reused": dataset_reused,
    }


def generate_dataset(
    chunks: list[Chunk],
    llm_client: LLMClient,
    sample_size: int,
    seed: int,
) -> tuple[list[EvalItem], list[str]]:
    sampled_chunks = sample_chunks(chunks, sample_size=sample_size, seed=seed)
    items: list[EvalItem] = []
    errors: list[str] = []

    for chunk in sampled_chunks:
        prompt = build_question_generation_prompt(chunk.id, chunk.text)
        try:
            content = llm_client.chat(EVAL_QUESTION_SYSTEM_PROMPT, prompt, temperature=0)
            parsed = parse_json_object(content)
            question = str(parsed["question"]).strip()
            reference_answer = str(parsed["reference_answer"]).strip()
            if not question or not reference_answer:
                raise ValueError("question/reference_answer cannot be empty")
            items.append(
                EvalItem(
                    question=question,
                    gold_chunk_id=chunk.id,
                    reference_answer=reference_answer,
                    gold_text_preview=text_preview(chunk.text),
                )
            )
        except Exception as exc:  # Keep eval generation robust across single bad samples.
            errors.append(f"{chunk.id}: {exc}")

    return items, errors


def sample_chunks(chunks: list[Chunk], sample_size: int, seed: int) -> list[Chunk]:
    if not chunks:
        return []
    count = min(sample_size, len(chunks))
    rng = random.Random(seed)
    return rng.sample(chunks, count)


def parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Generated content must be a JSON object")
    return parsed


def evaluate_dataset(
    dataset: list[EvalItem],
    chunks: list[Chunk],
    embedding_client: EmbeddingClient,
    top_k: int,
) -> list[EvalResult]:
    results: list[EvalResult] = []
    question_embeddings = embedding_client.embed_texts([item.question for item in dataset])
    for item, question_embedding in zip(dataset, question_embeddings):
        retrieved = retrieve(question_embedding, chunks, top_k=top_k)
        gold_rank = find_gold_rank(item.gold_chunk_id, retrieved)
        results.append(
            EvalResult(
                question=item.question,
                gold_chunk_id=item.gold_chunk_id,
                reference_answer=item.reference_answer,
                retrieved_chunks=[
                    RetrievedChunk(
                        chunk_id=result.chunk_id,
                        score=result.score,
                        text_preview=text_preview(result.text),
                    )
                    for result in retrieved
                ],
                gold_rank=gold_rank,
                hit_at_1=is_hit_at_k(gold_rank, 1),
                hit_at_3=is_hit_at_k(gold_rank, 3),
                hit_at_5=is_hit_at_k(gold_rank, 5),
                reciprocal_rank=(1.0 / gold_rank) if gold_rank else 0.0,
            )
        )
    return results


def find_gold_rank(gold_chunk_id: str, retrieved: list[RetrievalResult]) -> int | None:
    for index, result in enumerate(retrieved, start=1):
        if result.chunk_id == gold_chunk_id:
            return index
    return None


def is_hit_at_k(gold_rank: int | None, k: int) -> bool:
    return gold_rank is not None and gold_rank <= k


def compute_metrics(results: list[EvalResult], top_ks: tuple[int, ...]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {
            "sample_count": 0,
            "top1_hit_rate": 0.0,
            "mrr": 0.0,
            "average_gold_rank": None,
            "missed_count": 0,
            "recall": {f"recall_at_{k}": 0.0 for k in top_ks},
        }

    found_ranks = [result.gold_rank for result in results if result.gold_rank is not None]
    recall = {
        f"recall_at_{k}": sum(is_hit_at_k(result.gold_rank, k) for result in results) / total
        for k in top_ks
    }
    return {
        "sample_count": total,
        "top1_hit_rate": recall.get("recall_at_1", 0.0),
        "mrr": sum(result.reciprocal_rank for result in results) / total,
        "average_gold_rank": (sum(found_ranks) / len(found_ranks)) if found_ranks else None,
        "missed_count": total - len(found_ranks),
        "recall": recall,
    }


def save_dataset(dataset: list[EvalItem], path: Path) -> None:
    save_jsonl([asdict(item) for item in dataset], path)


def load_dataset(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []
    for raw in load_jsonl(path):
        items.append(
            EvalItem(
                question=str(raw["question"]),
                gold_chunk_id=str(raw["gold_chunk_id"]),
                reference_answer=str(raw["reference_answer"]),
                gold_text_preview=str(raw["gold_text_preview"]),
            )
        )
    if not items:
        raise ValueError(f"Eval dataset is empty: {path}")
    return items


def save_results(results: list[EvalResult], path: Path) -> None:
    save_jsonl([asdict(result) for result in results], path)


def save_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def build_summary_markdown(
    metrics: dict[str, Any],
    dataset: list[EvalItem],
    results: list[EvalResult],
    generation_errors: list[str],
    index_path: Path,
    output_dir: Path,
    sample_size: int,
    seed: int,
    top_k: int,
    dataset_reused: bool,
    embedding_model: str,
    llm_model: str,
) -> str:
    recall = metrics["recall"]
    average_rank = metrics["average_gold_rank"]
    average_rank_text = f"{average_rank:.2f}" if average_rank is not None else "N/A"
    misses = [result for result in results if result.gold_rank is None][:5]

    lines = [
        "# RAG Retrieval Evaluation Summary",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Index: `{index_path}`",
        f"- Output dir: `{output_dir}`",
        f"- Dataset reused: `{dataset_reused}`",
        f"- Requested sample size: `{sample_size}`",
        f"- Effective sample count: `{len(dataset)}`",
        f"- Seed: `{seed}`",
        f"- Retrieval top_k: `{top_k}`",
        f"- Embedding model: `{embedding_model}`",
        f"- LLM model for question generation: `{llm_model}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Meaning |",
        "| --- | ---: | --- |",
        f"| Recall@1 | {recall['recall_at_1']:.2%} | gold chunk 出现在第 1 个召回结果中的比例。 |",
        f"| Recall@3 | {recall['recall_at_3']:.2%} | gold chunk 出现在前 3 个召回结果中的比例。 |",
        f"| Recall@5 | {recall['recall_at_5']:.2%} | gold chunk 出现在前 5 个召回结果中的比例。 |",
        f"| MRR | {metrics['mrr']:.4f} | gold chunk 排名越靠前越接近 1。未命中按 0 计算。 |",
        f"| Top1 Hit Rate | {metrics['top1_hit_rate']:.2%} | 与 Recall@1 相同，是最严格的直接命中能力。 |",
        f"| Average Gold Rank | {average_rank_text} | 只在命中的样本中计算 gold chunk 的平均排名。 |",
        f"| Missed Count | {metrics['missed_count']} | gold chunk 未出现在 Top {top_k} 的样本数量。 |",
        "",
        "## Interpretation",
        "",
        "- Recall@1 高说明问题向量和原文 chunk 的语义匹配很直接，首条结果通常可用于回答。",
        "- Recall@5 高但 Recall@1 低说明相关片段能被找回，但排序还可以优化，后续可考虑 rerank。",
        "- MRR 对排名敏感，适合观察排序质量；它比 Recall@5 更能反映 gold chunk 是否靠前。",
        "- 未命中样例通常用于分析 chunk 切分、问题生成质量、embedding 模型或 top_k 设置是否需要调整。",
        "",
        "## Failed Examples",
        "",
    ]

    if not misses:
        lines.append("No failed examples. All gold chunks were found within the evaluated Top K.")
    else:
        for index, result in enumerate(misses, start=1):
            top_chunks = ", ".join(chunk.chunk_id for chunk in result.retrieved_chunks[:5])
            lines.extend(
                [
                    f"### {index}. {result.question}",
                    "",
                    f"- Gold chunk: `{result.gold_chunk_id}`",
                    f"- Retrieved top chunks: `{top_chunks}`",
                    f"- Reference answer: {result.reference_answer}",
                    "",
                ]
            )

    if generation_errors:
        lines.extend(
            [
                "## Generation Errors",
                "",
                f"{len(generation_errors)} chunk(s) failed during question generation.",
                "",
            ]
        )
        for error in generation_errors[:10]:
            lines.append(f"- {error}")

    return "\n".join(lines) + "\n"


def text_preview(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit] + "..."
