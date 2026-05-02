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
        CHUNK_MAX_SIZE,
        CHUNK_SIZE,
        DEFAULT_BOOK_PATH,
        DEFAULT_INDEX_PATH,
        DEFAULT_TOP_K,
        ConfigError,
        load_embedding_config,
        load_llm_config,
        load_reranker_config,
    )
    from src.embeddings import APIError, EmbeddingClient
    from src.evaluator import (
        DEFAULT_EVAL_DIR,
        DEFAULT_RERANK_BM25_TOP_N,
        DEFAULT_RERANK_CANDIDATE_TOP_N,
        DEFAULT_RERANK_VECTOR_TOP_N,
        DEFAULT_SAMPLE_SIZE,
        DEFAULT_SEED,
        run_evaluation,
    )
    from src.epub_importer import EpubImportError, import_epub_to_text
    from src.index_store import IndexStoreError, save_chunks
    from src.llm import LLMClient
    from src.retriever import (
        DEFAULT_BOOK_RESULT_CAP,
        DEFAULT_BOOK_ROUTE_COUNT,
        RetrievalResult,
    )
    from src.rag_service import answer_question, retrieve_contexts
    from src.reranker import RerankerClient
else:
    from .chunker import build_chunks
    from .config import (
        CHUNK_OVERLAP,
        CHUNK_MAX_SIZE,
        CHUNK_SIZE,
        DEFAULT_BOOK_PATH,
        DEFAULT_INDEX_PATH,
        DEFAULT_TOP_K,
        ConfigError,
        load_embedding_config,
        load_llm_config,
        load_reranker_config,
    )
    from .embeddings import APIError, EmbeddingClient
    from .evaluator import (
        DEFAULT_EVAL_DIR,
        DEFAULT_RERANK_BM25_TOP_N,
        DEFAULT_RERANK_CANDIDATE_TOP_N,
        DEFAULT_RERANK_VECTOR_TOP_N,
        DEFAULT_SAMPLE_SIZE,
        DEFAULT_SEED,
        run_evaluation,
    )
    from .epub_importer import EpubImportError, import_epub_to_text
    from .index_store import IndexStoreError, save_chunks
    from .llm import LLMClient
    from .retriever import (
        DEFAULT_BOOK_RESULT_CAP,
        DEFAULT_BOOK_ROUTE_COUNT,
        RetrievalResult,
    )
    from .rag_service import answer_question, retrieve_contexts
    from .reranker import RerankerClient


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
        if args.command == "import-epub":
            return run_import_epub(args)
    except (ConfigError, APIError, EpubImportError, IndexStoreError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FictionRag MVP console tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Build local JSONL index")
    index_parser.add_argument(
        "--book",
        action="append",
        required=True,
        help="Path to a novel .txt file. Repeat to build a multi-book index.",
    )
    index_parser.add_argument(
        "--book-name",
        action="append",
        help="Book name for the matching --book. Repeat in the same order as --book.",
    )
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
    eval_parser.add_argument(
        "--sample-per-book",
        action="append",
        default=[],
        metavar="BOOK=COUNT",
        help="Stratified eval sampling count per book_name. Repeat for multiple books.",
    )
    eval_parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    eval_parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    eval_parser.add_argument(
        "--book-route-count",
        type=int,
        default=DEFAULT_BOOK_ROUTE_COUNT,
        help="Route retrieval through the top N candidate books before scene expansion.",
    )
    eval_parser.add_argument(
        "--book-result-cap",
        type=int,
        default=DEFAULT_BOOK_RESULT_CAP,
        help="Maximum number of final Top K chunks allowed from one routed book.",
    )
    eval_parser.add_argument(
        "--rerank",
        action="store_true",
        help="Rerank retrieval candidates with the configured reranker model.",
    )
    eval_parser.add_argument(
        "--rerank-candidate-top-n",
        type=int,
        default=DEFAULT_RERANK_CANDIDATE_TOP_N,
        help="Number of pre-rerank candidates to score.",
    )
    eval_parser.add_argument(
        "--rerank-vector-top-n",
        type=int,
        default=DEFAULT_RERANK_VECTOR_TOP_N,
        help="Dense retrieval top-N used when building rerank candidates.",
    )
    eval_parser.add_argument(
        "--rerank-bm25-top-n",
        type=int,
        default=DEFAULT_RERANK_BM25_TOP_N,
        help="BM25 retrieval top-N used when building rerank candidates.",
    )
    eval_parser.add_argument(
        "--force-generate",
        action="store_true",
        help="Regenerate dataset.jsonl even if it already exists",
    )

    import_parser = subparsers.add_parser("import-epub", help="Clean an EPUB into plain text")
    import_parser.add_argument("--epub", required=True, help="Path to the source EPUB file")
    import_parser.add_argument("--output", required=True, help="Output .txt path")
    import_parser.add_argument(
        "--include-prefix",
        help="Only import documents whose first paragraphs start with this prefix.",
    )

    return parser


def run_index(args: argparse.Namespace) -> int:
    index_path = Path(args.index_path)
    book_paths = [Path(book) for book in args.book]
    book_names = _resolve_book_names(book_paths, getattr(args, "book_name", None))

    chunks = []
    book_chunk_counts: list[tuple[Path, str, int]] = []
    for book_path, book_name in zip(book_paths, book_names):
        if not book_path.exists():
            raise FileNotFoundError(f"Novel file does not exist: {book_path}")
        if not book_path.is_file():
            raise ValueError(f"Novel path is not a file: {book_path}")

        text = book_path.read_text(encoding="utf-8")
        if not text:
            raise ValueError(f"Novel file is empty: {book_path}")

        book_chunks = build_chunks(
            text,
            book_name=book_name,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
            max_chunk_size=CHUNK_MAX_SIZE,
        )
        chunks.extend(book_chunks)
        book_chunk_counts.append((book_path, book_name, len(book_chunks)))

    embedding_client = EmbeddingClient(load_embedding_config())
    embeddings = embedding_client.embed_texts([chunk.text for chunk in chunks])
    embedded_chunks = [
        replace(chunk, embedding=embedding)
        for chunk, embedding in zip(chunks, embeddings)
    ]

    save_chunks(embedded_chunks, index_path)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(book_chunk_counts)} book(s)")
    for book_path, book_name, count in book_chunk_counts:
        print(f"- {book_name}: {count} chunks from {book_path}")
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
    rag_answer = answer_question(
        question=args.question,
        top_k=args.top_k,
        index_path=Path(args.index_path),
    )
    results = rag_answer.contexts

    print("Question:")
    print(args.question)
    print()
    print("Retrieved Context:")
    print_retrieval_results(results, top_k=args.top_k, include_header=False)
    print("Answer:")
    print(rag_answer.answer)
    return 0


