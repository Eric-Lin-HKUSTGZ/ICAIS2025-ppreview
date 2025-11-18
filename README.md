# ICAIS2025-PaperReview

论文评阅智能体系统 - 基于多阶段智能分析流程的创新论文评阅系统


## 文件结构

```
ICAIS2025-ppreview/
├── api_service.py         # FastAPI主应用 (V1版本)
├── api_service_v2.py      # FastAPI主应用 (V2版本)
├── config.py              # 配置管理
├── llm_client.py          # LLM客户端
├── embedding_client.py    # Embedding客户端
├── pdf_parser.py          # PDF解析模块
├── paper_analyzer.py      # 论文分析模块
├── reviewer.py            # 评阅生成模块 (V1版本)
├── reviewer_v2.py         # 评阅生成模块 (V2版本)
├── retriever.py           # 论文检索模块
├── prompt_template.py     # Prompt模板 (V1版本)
├── prompt_template_v2.py  # Prompt模板 (V2版本)
├── requirements.txt       # 依赖包
├── Dockerfile            # Docker配置
├── docker-compose.yml    # Docker Compose配置
└── README.md             # 项目说明
```

## 系统概述

本系统是一个创新的论文评阅智能体，提供两个版本的实现方案：

### V1版本（完整版）
通过多阶段智能分析流程，结合PDF结构化解析、相关论文检索对比、语义相似度分析和推理模型深度评估，生成高质量的论文评阅报告。

**核心特点**：
1. **多阶段智能分析流程**：不是简单地将PDF文本输入LLM，而是采用分阶段、多维度分析
2. **PDF结构化解析**：智能提取论文的关键结构化信息
3. **相关论文检索与对比分析**：利用Semantic Scholar API检索相关论文进行深度对比
4. **语义相似度分析**：使用embedding识别创新点和相似工作
5. **推理模型深度评估**：使用deepseek-reasoner进行多轮深度推理分析

**系统架构（V1）**：
```
PDF输入 → 结构化解析 → 关键信息提取 → 相关论文检索 → 语义对比分析 → 多维度评估 → 生成评阅报告
```

### V2版本（简化版，推荐）
基于大模型能力的纯LLM方案，不涉及外部文件检索，通过高质量的prompt设计确保输出准确无误的评阅结果。

**核心特点**：
1. **纯LLM方案**：完全基于大模型能力，不依赖外部论文检索
2. **高质量Prompt设计**：精心设计的prompt模板，确保输出准确、深入、有证据支撑
3. **简化流程**：4步流程，更快速、更稳定
4. **证据支撑**：严格要求引用具体章节、图表、数据，确保评阅的学术严谨性
5. **深度分析**：每个维度都有详细的子要求，确保分析的深度和全面性

**系统架构（V2）**：
```
PDF输入 → 结构化解析 → 创新点分析 → 多维度评估 → 生成评阅报告
```

**V2版本优势**：
- ✅ 不依赖外部API（Semantic Scholar、Embedding），更稳定可靠
- ✅ 流程更简洁，处理速度更快
- ✅ Prompt质量更高，评阅结果更准确、更深入
- ✅ 严格要求引用具体证据，学术严谨性更强
- ✅ 更适合生产环境部署

**推荐使用V2版本**，除非需要与外部论文进行对比分析。

## API接口

### V1版本端点

```
POST http://<agent_service_host>:3000/paper_review
```

### V2版本端点（推荐）

```
POST http://<agent_service_host>:3000/paper_review
```

**注意**：V1和V2使用相同的端点路径，但需要运行对应的服务文件：
- V1版本：运行 `api_service.py`
- V2版本：运行 `api_service_v2.py`

### 请求格式

```json
{
  "query": "Please provide a brief review of this paper",
  "pdf_content": "base64_encoded_pdf_string"
}
```

### 响应格式

SSE流式输出，每个事件包含`type`和`message`字段：

- `type`: 事件类型（start, step, step_result, section, final, error, warning, info）
- `message`: Markdown格式的消息内容

### 输出结构

```markdown
# Summary
[论文摘要和核心贡献]

# Strengths
[论文优点]

# Weaknesses / Concerns
[论文不足]

# Questions for Authors
[向作者的问题]

# Score
- Overall: X/10
- Novelty: X/10
- Technical Quality: X/10
- Clarity: X/10
- Confidence: X/5
```

## 环境配置

### 必需的环境变量

```bash
# LLM服务配置
SCI_MODEL_BASE_URL=https://api.example.com/v1
SCI_MODEL_API_KEY=your_api_key
SCI_LLM_MODEL=deepseek-ai/DeepSeek-V3
SCI_LLM_REASONING_MODEL=deepseek-ai/DeepSeek-Reasoner

# Embedding配置
SCI_EMBEDDING_MODEL=text-embedding-v4
```

