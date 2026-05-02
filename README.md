# FictionRag

FictionRag is a minimal console-based RAG assistant for asking questions about one local fiction `.txt` file. The MVP follows the flow described in `doc/requirement.md` and `doc/spec.md`:

```text
txt novel -> chunking -> embedding -> JSONL index -> retrieval -> LLM answer
```

## Setup

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Configure API environment variables. You can either export them in the shell or create a local `.env` file based on `.env.example`.

```powershell
$env:EMBEDDING_API_KEY="your_embedding_api_key"
$env:EMBEDDING_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:EMBEDDING_MODEL="qwen3-vl-embedding"

$env:LLM_API_KEY="your_llm_api_key"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_MODEL="deepseek-v4-flash"
```

`qwen3-vl-embedding` is configured with the DashScope compatible base URL, and the client automatically calls DashScope's multimodal embedding endpoint required by that model.

## Usage

Put one UTF-8 `.txt` novel file under `data/novels/`, then build the local index:

```powershell
python -m src.main index --book data/novels/book.txt
```

Inspect retrieval results without calling the LLM:

```powershell
python -m src.main retrieve "主角第一次见到某人是什么时候？"
```

Run the full RAG question-answer flow:

```powershell
python -m src.main ask "主角第一次见到某人是什么时候？"
```

Start the minimal Flask API:

```powershell
python -m src.app
```

Open the lightweight chat frontend:

```text
http://127.0.0.1:5000/
```

Ask through the API:

```powershell
curl -X POST http://127.0.0.1:5000/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"主角第一次见到某人是什么时候？\",\"top_k\":5}"
```

You can also start the interactive console menu:

```powershell
python -m src.main
```

The menu supports asking questions, viewing retrieval results only, and rebuilding the index. Rebuilding the index always uses `data/novels/book.txt`; question answering prints the retrieved context before the final answer.

By default, the index is saved to `data/index/chunks.jsonl`, and repeated `index` runs overwrite the old file.

## Evaluation

Run quantitative retrieval evaluation against the existing index:

```powershell
python -m src.main eval
```

The evaluator samples chunks, asks the LLM to generate one question per chunk, then checks whether retrieval returns the source chunk. Outputs are written to `rag_eval/`:

- `dataset.jsonl`: generated questions, gold chunk IDs, and reference answers.
- `results.jsonl`: per-question retrieval results and hit/rank data.
- `summary.md`: Recall@1/3/5, MRR, interpretation, and failed examples.

By default, an existing `rag_eval/dataset.jsonl` is reused for stable comparisons. Add `--force-generate` to create a new dataset:

```powershell
python -m src.main eval --force-generate
```

## Test

```powershell
pytest
```
