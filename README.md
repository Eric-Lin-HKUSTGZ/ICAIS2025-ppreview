# ICAIS2025-PaperReview

论文评阅智能体系统 - 基于多阶段智能分析流程的创新论文评阅系统


## 文件结构

```
ICAIS2025-ppreview/
├── main.py                 # FastAPI主应用
├── config.py              # 配置管理
├── llm_client.py          # LLM客户端
├── embedding_client.py    # Embedding客户端
├── pdf_parser.py          # PDF解析模块
├── paper_analyzer.py      # 论文分析模块
├── reviewer.py            # 评阅生成模块
├── retriever.py           # 论文检索模块
├── prompt_template.py     # Prompt模板
├── requirements.txt       # 依赖包
├── Dockerfile            # Docker配置
└── README.md             # 项目说明
```

## 系统概述

本系统是一个创新的论文评阅智能体，通过多阶段智能分析流程，结合PDF结构化解析、相关论文检索对比、语义相似度分析和推理模型深度评估，生成高质量的论文评阅报告。

### 核心创新点

1. **多阶段智能分析流程**：不是简单地将PDF文本输入LLM，而是采用分阶段、多维度分析
2. **PDF结构化解析**：智能提取论文的关键结构化信息
3. **相关论文检索与对比分析**：利用Semantic Scholar API检索相关论文进行深度对比
4. **语义相似度分析**：使用embedding识别创新点和相似工作
5. **推理模型深度评估**：使用deepseek-reasoner进行多轮深度推理分析

## 系统架构

```
PDF输入 → 结构化解析 → 关键信息提取 → 相关论文检索 → 语义对比分析 → 多维度评估 → 生成评阅报告
```

## API接口

### 端点

```
POST http://<agent_service_host>:3000/paper_review
```

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

```bash
python main.py
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

## 系统流程

### 阶段1: PDF智能解析与结构化提取

- 解码Base64编码的PDF
- 提取PDF文本内容
- 使用LLM进行结构化解析，提取：
  - 标题、作者、摘要、关键词
  - 引言、方法、实验、结果、结论
  - 论文类型、核心贡献、技术路线

### 阶段2: 关键信息提取与查询构建

- 提取3-5个核心关键词
- 构建用于Semantic Scholar检索的查询字符串
- 识别研究领域和主题

### 阶段3: 相关论文检索与筛选

- 使用Semantic Scholar API进行多维度检索：
  - 基于关键词的最新论文
  - 基于关键词的高引用论文
  - 基于标题和摘要的相关论文
- 使用embedding计算语义相似度
- 筛选出最相关的5-10篇论文

### 阶段4: 语义相似度分析与创新点识别

- 计算待评论文与相关论文的语义相似度
- 使用LLM分析论文的创新点和技术贡献
- 识别论文与现有工作的差异和优势
- 评估论文的原创性

### 阶段5: 多维度深度评估

使用推理模型（deepseek-reasoner）进行多轮深度分析：

- **技术质量评估**：方法合理性、实验设计、结果可信度
- **新颖性评估**：创新点、与现有工作的差异
- **清晰度评估**：写作质量、逻辑清晰度、可读性
- **完整性评估**：内容完整性、实验充分性

### 阶段6: 生成评阅报告

使用推理模型生成结构化的评阅报告，包含Summary、Strengths、Weaknesses/Concerns、Questions for Authors和Score等部分。

## 性能优化

1. **并行处理**：相关论文检索、语义相似度计算和创新点分析可以并行进行
2. **批量embedding**：批量计算embedding，减少API调用次数
3. **超时控制**：各阶段设置独立的超时时间，总超时20分钟
4. **错误恢复**：各阶段独立，失败不影响后续流程


## 技术栈

- **FastAPI**: Web框架
- **SSE (Server-Sent Events)**: 流式输出
- **pdfplumber**: PDF文本提取
- **OpenAI API**: Embedding服务
- **Semantic Scholar API**: 论文检索
- **DeepSeek LLM**: 文本生成和推理

## 注意事项

1. 系统不维护本地数据库，所有处理基于prompt和API调用
2. 单轮对话场景，不支持多轮交互
3. 总处理时间不超过20分钟
4. PDF内容需要Base64编码
5. 需要配置LLM和Embedding API密钥

## 许可证

MIT License