### 可选的环境变量

```bash
# 超时配置（秒）
PDF_PARSE_TIMEOUT=120
KEY_EXTRACTION_TIMEOUT=60
RETRIEVAL_TIMEOUT=180
SEMANTIC_ANALYSIS_TIMEOUT=120
EVALUATION_TIMEOUT=480
REPORT_GENERATION_TIMEOUT=240
REVIEW_TIMEOUT=1200  # 总超时20分钟

# 论文检索配置
MAX_PAPERS_PER_QUERY=5
MAX_TOTAL_PAPERS=10
SEMANTIC_SCHOLAR_TIMEOUT=30
SEMANTIC_SCHOLAR_MAX_RETRIES=10
```

## 安装与运行

### 本地运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 配置环境变量（创建`.env`文件或设置系统环境变量）

3. 运行服务：

**V1版本**：
```bash
python api_service.py
```

**V2版本（推荐）**：
```bash
python api_service_v2.py
```

服务将在 `http://localhost:3000` 启动

### Docker运行

1. 构建镜像：

```bash
docker build -t paper-review .
```

2. 运行容器：

```bash
docker run -p 3000:3000 --env-file .env paper-review
```

## 容器化部署

系统支持使用 Docker 和 Docker Compose 进行容器化部署。

### 前置要求

1. **Docker 和 Docker Compose**：确保已安装并运行
   - 如果使用 colima，确保 colima 已启动：`colima start`
   - 如果使用 Docker Desktop，确保 Docker Desktop 正在运行

2. **基础镜像**：已通过 colima 拉取华为云镜像
   ```bash
   docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim-bookworm
   ```

3. **创建标签**：通过docker tag将华为云 SWR 的镜像重新打标签为 Docker Hub 官方格式
   ```bash
   docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim-bookworm python:3.12-slim-bookworm
   ```

### 部署步骤

#### 1. 配置环境变量

确保已创建 `.env` 文件并配置了必要的环境变量（参考上方"环境配置"章节）。

#### 2. 构建 Docker 镜像

```bash
docker-compose build
```

**说明**：
- Dockerfile 已配置使用华为云镜像：`python:3.12-slim-bookworm`
- 构建过程会自动安装 Python 依赖（使用清华镜像源加速）

#### 3. 启动服务

```bash
docker-compose up -d
```

**说明**：
- `-d` 参数表示后台运行
- 服务将在端口 3000 上启动（可通过 `HOST_PORT` 环境变量修改）

#### 4. 查看服务状态

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看最近 100 行日志
docker-compose logs --tail=100
```

#### 5. 验证服务

**健康检查**：
```bash
curl http://localhost:3000/health
```

预期响应：
```json
{
  "status": "ok",
  "service": "ICAIS2025-PaperReview API"
}
```

**查看 API 文档**：
访问：http://localhost:3000/docs

**测试 API 端点**：
```bash
curl -X POST http://localhost:3000/paper_review \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Please review this paper",
    "pdf_content": "base64_encoded_pdf_content"
  }' \
  --no-buffer
```

### 常用操作

#### 停止服务
```bash
docker-compose down
```

#### 重启服务
```bash
docker-compose restart
```

#### 重新构建并启动
```bash
docker-compose up -d --build
```

#### 查看实时日志
```bash
docker-compose logs -f app
```

#### 进入容器
```bash
docker-compose exec app /bin/bash
```

#### 清理资源
```bash
# 停止并删除容器
docker-compose down

# 停止并删除容器、网络、卷
docker-compose down -v

# 删除镜像（谨慎使用）
docker rmi icais2025-ppreview:latest
```

### 容器配置说明

#### 端口配置

默认端口映射：`3000:3000`（主机端口:容器端口）

可通过环境变量修改：
```bash
# 在 .env 文件中设置
HOST_PORT=8080
```

或在 `docker-compose.yml` 中直接修改：
```yaml
ports:
  - "8080:3000"  # 主机端口:容器端口
```

#### 环境变量

所有配置通过 `.env` 文件管理，支持的环境变量请参考上方"环境配置"章节。

**重要环境变量**：
- `SCI_MODEL_BASE_URL`：LLM API 端点（必需）
- `SCI_MODEL_API_KEY`：LLM API 密钥（必需）
- `SCI_LLM_MODEL`：LLM 模型名称
- `SCI_LLM_REASONING_MODEL`：推理模型名称
- `SCI_EMBEDDING_BASE_URL`：Embedding API 端点
- `SCI_EMBEDDING_API_KEY`：Embedding API 密钥
- `SCI_EMBEDDING_MODEL`：Embedding 模型名称
- `HOST_PORT`：主机端口（默认：3000）

#### 资源限制

如需限制容器资源使用，可在 `docker-compose.yml` 中添加：

```yaml
services:
  app:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 故障排除