def run_eval(args: argparse.Namespace) -> int:
    llm_client = LLMClient(load_llm_config())
    embedding_client = EmbeddingClient(load_embedding_config())
    reranker_client = RerankerClient(load_reranker_config()) if args.rerank else None
    samples_per_book = _parse_sample_per_book(args.sample_per_book)
    summary = run_evaluation(
        index_path=Path(args.index_path),
        output_dir=Path(args.output_dir),
        sample_size=args.sample_size,
        seed=args.seed,
        top_k=args.top_k,
        force_generate=args.force_generate,
        llm_client=llm_client,
        embedding_client=embedding_client,
        samples_per_book=samples_per_book,
        book_route_count=args.book_route_count,
        book_result_cap=args.book_result_cap,
        rerank_enabled=args.rerank,
        reranker_client=reranker_client,
        rerank_candidate_top_n=args.rerank_candidate_top_n,
        rerank_vector_top_n=args.rerank_vector_top_n,
        rerank_bm25_top_n=args.rerank_bm25_top_n,
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
    print(f"Book route count: {args.book_route_count}")
    print(f"Book result cap: {args.book_result_cap}")
    print(f"Rerank enabled: {args.rerank}")
    if args.rerank:
        print(f"Rerank candidate top_n: {args.rerank_candidate_top_n}")
        print(f"Rerank vector top_n: {args.rerank_vector_top_n}")
        print(f"Rerank BM25 top_n: {args.rerank_bm25_top_n}")
    print(f"Summary: {summary['summary_path']}")
    return 0


def run_import_epub(args: argparse.Namespace) -> int:
    paragraph_count, character_count = import_epub_to_text(
        epub_path=Path(args.epub),
        output_path=Path(args.output),
        include_prefix=args.include_prefix,
    )
    print(f"Imported EPUB to {args.output}")
    print(f"Paragraphs: {paragraph_count}")
    print(f"Characters: {character_count}")
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
        book=[str(DEFAULT_BOOK_PATH)],
        book_name=None,
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
    return retrieve_contexts(question=question, index_path=index_path, top_k=top_k)


def _resolve_book_names(book_paths: list[Path], book_names: list[str] | None) -> list[str]:
    if not book_names:
        return [book_path.stem for book_path in book_paths]
    if len(book_names) != len(book_paths):
        raise ValueError("--book-name must be provided once for each --book")
    resolved = [book_name.strip() for book_name in book_names]
    if any(not book_name for book_name in resolved):
        raise ValueError("--book-name cannot be empty")
    if len(set(resolved)) != len(resolved):
        raise ValueError("--book-name values must be unique within one index")
    return resolved


def _parse_sample_per_book(values: list[str]) -> dict[str, int] | None:
    if not values:
        return None

    samples_per_book: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--sample-per-book must use BOOK=COUNT format")
        book_name, raw_count = value.split("=", 1)
        book_name = book_name.strip()
        if not book_name:
            raise ValueError("--sample-per-book book name cannot be empty")
        try:
            count = int(raw_count)
        except ValueError as exc:
            raise ValueError("--sample-per-book count must be an integer") from exc
        if count <= 0:
            raise ValueError("--sample-per-book count must be greater than 0")
        samples_per_book[book_name] = count
    return samples_per_book


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
        print(
            f"[{index}] book={result.chunk.book_name} "
            f"chunk_id={result.chunk_id} score={result.score:.4f}"
        )
        print(result.text)
        print()


if __name__ == "__main__":
    raise SystemExit(main())
