"""Command-line entry point for the FictionRag MVP."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.chunker import build_chunks
    from src.config import (
        CHUNK_OVERLAP,
        CHUNK_SIZE,
        DEFAULT_BOOK_PATH,
        DEFAULT_INDEX_PATH,
        DEFAULT_TOP_K,
        ConfigError,
        load_embedding_config,
        load_llm_config,
    )
    from src.embeddings import APIError, EmbeddingClient
    from src.evaluator import (
        DEFAULT_EVAL_DIR,
        DEFAULT_SAMPLE_SIZE,
        DEFAULT_SEED,
        run_evaluation,
    )
    from src.index_store import IndexStoreError, load_chunks, save_chunks
    from src.llm import LLMClient
    from src.prompts import build_user_prompt
    from src.retriever import RetrievalResult, retrieve
else:
    from .chunker import build_chunks
    from .config import (
        CHUNK_OVERLAP,
        CHUNK_SIZE,
        DEFAULT_BOOK_PATH,
        DEFAULT_INDEX_PATH,
        DEFAULT_TOP_K,
        ConfigError,
        load_embedding_config,
        load_llm_config,
    )
    from .embeddings import APIError, EmbeddingClient
    from .evaluator import (
        DEFAULT_EVAL_DIR,
        DEFAULT_SAMPLE_SIZE,
        DEFAULT_SEED,
        run_evaluation,
    )
    from .index_store import IndexStoreError, load_chunks, save_chunks
    from .llm import LLMClient
    from .prompts import build_user_prompt
    from .retriever import RetrievalResult, retrieve


def main(argv: list[str] | None = None) -> int:
    if argv is None and len(sys.argv) == 1:
        return run_console_menu()

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "index":
            return run_index(args)
        if args.command == "retrieve":
            return run_retrieve(args)
        if args.command == "ask":
            return run_ask(args)
        if args.command == "eval":
            return run_eval(args)
    except (ConfigError, APIError, IndexStoreError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FictionRag MVP console tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Build local JSONL index")
    index_parser.add_argument("--book", required=True, help="Path to the novel .txt file")
    index_parser.add_argument(
        "--index-path",
        default=str(DEFAULT_INDEX_PATH),
        help="Output JSONL index path",
    )

    retrieve_parser = subparsers.add_parser("retrieve", help="Show retrieval results only")
    retrieve_parser.add_argument("question", help="Question to retrieve context for")
    retrieve_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    retrieve_parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH))

    ask_parser = subparsers.add_parser("ask", help="Retrieve context and ask the LLM")
    ask_parser.add_argument("question", help="Question to answer")
    ask_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    ask_parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH))

    eval_parser = subparsers.add_parser("eval", help="Run quantitative retrieval evaluation")
    eval_parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH))
    eval_parser.add_argument("--output-dir", default=str(DEFAULT_EVAL_DIR))
    eval_parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    eval_parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    eval_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    eval_parser.add_argument(
        "--force-generate",
        action="store_true",
        help="Regenerate dataset.jsonl even if it already exists",
    )

    return parser


def run_index(args: argparse.Namespace) -> int:
    book_path = Path(args.book)
    index_path = Path(args.index_path)
    if not book_path.exists():
        raise FileNotFoundError(f"Novel file does not exist: {book_path}")
    if not book_path.is_file():
        raise ValueError(f"Novel path is not a file: {book_path}")

    text = book_path.read_text(encoding="utf-8")
    if not text:
        raise ValueError(f"Novel file is empty: {book_path}")

    book_name = book_path.stem
    chunks = build_chunks(
        text,
        book_name=book_name,
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP,
    )

    embedding_client = EmbeddingClient(load_embedding_config())
    embeddings = embedding_client.embed_texts([chunk.text for chunk in chunks])
    embedded_chunks = [
        replace(chunk, embedding=embedding)
        for chunk, embedding in zip(chunks, embeddings)
    ]

    save_chunks(embedded_chunks, index_path)
    print(f"Indexed {len(embedded_chunks)} chunks from {book_path}")
    print(f"Index saved to {index_path}")
    return 0


def run_retrieve(args: argparse.Namespace) -> int:
    results = _retrieve_for_question(
        question=args.question,
        index_path=Path(args.index_path),
        top_k=args.top_k,
    )
    print_retrieval_results(results, top_k=args.top_k)
    return 0


def run_ask(args: argparse.Namespace) -> int:
    results = _retrieve_for_question(
        question=args.question,
        index_path=Path(args.index_path),
        top_k=args.top_k,
    )
    user_prompt = build_user_prompt(args.question, results)
    llm_client = LLMClient(load_llm_config())
    answer = llm_client.answer(user_prompt)

    print("Question:")
    print(args.question)
    print()
    print("Retrieved Context:")
    print_retrieval_results(results, top_k=args.top_k, include_header=False)
    print("Answer:")
    print(answer)
    return 0


def run_eval(args: argparse.Namespace) -> int:
    llm_client = LLMClient(load_llm_config())
    embedding_client = EmbeddingClient(load_embedding_config())
    summary = run_evaluation(
        index_path=Path(args.index_path),
        output_dir=Path(args.output_dir),
        sample_size=args.sample_size,
        seed=args.seed,
        top_k=args.top_k,
        force_generate=args.force_generate,
        llm_client=llm_client,
        embedding_client=embedding_client,
    )
    metrics = summary["metrics"]
    recall = metrics["recall"]

    print("RAG evaluation completed.")
    print(f"Dataset reused: {summary['dataset_reused']}")
    print(f"Dataset count: {summary['dataset_count']}")
    print(f"Recall@1: {recall['recall_at_1']:.2%}")
    print(f"Recall@3: {recall['recall_at_3']:.2%}")
    print(f"Recall@5: {recall['recall_at_5']:.2%}")
    print(f"MRR: {metrics['mrr']:.4f}")
    print(f"Summary: {summary['summary_path']}")
    return 0


def run_console_menu() -> int:
    print("FictionRag Console")
    print(f"Default book: {DEFAULT_BOOK_PATH}")
    print(f"Default index: {DEFAULT_INDEX_PATH}")
    print("Type the menu number and press Enter.")

    while True:
        print()
        print("1. Ask question")
        print("2. Show retrieval only")
        print("3. Build or rebuild index")
        print("4. Exit")

        choice = _prompt("Select: ").strip()
        if choice in {"4", "q", "quit", "exit"}:
            print("Bye.")
            return 0
        if choice == "1":
            _interactive_ask()
            continue
        if choice == "2":
            _interactive_retrieve()
            continue
        if choice == "3":
            _interactive_index()
            continue
        print("Unknown option. Please select 1, 2, 3, or 4.")


def _interactive_ask() -> None:
    question = _prompt("Question: ").strip()
    if not question:
        print("Question cannot be empty.")
        return

    args = argparse.Namespace(
        question=question,
        top_k=DEFAULT_TOP_K,
        index_path=str(DEFAULT_INDEX_PATH),
    )
    _run_interactive_action(lambda: run_ask(args))


def _interactive_retrieve() -> None:
    question = _prompt("Question: ").strip()
    if not question:
        print("Question cannot be empty.")
        return

    args = argparse.Namespace(
        question=question,
        top_k=DEFAULT_TOP_K,
        index_path=str(DEFAULT_INDEX_PATH),
    )
    _run_interactive_action(lambda: run_retrieve(args))


def _interactive_index() -> None:
    args = argparse.Namespace(
        book=str(DEFAULT_BOOK_PATH),
        index_path=str(DEFAULT_INDEX_PATH),
    )
    print(f"Building index from: {DEFAULT_BOOK_PATH}")
    _run_interactive_action(lambda: run_index(args))


def _run_interactive_action(action) -> None:
    try:
        action()
    except (ConfigError, APIError, IndexStoreError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)


def _prompt(label: str) -> str:
    try:
        return input(label)
    except EOFError:
        return "4"


def _retrieve_for_question(
    question: str,
    index_path: Path,
    top_k: int,
) -> list[RetrievalResult]:
    chunks = load_chunks(index_path)
    embedding_client = EmbeddingClient(load_embedding_config())
    question_embedding = embedding_client.embed_text(question)
    return retrieve(question_embedding, chunks, top_k=top_k)


def print_retrieval_results(
    results: list[RetrievalResult],
    top_k: int,
    include_header: bool = True,
) -> None:
    if include_header:
        print(f"Top {top_k} retrieval results:")
        print()

    if not results:
        print("No retrieval results.")
        return

    for index, result in enumerate(results, start=1):
        print(f"[{index}] chunk_id={result.chunk_id} score={result.score:.4f}")
        print(result.text)
        print()


if __name__ == "__main__":
    raise SystemExit(main())
