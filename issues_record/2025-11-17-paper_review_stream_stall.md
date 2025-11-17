# Issue: /paper_review SSE 流在容器环境下超时

- **日期**: 2025-11-17  
- **环境**: `ICAIS2025-ppreview` 容器，使用 `ICAIS2025-Ideation/test_api_for_arena.py` 进行集成测试  
- **症状**:
  - 客户端在步骤 3 之后长时间无输出，最终触发 `httpx.ReadTimeout`。
  - 服务器日志只显示请求已受理，没有持续的 SSE chunk。

## 根因分析

1. `pdf_parser.parse`、`paper_analyzer.extract_keywords`、`PaperRetriever.hybrid_retrieve` 与创新点分析等阶段是同步阻塞调用（通过 `asyncio.to_thread` 包裹），在大 PDF + reasoning 模型下可持续 60s+。
2. 这些阶段在执行期间没有任何 `yield`，即使 FastAPI 端点使用 `StreamingResponse`，客户端在长时间内收不到数据，从而认为连接已失活。
3. 当调用超出 `httpx` 默认 read timeout（60s/120s）时，客户端主动取消，服务端仍在后台运行导致“卡住”的观感。

## 解决方案

- 扩展 `run_with_heartbeat`：
  - 支持可选 `timeout`，超过总时长自动取消任务并抛出 `asyncio.TimeoutError`。
  - 在任务执行期间每隔 `heartbeat_interval`（默认 15-25s）发送一个空格 chunk，确保 SSE 保持活跃。
- 将耗时阶段统一使用 `run_with_heartbeat` 包裹，并在超时时发送友好的 fallback 信息：
  - PDF 解析 (`pdf_parser.parse`)
  - 关键词提取 (`paper_analyzer.extract_keywords`)
  - 论文检索 (`paper_analyzer.retrieve_related_papers`)
  - 语义相似度/创新点分析
  - 评阅报告生成 (`reviewer.review`)
- 对 `structured_info` 为空的极端情况进行守卫，及时返回错误提示，避免后续阶段引用 `None`。

## 结果验证

1. 重启容器并运行 `python3 ICAIS2025-Ideation/test_api_for_arena.py`。
2. `/paper_review` 端到端完成，全程持续输出步骤提示/心跳，不再触发 ReadTimeout。
3. 终端打印完整评阅报告，`[Stream completed]` 正常结束。

## 影响

- 客户端在长耗时阶段不再误判为无响应。
- 即使上游模型速度波动，服务端仍能保持心跳与超时保护，整体交互体验显著改善。