#### 常见问题

1. **端口已被占用**
   - 错误：`bind: address already in use`
   - 解决：修改 `HOST_PORT` 环境变量或停止占用端口的服务

2. **容器无法启动**
   - 检查日志：`docker-compose logs app`
   - 检查环境变量配置是否正确
   - 确认 `.env` 文件存在且格式正确

3. **依赖安装失败**
   - 检查网络连接
   - 确认 Dockerfile 中的镜像源配置正确
   - 尝试手动构建：`docker build -t icais2025-ppreview:latest .`

4. **服务响应超时**
   - 检查容器资源使用：`docker stats`
   - 增加超时配置（在 `.env` 文件中）
   - 检查 LLM 和 Embedding API 的连接状态

### 更新服务

当代码更新后，需要重新构建并启动服务：

```bash
# 停止当前服务
docker-compose down

# 重新构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

或使用一条命令：
```bash
docker-compose up -d --build
```

### 生产环境建议

1. **使用反向代理**：建议使用 Nginx 或 Traefik 作为反向代理
2. **配置 HTTPS**：使用 SSL/TLS 证书保护 API 端点
3. **监控和日志**：配置日志收集和监控系统
4. **资源限制**：根据实际负载设置合理的资源限制
5. **健康检查**：配置容器健康检查，自动重启异常容器
6. **备份配置**：定期备份 `.env` 配置文件

## 系统流程

### V1版本流程（6阶段）

#### 阶段1: PDF智能解析与结构化提取

- 解码Base64编码的PDF
- 提取PDF文本内容
- 使用LLM进行结构化解析，提取：
  - 标题、作者、摘要、关键词
  - 引言、方法、实验、结果、结论
  - 论文类型、核心贡献、技术路线

#### 阶段2: 关键信息提取与查询构建

- 提取3-5个核心关键词
- 构建用于Semantic Scholar检索的查询字符串
- 识别研究领域和主题

#### 阶段3: 相关论文检索与筛选

- 使用Semantic Scholar API进行多维度检索：
  - 基于关键词的最新论文
  - 基于关键词的高引用论文
  - 基于标题和摘要的相关论文
- 使用embedding计算语义相似度
- 筛选出最相关的5-10篇论文

#### 阶段4: 语义相似度分析与创新点识别

- 计算待评论文与相关论文的语义相似度
- 使用LLM分析论文的创新点和技术贡献
- 识别论文与现有工作的差异和优势
- 评估论文的原创性

#### 阶段5: 多维度深度评估

使用推理模型（deepseek-reasoner）进行多轮深度分析：

- **技术质量评估**：方法合理性、实验设计、结果可信度
- **新颖性评估**：创新点、与现有工作的差异
- **清晰度评估**：写作质量、逻辑清晰度、可读性
- **完整性评估**：内容完整性、实验充分性

#### 阶段6: 生成评阅报告

使用推理模型生成结构化的评阅报告，包含Summary、Strengths、Weaknesses/Concerns、Questions for Authors和Score等部分。

---

### V2版本流程（4阶段，推荐）

#### 步骤1: PDF解析与结构化提取

- 解码Base64编码的PDF
- 提取PDF文本内容
- 使用LLM进行结构化解析，提取：
  - 标题、作者、摘要、关键词
  - 引言、方法、实验、结果、结论
  - 论文类型、核心贡献、技术路线
- **关键改进**：即使结构化解析失败，也会保留原始文本内容，确保后续分析有足够信息

#### 步骤2: 创新点分析

基于论文内容本身进行深度创新点分析，**不依赖外部论文检索**：

- **核心创新点识别**：识别3-5个核心创新点，每个创新点包含：
  - 明确描述和技术细节
  - 引用具体章节、图表或表格
  - 创新程度评估
- **技术贡献分析**：分析方法创新、理论贡献、工程贡献、应用创新
- **与现有技术的区别**：基于论文中的相关工作部分进行分析
- **原创性评估**：从新颖性、独立性、深度、影响等角度评估
- **技术优势与局限性**：分析技术优势和局限性

**Prompt特点**：
- 严格要求引用具体位置（章节、图表、表格）
- 要求提供技术细节和证据支撑
- 强调基于论文内容本身，不得编造

#### 步骤3: 多维度深度评估

使用推理模型（deepseek-reasoner）进行多轮深度评估，**不依赖外部论文检索**：

- **技术质量评估**：
  - 方法的合理性和可靠性（理论基础、技术路线、算法设计、实现细节）
  - 实验设计质量（实验设置、对照实验、评估指标、实验规模）
  - 结果的可信度和有效性（成功/失败模式、统计显著性、公平性比较、混淆因素）
  - 技术严谨性（算法实现细节、计算复杂度分析、可扩展性考虑）
- **新颖性评估**：
  - 创新水平（核心算法的新颖之处、对领域的贡献程度）
  - 贡献意义（学术价值、实用价值）
  - 与现有工作的区别（独特贡献、改进程度）
- **清晰度评估**：
  - 写作质量（表达清晰度、术语使用）
  - 逻辑流程和组织（结构合理性、逻辑清晰度）
  - 呈现清晰度（图表质量、公式表达）
  - 可读性（数学公式和符号的一致性、关键概念的解释）
- **完整性评估**：
  - 内容完整性（必要组成部分、信息充分性）
  - 实验充分性（消融研究、不同设置下的验证、失败案例分析）
  - 讨论深度（结果分析、局限性讨论）
  - 缺失要素（实现细节、超参数设置、可复现性信息、资源消耗讨论）

**Prompt特点**：
- 每个维度都有详细的子要求
- 严格要求引用具体章节、表格或图表
- 要求深入分析实验结果，识别成功和失败的模式
- 强调基于论文内容本身，不得编造

#### 步骤4: 生成评阅报告

使用推理模型生成高质量的评阅报告，包含：

- **摘要（Summary）**：200-250字，必须包含：
  - 论文的核心贡献（2-3句话）
  - 主要方法或技术路线（1-2句话）
  - 关键实验结果和数据（2-3句话，必须包含具体性能指标）
- **优点（Strengths）**：2-4个维度，每个维度：
  - 使用明确的主题句作为开头
  - 详细说明该优点的具体表现和意义
  - 引用具体位置（章节、图表、表格）
  - 引用具体数据（性能指标、提升幅度等）
- **缺点/关注点（Weaknesses / Concerns）**：至少3-4个维度，每个缺点：
  - 明确指出具体的问题和位置
  - 说明为什么这是一个问题
  - 引用具体位置
  - 保持客观和建设性
- **给作者的问题（Questions for Authors）**：4-6个建设性问题，覆盖：
  - 技术细节、实验分析、泛化性、设计选择、未来工作
- **评分（Score）**：5个维度，每个评分都有详细说明（2-3句话）：
  - 总体（Overall）、新颖性（Novelty）、技术质量（Technical Quality）、清晰度（Clarity）、置信度（Confidence）

**Prompt特点**：
- 严格要求格式和内容质量
- 要求提供具体数据和性能指标
- 要求引用具体位置支撑观点
- 强调深入具体，避免泛泛而谈

## 性能优化

### V1版本优化

1. **并行处理**：相关论文检索、语义相似度计算和创新点分析可以并行进行
2. **批量embedding**：批量计算embedding，减少API调用次数
3. **超时控制**：各阶段设置独立的超时时间，总超时20分钟
4. **错误恢复**：各阶段独立，失败不影响后续流程

### V2版本优化

1. **简化流程**：4步流程，减少处理时间
2. **无外部依赖**：不依赖Semantic Scholar和Embedding API，更稳定快速
3. **超时控制**：各阶段设置独立的超时时间，总超时20分钟
4. **错误恢复**：各阶段独立，失败不影响后续流程
5. **心跳机制**：SSE流式输出，定期发送心跳，防止客户端超时
6. **重试机制**：评阅报告生成阶段支持自动重试（最多3次），应对临时API错误


## 技术栈

### V1版本

- **FastAPI**: Web框架
- **SSE (Server-Sent Events)**: 流式输出
- **pdfplumber**: PDF文本提取
- **OpenAI API**: Embedding服务
- **Semantic Scholar API**: 论文检索
- **DeepSeek LLM**: 文本生成和推理

### V2版本

- **FastAPI**: Web框架
- **SSE (Server-Sent Events)**: 流式输出
- **pdfplumber**: PDF文本提取
- **DeepSeek LLM**: 文本生成和推理（仅依赖LLM，无需Embedding和检索服务）

## 版本选择建议

### 使用V1版本的情况

- 需要与外部论文进行对比分析
- 需要识别论文与现有工作的具体差异
- 需要基于相关论文进行创新点分析
- 有稳定的Semantic Scholar和Embedding API访问

### 使用V2版本的情况（推荐）

- 追求更稳定、更快速的评阅流程
- 不需要外部论文对比，仅基于论文本身进行评阅
- 希望获得更深入、更有证据支撑的评阅结果
- 生产环境部署，需要减少外部依赖
- 希望评阅结果更符合学术规范（引用具体位置、提供具体数据）

**推荐使用V2版本**，除非有特殊需求需要与外部论文进行对比。

## 注意事项

1. 系统不维护本地数据库，所有处理基于prompt和API调用
2. 单轮对话场景，不支持多轮交互
3. 总处理时间不超过20分钟
4. PDF内容需要Base64编码
5. **V1版本**需要配置LLM和Embedding API密钥
6. **V2版本**仅需要配置LLM API密钥（推荐）

## 许可证

MIT License
