"""
API服务 V2 - 基于大模型能力的论文评阅系统（不涉及文件检索）
简化的4步流程：PDF解析 → 创新点分析 → 多维度评估 → 生成评阅报告
"""
import os
import json
import time
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import signal
import sys

from config import Config
from llm_client import LLMClient
from pdf_parser import PDFParser
from reviewer_v2 import ReviewerV2
from prompt_template_v2 import detect_language


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
    title="ICAIS2025-PaperReview API V2",
    version="2.0.0",
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


def format_sse_data(content: str) -> str:
    """生成OpenAI格式的SSE数据"""
    data = {
        "object": "chat.completion.chunk",
        "choices": [{
            "delta": {
                "content": content
            }
        }]
    }
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def format_sse_done() -> str:
    """生成SSE结束标记"""
    return "data: [DONE]\n\n"

def stream_message(message: str, chunk_size: int = 1):
    """将消息按字符流式输出（同步生成器）"""
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i + chunk_size]
        yield format_sse_data(chunk)


async def run_with_heartbeat(task_func, *args, heartbeat_interval=25, timeout=None, **kwargs):
    """
    执行长时间任务，期间定期发送心跳数据
    
    Args:
        task_func: 要执行的同步函数
        *args: 位置参数
        heartbeat_interval: 心跳间隔（秒）
        timeout: 任务超时时间（秒），None表示不超时
        **kwargs: 关键字参数
    """
    import asyncio
    start_time = time.time()
    
    # 创建任务
    task = asyncio.create_task(asyncio.to_thread(task_func, *args, **kwargs))
    
    # 定期发送心跳
    while not task.done():
        await asyncio.sleep(heartbeat_interval)
        
        # 检查超时
        if timeout is not None:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                task.cancel()
                raise asyncio.TimeoutError(f"任务执行超过 {timeout} 秒，已取消")
        
        # 发送心跳（空内容）
        yield format_sse_data("")
    
    # 返回结果
    try:
        result = await task
        yield ("RESULT", result)
    except Exception as e:
        raise e


