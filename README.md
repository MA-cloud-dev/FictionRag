# FictionRag

FictionRag 是一个面向本地小说原文的多书 RAG 问答助手。当前 MVP 链路与 `doc/requirement.md`、`doc/spec.md` 保持一致：

```text
txt/EPUB -> 清洗 -> 结构化切片 -> embedding -> JSONL 索引 -> hybrid 多书召回 -> LLM 回答
```

当前实现包含：

- 多本 `.txt` 小说建索引，默认以文件名作为 `book_name`。
- EPUB 清洗导入。
- 章节、场景、自然段感知切片。
- dense 向量召回 + BM25 sparse 召回。
- 在线问答和离线评测都支持 qwen3-rerank 候选重排。
- 多书路由、scene 上下文扩展、单书结果上限和第 5 位 rescue slot。
- 控制台命令、Flask API 和轻量聊天前端。

## Setup

创建并激活虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
pip install -r requirements.txt
```

配置 API 环境变量。可以在 shell 中导出，也可以基于 `.env.example` 创建本地 `.env`：

```powershell
$env:EMBEDDING_API_KEY="your_embedding_api_key"
$env:EMBEDDING_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:EMBEDDING_MODEL="qwen3-vl-embedding"

$env:LLM_API_KEY="your_llm_api_key"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_MODEL="deepseek-v4-flash"
```

`qwen3-vl-embedding` 会自动走 DashScope multimodal embedding endpoint。rerank 评测默认复用 embedding key，并可通过 `RERANKER_API_KEY`、`RERANKER_BASE_URL`、`RERANKER_MODEL` 覆盖。

## Usage

把 UTF-8 `.txt` 小说放到 `data/novels/`，然后构建索引：

```powershell
python -m src.main index `
  --book data/novels/第一卷.txt --book-name 第一卷 `
  --book data/novels/第二卷.txt --book-name 第二卷
```

如果不传 `--book-name`，系统使用文件名 stem 作为书名。索引默认写入 `data/index/chunks.jsonl`，重复执行会覆盖旧索引。

导入 EPUB：

```powershell
python -m src.main import-epub --epub input.epub --output data/novels/第五卷.txt
```

只查看召回结果，不调用 LLM：

```powershell
python -m src.main retrieve "主角第一次见到某人是什么时候？"
```

执行完整问答：

```powershell
python -m src.main ask "主角第一次见到某人是什么时候？"
```

启动 Flask API 和前端：

```powershell
python -m src.app
```

打开：

```text
http://127.0.0.1:5000/
```

通过 API 提问：

```powershell
curl -X POST http://127.0.0.1:5000/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"主角第一次见到某人是什么时候？\",\"top_k\":5}"
```

也可以启动交互式控制台菜单：

```powershell
python -m src.main
```

注意：交互式菜单中的“重建索引”仍使用 `data/novels/book.txt` 这个旧默认路径；多书建索引建议使用显式 `index --book ...` 命令。

## Evaluation

运行离线召回评测：

```powershell
python -m src.main eval
```

评测会抽样 chunk，让 LLM 为每个 chunk 生成问题，再检查召回是否返回 gold chunk。默认输出到 `rag_eval/`：

- `dataset.jsonl`：生成的问题、gold chunk ID 和参考答案。
- `question_embeddings.jsonl`：问题向量缓存。
- `results.jsonl`：逐问题召回结果和命中信息。
- `summary.md`：Recall@1/3/5、MRR、分书指标和失败样例分析。

默认复用已有 `dataset.jsonl`。需要重新生成数据集时使用：

```powershell
python -m src.main eval --force-generate
```

启用 qwen3-rerank 离线评测：

```powershell
python -m src.main eval --rerank `
  --book-route-count 5 `
  --book-result-cap 3 `
  --rerank-vector-top-n 100 `
  --rerank-bm25-top-n 100 `
  --rerank-candidate-top-n 30
```

在线 `retrieve`、`ask` 和 Web 问答默认启用 rerank：先构建 Top 30 候选池，再调用 qwen3-rerank 重排并返回 Top K。需要临时关闭时设置：

```powershell
$env:FICTIONRAG_ENABLE_RERANK="false"
```

`eval --rerank` 仍可用于离线评测 rerank 效果。

## Test

```powershell
pytest
```
