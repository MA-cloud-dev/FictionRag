# Chunk Optimization Evaluation Comparison

## 数据集说明

- 旧数据集：`rag_eval\dataset.jsonl`，49 条。
- 新数据集：`rag_eval_chunk_optimized\dataset.jsonl`，49 条。
- 新数据集复用旧数据集的问题和参考答案，但根据新切分后的 `gold_text_preview` 文本锚点重新映射 `gold_chunk_id`。
- 映射结果：精确文本锚点 47 条，模糊兜底 2 条，gold chunk id 变化 48 条。
- 旧 `rag_eval` 文件未覆盖；本次结果写入 `rag_eval_chunk_optimized`。

## 指标对比

| Metric | 旧固定切分 | 新结构切分 | 变化 |
| --- | ---: | ---: | ---: |
| Dataset Count | 49 | 49 | +0 |
| Recall@1 | 65.31% | 42.86% | -22.45% |
| Recall@3 | 89.80% | 67.35% | -22.45% |
| Recall@5 | 91.84% | 67.35% | -24.49% |
| MRR | 0.7738 | 0.5442 | -0.2296 |
| Missed Count | 4 | 16 | +12 |

## 命中变化

- 两边都命中 Top5：33 条。
- 旧切分命中、新切分未命中：12 条。
- 新切分命中、旧切分未命中：0 条。
- 两边都未命中：4 条。

## 观察

- 新结构切分的 chunk 语义边界更干净，但本轮只改了切分，没有加入同 scene 邻近扩展或 rerank。
- 新 chunk 数量从旧固定窗口的隐含编号体系变化为 187 条结构 chunk，旧问题虽然复用，但 gold id 已整体迁移，所以指标主要衡量“相同问题在新索引下能否找回新 gold chunk”。
- Recall@5 下降说明仅靠单条向量相似度时，新 chunk 的语义更集中后，部分问题会召回到相邻或同章节相关 chunk，但没有命中精确 gold chunk。下一步应优先验证同 scene 邻近扩展。

## 新切分未命中样例

### 1. 在魔大陆时，是谁发现小偷的痕迹并追上去教训了对方？

- Gold chunk: `book-000079`
- Retrieved top chunks: `book-000001, book-000030, book-000045, book-000051, book-000052`
- Reference answer: 瑞杰路德

### 2. 鲁迪乌斯在船舱中借口去做什么？

- Gold chunk: `book-000073`
- Retrieved top chunks: `book-000074, book-000098, book-000048, book-000101, book-000068`
- Reference answer: 去厕所

### 3. 为什么斯佩路德族的搭船费用特别贵？

- Gold chunk: `book-000009`
- Retrieved top chunks: `book-000011, book-000013, book-000122, book-000014, book-000004`
- Reference answer: 官员推测是防恐对策，为了防止有人把斯佩路德族当成奴隶送到米里斯大陆作乱闹事。

### 4. 魔界大帝奇希莉卡·奇希里斯最让人畏惧的能力是什么？

- Gold chunk: `book-000031`
- Retrieved top chunks: `book-000032, book-000023, book-000024, book-000028, book-000022`
- Reference answer: 她可以把他人的眼睛变成魔眼。

### 5. 在赞特港，鲁迪乌斯他们将魔大陆的货币兑换后，得到了哪些米里斯货币？每种各多少枚？

- Gold chunk: `book-000075`
- Retrieved top chunks: `book-000006, book-000077, book-000013, book-000076, book-000014`
- Reference answer: 米里斯银币三枚、米里斯大铜币七枚、米里斯铜币两枚。

### 6. 被菲兹打倒的刺客在阿斯拉王国被称为什么？

- Gold chunk: `book-000185`
- Retrieved top chunks: `book-000186, book-000168, book-000187, book-000183, book-000184`
- Reference answer: 夜目之乌鸦

### 7. 在片段中，艾莉丝称呼基列奴为什么？

- Gold chunk: `book-000133`
- Retrieved top chunks: `book-000134, book-000135, book-000140, book-000008, book-000158`
- Reference answer: 师父

### 8. 在小说片段中，主角和基斯对话时，注意到了哪些异常现象？

- Gold chunk: `book-000112`
- Retrieved top chunks: `book-000113, book-000153, book-000108, book-000159, book-000114`
- Reference answer: 看守小姐没来、外面有点吵、有点热、空气里有呛人的烟。

### 9. 菲兹在什么时候拜访了爱丽儿？

- Gold chunk: `book-000180`
- Retrieved top chunks: `book-000181, book-000177, book-000168, book-000178, book-000182`
- Reference answer: 深夜（即将就寝的时分）

### 10. 艾莉丝为什么突然宣布要回去并离开？

- Gold chunk: `book-000036`
- Retrieved top chunks: `book-000149, book-000148, book-000075, book-000040, book-000003`
- Reference answer: 因为她丧失了自信，因为对手突然变强。

