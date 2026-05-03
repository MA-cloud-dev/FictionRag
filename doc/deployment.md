# FictionRag Docker Deployment

## 稳定部署方案

当前项目是 Python + Flask 单体服务，前端静态文件由 Flask 同进程托管，默认索引路径是 `data/index/chunks.jsonl`。最稳定的容器化方式是：

- 镜像只包含代码、前端静态资源和 Python 依赖。
- `data/` 通过 volume 或 bind mount 挂载，保存小说原文、实体表和索引文件。
- API key 通过 `.env` 或运行平台的 Secret 注入，不写入镜像。
- 生产入口使用 Gunicorn，不使用 Flask 开发服务器。
- 容器健康检查访问 `/`，避免在索引未生成时因为 `/api/books` 返回 500 而误判容器不健康。

## 构建镜像

```bash
docker build -t fictionrag:latest .
```

## 使用 docker compose 启动

先基于 `.env.example` 创建 `.env`，填入模型服务配置，然后执行：

```bash
docker compose up -d --build
```

Linux 服务器使用 bind mount 时，确保容器用户可以写入数据目录：

```bash
sudo chown -R 10001:10001 data
```

访问：

```text
http://127.0.0.1:5000/
```

## 运行索引构建

容器启动前或启动后都可以构建索引。推荐把小说文本放在宿主机 `data/novels/`，再执行：

```bash
docker compose run --rm fictionrag python -m src.main index \
  --book data/novels/第一卷.txt --book-name 第一卷 \
  --book data/novels/第二卷.txt --book-name 第二卷
```

索引会写入宿主机挂载目录：

```text
data/index/chunks.jsonl
```

## 单容器运行

```bash
docker run -d \
  --name fictionrag \
  --restart unless-stopped \
  --env-file .env \
  -e FICTIONRAG_HOST=0.0.0.0 \
  -p 5000:5000 \
  -v "$(pwd)/data:/app/data" \
  fictionrag:latest
```

Windows PowerShell 可使用：

```powershell
docker run -d `
  --name fictionrag `
  --restart unless-stopped `
  --env-file .env `
  -e FICTIONRAG_HOST=0.0.0.0 `
  -p 5000:5000 `
  -v "${PWD}/data:/app/data" `
  fictionrag:latest
```

## 关键环境变量

必填：

- `EMBEDDING_API_KEY`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_MODEL`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

可选：

- `RERANKER_API_KEY`
- `RERANKER_BASE_URL`
- `RERANKER_MODEL`
- `FICTIONRAG_ENABLE_RERANK`
- `FICTIONRAG_PORT`
- `GUNICORN_WORKERS`
- `GUNICORN_THREADS`
- `GUNICORN_TIMEOUT`

## 生产建议

- 不要把 `.env`、小说原文或索引文件 COPY 进镜像。
- 首次部署后先执行索引构建，再开放问答接口。
- 如果问题请求耗时偏高，优先提高 `GUNICORN_TIMEOUT`，再根据机器 CPU 调整 `GUNICORN_WORKERS`。
- 如果由 Nginx、Caddy 或云负载均衡代理，外层负责 TLS，容器内保持 HTTP 即可。
