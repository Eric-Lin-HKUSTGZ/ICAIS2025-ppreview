import os
import json
import time
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import signal
import sys

from config import Config
from llm_client import LLMClient
from embedding_client import EmbeddingClient
from retriever import PaperRetriever
from pdf_parser import PDFParser
from paper_analyzer import PaperAnalyzer
from reviewer import Reviewer


def load_env_file(env_file: str):
    """加载环境变量文件"""
    if not os.path.isabs(env_file):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_file = os.path.join(current_dir, env_file)
    
    if os.path.exists(env_file):
        print(f"✓ 找到 .env 文件: {env_file}")
        loaded_count = 0
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"\'')
                    loaded_count += 1
        print(f"✓ 成功加载 {loaded_count} 个环境变量")
        return True
    else:
        print(f"⚠️ 警告: 未找到 .env 文件: {env_file}")
        return False


# 加载环境变量
load_env_file(".env")

# 创建FastAPI应用
app = FastAPI(
    title="ICAIS2025-PaperReview API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.middleware("http")
async def simple_log_middleware(request, call_next):
    """简化的日志中间件"""
    start_time = time.time()
    path = request.url.path
    
    if not path.startswith("/health"):
        print(f"📥 [{time.strftime('%H:%M:%S')}] {request.method} {path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        if not path.startswith("/health"):
            print(f"📤 [{time.strftime('%H:%M:%S')}] {request.method} {path} - {response.status_code} ({process_time:.3f}s)")
        return response
    except Exception as e:
        print(f"❌ [{time.strftime('%H:%M:%S')}] 错误: {request.method} {path} - {e}")
        raise

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 设置全局超时
REQUEST_TIMEOUT = Config.REVIEW_TIMEOUT  # 20分钟总超时


class PaperReviewRequest(BaseModel):
    query: str
    pdf_content: str


def format_sse_data(data: dict) -> str:
    """生成SSE格式的数据"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _generate_review_internal(query: str, pdf_content: str) -> AsyncGenerator[str, None]:
    """内部生成器函数，执行实际的评阅逻辑"""
    start_time = time.time()
    
    yield format_sse_data({
        "type": "start",
        "message": "# 开始论文评阅\n\n"
    })
    
    # 验证配置
    try:
        config_valid = await asyncio.to_thread(Config.validate_config)
        if not config_valid:
            yield format_sse_data({
                "type": "error",
                "message": "## 错误\n\n配置验证失败，请检查环境变量设置\n\n"
            })
            return
    except Exception as e:
        yield format_sse_data({
            "type": "error",
            "message": f"## 错误\n\n配置验证异常: {e}\n\n"
        })
        return
    
    # 创建组件
    try:
        llm_client = LLMClient()
        yield format_sse_data({"type": "info", "message": "LLM客户端初始化成功\n\n"})
    except Exception as e:
        yield format_sse_data({
            "type": "error",
            "message": f"## 错误\n\nLLM客户端初始化失败: {e}\n\n"
        })
        return
    
    try:
        embedding_client = EmbeddingClient()
        yield format_sse_data({"type": "info", "message": "Embedding客户端初始化成功\n\n"})
    except Exception as e:
        yield format_sse_data({
            "type": "error",
            "message": f"## 错误\n\nEmbedding客户端初始化失败: {e}\n\n"
        })
        return
    
    try:
        retriever = PaperRetriever()
        yield format_sse_data({"type": "info", "message": "论文检索器初始化成功\n\n"})
    except Exception as e:
        yield format_sse_data({
            "type": "error",
            "message": f"## 错误\n\n论文检索器初始化失败: {e}\n\n"
        })
        return
    
    # 创建解析器、分析器和评阅器
    pdf_parser = PDFParser(llm_client)
    paper_analyzer = PaperAnalyzer(llm_client, embedding_client, retriever)
    reviewer = Reviewer(llm_client)
    
    # 阶段1: PDF解析
    yield format_sse_data({"type": "step", "step": 1, "message": "## 阶段1: PDF解析与结构化提取\n\n"})
    try:
        structured_info = await asyncio.wait_for(
            asyncio.to_thread(pdf_parser.parse, pdf_content, Config.PDF_PARSE_TIMEOUT),
            timeout=Config.PDF_PARSE_TIMEOUT + 10
        )
        yield format_sse_data({
            "type": "step_result",
            "step": 1,
            "message": "PDF解析完成\n\n"
        })
    except asyncio.TimeoutError:
        yield format_sse_data({
            "type": "error",
            "message": "## 错误\n\nPDF解析超时\n\n"
        })
        return
    except Exception as e:
        yield format_sse_data({
            "type": "error",
            "message": f"## 错误\n\nPDF解析失败: {e}\n\n"
        })
        return
    
    # 检查是否有错误
    if "error" in structured_info:
        yield format_sse_data({
            "type": "warning",
            "message": f"⚠️ PDF解析警告: {structured_info.get('error')}\n\n"
        })
        # 如果只有错误信息，无法继续
        if not structured_info.get("raw_text"):
            yield format_sse_data({
                "type": "error",
                "message": "## 错误\n\nPDF解析失败，无法继续\n\n"
            })
            return
    
    # 阶段2: 关键信息提取与查询构建
    yield format_sse_data({"type": "step", "step": 2, "message": "## 阶段2: 关键信息提取\n\n"})
    try:
        # 只提取关键词，不进行完整分析（节省时间）
        keywords = await asyncio.wait_for(
            asyncio.to_thread(paper_analyzer.extract_keywords, structured_info, Config.KEY_EXTRACTION_TIMEOUT),
            timeout=Config.KEY_EXTRACTION_TIMEOUT + 10
        )
        query = await asyncio.to_thread(paper_analyzer.build_query, keywords, structured_info)
        yield format_sse_data({
            "type": "step_result",
            "step": 2,
            "message": f"提取到关键词: {', '.join(keywords) if keywords else '无'}\n\n"
        })
    except asyncio.TimeoutError:
        yield format_sse_data({
            "type": "warning",
            "message": "⚠️ 关键信息提取超时，使用备用方法\n\n"
        })
        keywords = []
        query = structured_info.get("Title", "")[:100] if structured_info.get("Title") else ""
    
    # 阶段3: 相关论文检索（并行进行）
    yield format_sse_data({"type": "step", "step": 3, "message": "## 阶段3: 相关论文检索\n\n"})
    related_papers = []
    if query:
        try:
            related_papers = await asyncio.wait_for(
                asyncio.to_thread(paper_analyzer.retrieve_related_papers, query, keywords, Config.RETRIEVAL_TIMEOUT),
                timeout=Config.RETRIEVAL_TIMEOUT + 10
            )
        except Exception as e:
            yield format_sse_data({
                "type": "warning",
                "message": f"⚠️ 论文检索失败: {e}，将跳过对比分析\n\n"
            })
            related_papers = []
    
    yield format_sse_data({
        "type": "step_result",
        "step": 3,
        "message": f"检索到 **{len(related_papers)}** 篇相关论文\n\n"
    })
    
    # 阶段4: 语义相似度分析与创新点识别（并行进行）
    yield format_sse_data({"type": "step", "step": 4, "message": "## 阶段4: 语义分析与创新点识别\n\n"})
    innovation_analysis = ""
    if related_papers:
        # 并行计算语义相似度和创新点分析
        try:
            # 计算语义相似度
            # 格式化结构化信息为文本
            info_parts = []
            for key, value in structured_info.items():
                if key not in ["raw_text", "raw_response", "error"] and value:
                    info_parts.append(f"{key}:\n{value}\n")
            paper_text = "\n".join(info_parts)
            
            semantic_task = asyncio.create_task(
                asyncio.to_thread(paper_analyzer.calculate_semantic_similarity, paper_text, related_papers)
            )
            
            # 分析创新点
            innovation_task = asyncio.create_task(
                asyncio.wait_for(
                    asyncio.to_thread(paper_analyzer.analyze_innovation, structured_info, related_papers, Config.SEMANTIC_ANALYSIS_TIMEOUT),
                    timeout=Config.SEMANTIC_ANALYSIS_TIMEOUT + 10
                )
            )
            
            # 等待两个任务完成
            semantic_similarities, innovation_analysis = await asyncio.gather(
                semantic_task,
                innovation_task,
                return_exceptions=True
            )
            
            if isinstance(innovation_analysis, Exception):
                yield format_sse_data({
                    "type": "warning",
                    "message": f"⚠️ 创新点分析失败: {innovation_analysis}\n\n"
                })
                innovation_analysis = ""
            elif isinstance(semantic_similarities, Exception):
                yield format_sse_data({
                    "type": "warning",
                    "message": f"⚠️ 语义相似度计算失败: {semantic_similarities}\n\n"
                })
        except Exception as e:
            yield format_sse_data({
                "type": "warning",
                "message": f"⚠️ 分析失败: {e}\n\n"
            })
            innovation_analysis = ""
    
    yield format_sse_data({
        "type": "step_result",
        "step": 4,
        "message": "创新点分析完成\n\n"
    })
    
    # 阶段5: 多维度深度评估
    yield format_sse_data({"type": "step", "step": 5, "message": "## 阶段5: 多维度深度评估\n\n"})
    # 这个阶段在reviewer.review中完成，这里只是提示
    
    # 阶段6: 生成评阅报告
    yield format_sse_data({"type": "step", "step": 6, "message": "## 阶段6: 生成评阅报告\n\n"})
    try:
        review = await asyncio.wait_for(
            asyncio.to_thread(reviewer.review, structured_info, innovation_analysis, related_papers, Config.EVALUATION_TIMEOUT + Config.REPORT_GENERATION_TIMEOUT),
            timeout=Config.EVALUATION_TIMEOUT + Config.REPORT_GENERATION_TIMEOUT + 20
        )
        
        # 流式输出评阅报告
        yield format_sse_data({
            "type": "section",
            "section": "review",
            "message": review + "\n\n"
        })
        
        yield format_sse_data({
            "type": "final",
            "message": "评阅完成\n\n"
        })
    except asyncio.TimeoutError:
        yield format_sse_data({
            "type": "error",
            "message": "## 错误\n\n评阅报告生成超时\n\n"
        })
        return
    except Exception as e:
        yield format_sse_data({
            "type": "error",
            "message": f"## 错误\n\n评阅报告生成失败: {e}\n\n"
        })
        return
    
    elapsed = time.time() - start_time
    yield format_sse_data({
        "type": "info",
        "message": f"\n\n⏱️ 总耗时: {elapsed:.2f}秒 ({elapsed/60:.2f}分钟)\n\n"
    })


async def generate_review_stream(query: str, pdf_content: str) -> AsyncGenerator[str, None]:
    """生成评阅的流式输出生成器（带超时控制）"""
    start_time = time.time()
    
    try:
        async for item in _generate_review_internal(query, pdf_content):
            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed > REQUEST_TIMEOUT:
                yield format_sse_data({
                    "type": "error",
                    "message": f"## 超时错误\n\n请求处理超过 {REQUEST_TIMEOUT} 秒，已自动终止\n\n"
                })
                return
            yield item
                
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ 生成器错误: {e}\n{error_trace}")
        yield format_sse_data({
            "type": "error",
            "message": f"## 错误\n\n程序执行失败: {e}\n\n```\n{error_trace}\n```\n\n"
        })


@app.post("/paper_review")
async def paper_review(request: PaperReviewRequest):
    """
    论文评阅API端点
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not request.pdf_content or not request.pdf_content.strip():
        raise HTTPException(status_code=400, detail="PDF content cannot be empty")
    
    return EventSourceResponse(
        generate_review_stream(request.query, request.pdf_content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "ok", "service": "ICAIS2025-PaperReview API", "timestamp": time.time()}


@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "ICAIS2025-PaperReview API",
        "version": "1.0.0",
        "health": "http://localhost:3000/health",
        "docs": "http://localhost:3000/docs",
        "paper_review": "POST /paper_review"
    }


# 优雅关闭处理
def shutdown_handler(signum, frame):
    print(f"\n⚠️ 收到终止信号 {signum}，正在关闭服务...")
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == "__main__":
    import uvicorn
    
    # 验证端口可用性
    import socket
    def check_port(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return True
            except OSError:
                return False
    
    if not check_port(3000):
        print(f"❌ 端口3000已被占用，请检查是否有其他服务在使用")
        sys.exit(1)
    
    print("🚀 启动 FastAPI 服务...")
    print(f"📍 监听地址: http://0.0.0.0:3000")
    print(f"📝 健康检查: curl http://localhost:3000/health")
    print(f"📚 API文档: http://localhost:3000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_level="info",
        access_log=True,
        reload=False,
        workers=1,
        loop="asyncio",
        timeout_keep_alive=30,
        limit_concurrency=100,
    )