async def _generate_review_internal_v2(query: str, pdf_content: str) -> AsyncGenerator[str, None]:
    """内部生成器函数，执行实际的评阅逻辑 V2（4步流程）"""
    start_time = time.time()
    
    try:
        # 先检测语言，用于后续消息模板
        language = await asyncio.to_thread(detect_language, query)
        
        # 根据语言设置消息模板（4步流程）
        if language == 'zh':
            msg_templates = {
                'step1': "### 📄 步骤 1/4: PDF解析与结构化提取\n\n✅ 已完成\n\n",
                'step2': "### 💡 步骤 2/4: 创新点分析\n\n✅ 已完成\n\n",
                'step3': "### ⭐ 步骤 3/4: 多维度深度评估\n\n✅ 已完成\n\n",
                'step4': "### 📋 步骤 4/4: 生成评阅报告\n\n",
                'error_config': "## ❌ 错误\n\n配置验证失败，请检查环境变量设置\n\n",
                'error_config_exception': lambda e: f"## ❌ 错误\n\n配置验证异常: {e}\n\n",
                'error_llm_init': lambda e: f"## ❌ 错误\n\nLLM客户端初始化失败: {e}\n\n",
                'error_pdf_parse': lambda e: f"## ❌ 错误\n\nPDF解析失败，无法继续: {e}\n\n",
                'error_analysis': lambda e: f"## ❌ 错误\n\n分析失败: {e}\n\n",
                'error_review': lambda e: f"## ❌ 错误\n\n评阅报告生成失败: {e}\n\n",
                'error_timeout': lambda t: f"## ❌ 超时错误\n\n请求处理超过 {t} 秒，已自动终止\n\n",
                'error_general': lambda e: f"## ❌ 错误\n\n程序执行失败: {e}\n\n",
                'pdf_timeout': "⚠️ PDF解析超时，使用备用方法提取基本信息\n\n",
                'pdf_fallback': "基本信息提取完成\n\n",
                'pdf_warning': lambda e: f"⚠️ PDF解析警告: {e}\n\n"
            }
        else:
            msg_templates = {
                'step1': "### 📄 Step 1/4: PDF Parsing and Structure Extraction\n\n✅ Completed\n\n",
                'step2': "### 💡 Step 2/4: Innovation Analysis\n\n✅ Completed\n\n",
                'step3': "### ⭐ Step 3/4: Multi-dimensional Deep Evaluation\n\n✅ Completed\n\n",
                'step4': "### 📋 Step 4/4: Review Report Generation\n\n",
                'error_config': "## ❌ Error\n\nConfiguration validation failed. Please check environment variables.\n\n",
                'error_config_exception': lambda e: f"## ❌ Error\n\nConfiguration validation exception: {e}\n\n",
                'error_llm_init': lambda e: f"## ❌ Error\n\nLLM client initialization failed: {e}\n\n",
                'error_pdf_parse': lambda e: f"## ❌ Error\n\nPDF parsing failed. Cannot continue: {e}\n\n",
                'error_analysis': lambda e: f"## ❌ Error\n\nAnalysis failed: {e}\n\n",
                'error_review': lambda e: f"## ❌ Error\n\nReview report generation failed: {e}\n\n",
                'error_timeout': lambda t: f"## ❌ Timeout Error\n\nRequest processing exceeded {t} seconds. Automatically terminated.\n\n",
                'error_general': lambda e: f"## ❌ Error\n\nProcess execution failed: {e}\n\n",
                'pdf_timeout': "⚠️ PDF parsing timeout, using fallback method to extract basic information\n\n",
                'pdf_fallback': "Basic information extraction completed\n\n",
                'pdf_warning': lambda e: f"⚠️ PDF parsing warning: {e}\n\n"
            }
    
        # 验证配置
        try:
            config_valid = await asyncio.to_thread(Config.validate_config)
            if not config_valid:
                for chunk in stream_message(msg_templates['error_config']):
                    yield chunk
                return
        except Exception as e:
            for chunk in stream_message(msg_templates['error_config_exception'](e)):
                yield chunk
            return
    
        # 创建组件
        try:
            llm_client = LLMClient()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            for chunk in stream_message(msg_templates['error_llm_init'](e)):
                yield chunk
            return
    
        # 创建解析器和评阅器
        pdf_parser = PDFParser(llm_client)
        reviewer = ReviewerV2(llm_client)
        
        # 步骤1: PDF解析
        structured_info = None
        try:
            parse_timeout = Config.PDF_PARSE_TIMEOUT * 2
            heartbeat_interval = 15
            async for item in run_with_heartbeat(
                pdf_parser.parse,
                pdf_content,
                parse_timeout,
                language,
                heartbeat_interval=heartbeat_interval,
                timeout=parse_timeout + 10
            ):
                if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                    structured_info = item[1]
                    break
                else:
                    yield item
        except asyncio.TimeoutError:
            for chunk in stream_message(msg_templates['pdf_timeout']):
                yield chunk
            try:
                pdf_bytes = await asyncio.to_thread(pdf_parser.decode_base64_pdf, pdf_content)
                pdf_text = await asyncio.to_thread(pdf_parser.extract_text_from_pdf, pdf_bytes)
                structured_info = {
                    "raw_text": pdf_text[:10000],
                    "Title": "",
                    "Abstract": pdf_text[:500] if len(pdf_text) > 0 else "",
                    "error": "PDF结构化解析超时，已使用备用方法提取基本信息"
                }
                lines = pdf_text.split('\n')
                for line in lines[:10]:
                    line = line.strip()
                    if len(line) > 10 and len(line) < 200:
                        structured_info["Title"] = line
                        break
                if not structured_info["Title"]:
                    structured_info["Title"] = pdf_text[:100].strip().replace('\n', ' ')
                for chunk in stream_message(msg_templates['pdf_fallback']):
                    yield chunk
            except Exception as e:
                for chunk in stream_message(msg_templates['error_pdf_parse'](e)):
                    yield chunk
                return
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            try:
                pdf_bytes = await asyncio.to_thread(pdf_parser.decode_base64_pdf, pdf_content)
                pdf_text = await asyncio.to_thread(pdf_parser.extract_text_from_pdf, pdf_bytes)
                structured_info = {
                    "raw_text": pdf_text[:10000],
                    "Title": pdf_text[:100].strip().replace('\n', ' ') if pdf_text else "",
                    "Abstract": pdf_text[:500] if len(pdf_text) > 0 else "",
                    "error": f"PDF解析失败: {str(e)}"
                }
                for chunk in stream_message(msg_templates['pdf_timeout']):
                    yield chunk
                for chunk in stream_message(msg_templates['pdf_fallback']):
                    yield chunk
            except Exception as e2:
                for chunk in stream_message(msg_templates['error_pdf_parse'](e2)):
                    yield chunk
                return
        
        if structured_info is None:
            for chunk in stream_message(msg_templates['error_pdf_parse']("PDF parsing returned empty result")):
                yield chunk
            return
        
        if "error" in structured_info:
            for chunk in stream_message(msg_templates['pdf_warning'](structured_info.get('error'))):
                yield chunk
            if not structured_info.get("raw_text"):
                if language == 'zh':
                    error_msg = "## ❌ 错误\n\nPDF解析失败，无法继续\n\n"
                else:
                    error_msg = "## ❌ Error\n\nPDF parsing failed. Cannot continue.\n\n"
                for chunk in stream_message(error_msg):
                    yield chunk
                return
        
        # 输出步骤1完成
        for chunk in stream_message(msg_templates['step1']):
            yield chunk
        
        # 步骤2: 创新点分析
        innovation_analysis = ""
        try:
            analysis_timeout = Config.SEMANTIC_ANALYSIS_TIMEOUT
            heartbeat_interval = 15
            async for item in run_with_heartbeat(
                reviewer.analyze_innovation,
                structured_info,
                analysis_timeout,
                language,
                heartbeat_interval=heartbeat_interval,
                timeout=analysis_timeout + 10
            ):
                if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                    innovation_analysis = item[1] or ""
                    break
                else:
                    yield item
        except asyncio.TimeoutError:
            if language == 'zh':
                innovation_analysis = "创新点分析超时，使用论文自身信息进行基本总结。"
            else:
                innovation_analysis = "Innovation analysis timed out. Falling back to a basic summary from the paper itself."
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            if language == 'zh':
                innovation_analysis = f"创新点分析失败: {str(e)}"
            else:
                innovation_analysis = f"Innovation analysis failed: {str(e)}"
        
        # 输出步骤2完成
        for chunk in stream_message(msg_templates['step2']):
            yield chunk
        
        # 步骤3: 多维度评估
        evaluation = ""
        try:
            evaluation_timeout = Config.EVALUATION_TIMEOUT
            heartbeat_interval = 15
            async for item in run_with_heartbeat(
                reviewer.evaluate,
                structured_info,
                innovation_analysis,
                evaluation_timeout,
                language,
                heartbeat_interval=heartbeat_interval,
                timeout=evaluation_timeout + 10
            ):
                if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                    evaluation = item[1] or ""
                    break
                else:
                    yield item
        except asyncio.TimeoutError:
            if language == 'zh':
                evaluation = "评估超时，使用论文自身信息进行基本评估。"
            else:
                evaluation = "Evaluation timed out. Falling back to a basic evaluation from the paper itself."
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            if language == 'zh':
                evaluation = f"评估失败: {str(e)}"
            else:
                evaluation = f"Evaluation failed: {str(e)}"
        
        # 输出步骤3完成
        for chunk in stream_message(msg_templates['step3']):
            yield chunk
        
        # 步骤4: 生成评阅报告
        for chunk in stream_message(msg_templates['step4']):
            yield chunk
        
        if language == 'zh':
            progress_msg = "🔄 正在生成评阅报告，请稍候...\n\n"
        else:
            progress_msg = "🔄 Generating review report, please wait...\n\n"
        for chunk in stream_message(progress_msg):
            yield chunk
        
        try:
            review = None
            async for item in run_with_heartbeat(
                reviewer.generate_review,
                structured_info,
                evaluation,
                innovation_analysis,
                Config.REPORT_GENERATION_TIMEOUT,
                language,
                heartbeat_interval=25,
                timeout=Config.REPORT_GENERATION_TIMEOUT + 20
            ):
                if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                    review = item[1]
                    break
                else:
                    yield item
            
            if not review or review.strip() == "":
                if language == 'zh':
                    error_msg = "⚠️ 评阅报告生成失败，返回空内容\n\n"
                else:
                    error_msg = "⚠️ Review report generation failed, returned empty content\n\n"
                for chunk in stream_message(error_msg):
                    yield chunk
            else:
                # 流式输出评阅报告
                for chunk in stream_message(f"{review}\n\n"):
                    yield chunk
        except asyncio.TimeoutError:
            if language == 'zh':
                error_msg = "## ❌ 错误\n\n评阅报告生成超时\n\n"
            else:
                error_msg = "## ❌ Error\n\nReview report generation timeout\n\n"
            for chunk in stream_message(error_msg):
                yield chunk
            return
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            for chunk in stream_message(msg_templates['error_review'](e)):
                yield chunk
            return
    
        elapsed = time.time() - start_time
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ [_generate_review_internal_v2] 未捕获的异常: {e}\n{error_trace}")
        try:
            try:
                language = await asyncio.to_thread(detect_language, query)
            except:
                language = 'en'
            
            if language == 'zh':
                error_msg = f"## ❌ 错误\n\n程序执行失败: {e}\n\n"
            else:
                error_msg = f"## ❌ Error\n\nProcess execution failed: {e}\n\n"
            for chunk in stream_message(error_msg):
                yield chunk
        except:
            pass
    finally:
        # 发送结束标记
        yield format_sse_done()


@app.post("/paper_review")
async def paper_review(request: PaperReviewRequest):
    """
    论文评阅端点 V2 - 基于大模型能力，不涉及文件检索
    """
    try:
        return StreamingResponse(
            _generate_review_internal_v2(request.query, request.pdf_content),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "ok", "service": "ICAIS2025-PaperReview API V2", "timestamp": time.time()}


@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "ICAIS2025-PaperReview API V2",
        "version": "2.0.0",
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
    
    print("🚀 启动 FastAPI 服务 V2...")
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

