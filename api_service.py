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
from embedding_client import EmbeddingClient
from retriever import PaperRetriever
from pdf_parser import PDFParser
from paper_analyzer import PaperAnalyzer
from reviewer import Reviewer
from prompt_template import detect_language


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


def format_sse_data(content: str) -> str:
    """生成OpenAI格式的SSE数据
    
    格式：data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"..."}}]}
    """
    data = {
        "object": "chat.completion.chunk",
        "choices": [{
            "delta": {
                "content": content
            }
        }]
    }
    # 手动添加'data: '前缀，确保格式符合要求
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def format_sse_done() -> str:
    """生成SSE结束标记
    
    格式：data: [DONE]
    """
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
        *args, **kwargs: 传递给函数的参数
        heartbeat_interval: 心跳间隔（秒），默认25秒
    
    Yields:
        心跳数据（空格字符）或任务结果
    """
    import asyncio
    import time
    
    start_time = time.time()
    last_heartbeat = start_time
    
    # 创建任务（使用asyncio.to_thread将同步函数转换为协程）
    task = asyncio.create_task(asyncio.to_thread(task_func, *args, **kwargs))
    
    # 在任务执行期间定期发送心跳
    while not task.done():
        await asyncio.sleep(1)  # 每秒检查一次
        now = time.time()
        
        # 如果超过心跳间隔，发送心跳数据
        if now - last_heartbeat >= heartbeat_interval:
            yield format_sse_data(" ")  # 发送一个空格作为心跳
            last_heartbeat = now
        
        # 如果设置了超时并且超过总时长，取消任务
        if timeout is not None and (now - start_time) > timeout:
            task.cancel()
            raise asyncio.TimeoutError(f"任务执行超过 {timeout} 秒，已取消")
    
    # 等待任务完成并返回结果
    try:
        result = await task
        # 使用特殊标记来区分结果和心跳数据
        # 返回一个元组，第一个元素是标记，第二个元素是结果
        yield ("RESULT", result)
    except Exception as e:
        # 如果任务失败，记录错误并重新抛出异常
        print(f"⚠️  任务执行失败: {e}")
        import traceback
        print(traceback.format_exc())
        raise e


async def _generate_review_internal(query: str, pdf_content: str) -> AsyncGenerator[str, None]:
    """内部生成器函数，执行实际的评阅逻辑"""
    start_time = time.time()
    
    try:
        # print(f"[DEBUG] 开始执行论文评阅，query长度: {len(query)}, pdf_content长度: {len(pdf_content)}")
        
        # 先检测语言，用于后续消息模板
        language = await asyncio.to_thread(detect_language, query)
        # print(f"[DEBUG] 检测到语言: {'中文' if language == 'zh' else 'English'}")
        
        # 根据语言设置消息模板
        if language == 'zh':
            msg_templates = {
                'step1': "### 📄 步骤 1/6: PDF解析与结构化提取\n\n✅ 已完成\n\n",
                'step2': "### 🔑 步骤 2/6: 关键信息提取\n\n✅ 已完成\n\n",
                'step3': lambda n: (
                    "### 📚 步骤 3/6: 相关论文检索\n\n"
                    f"✅ 已检索到 {n} 篇相关论文\n\n" if n is not None else
                    "### 📚 步骤 3/6: 相关论文检索\n\n✅ 已完成\n\n"
                ),
                'step3_skip_degraded': "### 📚 步骤 3/6: 相关论文检索\n\n⚠️ 由于PDF解析信息不足，跳过外部论文检索，后续分析仅基于上传论文内容。\n\n",
                'step3_skip_no_query': "### 📚 步骤 3/6: 相关论文检索\n\n⚠️ 无法生成有效查询，跳过外部论文检索。\n\n",
                'step4': "### 💡 步骤 4/6: 语义分析与创新点识别\n\n✅ 已完成\n\n",
                'step5': "### ⭐ 步骤 5/6: 多维度深度评估\n\n✅ 已完成\n\n",
                'step6': "### 📋 步骤 6/6: 生成评阅报告\n\n",
                'error_config': "## ❌ 错误\n\n配置验证失败，请检查环境变量设置\n\n",
                'error_config_exception': lambda e: f"## ❌ 错误\n\n配置验证异常: {e}\n\n",
                'error_llm_init': lambda e: f"## ❌ 错误\n\nLLM客户端初始化失败: {e}\n\n",
                'error_embedding_init': lambda e: f"## ❌ 错误\n\nEmbedding客户端初始化失败: {e}\n\n",
                'error_retriever_init': lambda e: f"## ❌ 错误\n\n论文检索器初始化失败: {e}\n\n",
                'error_pdf_parse': lambda e: f"## ❌ 错误\n\nPDF解析失败，无法继续: {e}\n\n",
                'error_key_extraction': "## ❌ 错误\n\n关键信息提取失败\n\n",
                'error_retrieval': lambda e: f"## ❌ 错误\n\n论文检索失败: {e}\n\n",
                'error_analysis': lambda e: f"## ❌ 错误\n\n分析失败: {e}\n\n",
                'error_review': lambda e: f"## ❌ 错误\n\n评阅报告生成失败: {e}\n\n",
                'error_timeout': lambda t: f"## ❌ 超时错误\n\n请求处理超过 {t} 秒，已自动终止\n\n",
                'error_general': lambda e: f"## ❌ 错误\n\n程序执行失败: {e}\n\n",
                'pdf_timeout': "⚠️ PDF解析超时，使用备用方法提取基本信息\n\n",
                'key_extraction_timeout': "⚠️ 关键信息提取超时，使用备用方法\n\n",
                'pdf_fallback': "基本信息提取完成\n\n",
                'pdf_warning': lambda e: f"⚠️ PDF解析警告: {e}\n\n"
            }
        else:
            msg_templates = {
                'step1': "### 📄 Step 1/6: PDF Parsing and Structure Extraction\n\n✅ Completed\n\n",
                'step2': "### 🔑 Step 2/6: Key Information Extraction\n\n✅ Completed\n\n",
                'step3': lambda n: (
                    "### 📚 Step 3/6: Related Paper Retrieval\n\n"
                    f"✅ Retrieved {n} related papers\n\n" if n is not None else
                    "### 📚 Step 3/6: Related Paper Retrieval\n\n✅ Completed\n\n"
                ),
                'step3_skip_degraded': "### 📚 Step 3/6: Related Paper Retrieval\n\n⚠️ Skipped because the parsed PDF lacks reliable structure; subsequent analysis relies solely on the uploaded manuscript.\n\n",
                'step3_skip_no_query': "### 📚 Step 3/6: Related Paper Retrieval\n\n⚠️ Skipped because no valid query could be generated from the PDF content.\n\n",
                'step4': "### 💡 Step 4/6: Semantic Analysis and Innovation Identification\n\n✅ Completed\n\n",
                'step5': "### ⭐ Step 5/6: Multi-dimensional Deep Evaluation\n\n✅ Completed\n\n",
                'step6': "### 📋 Step 6/6: Review Report Generation\n\n",
                'error_config': "## ❌ Error\n\nConfiguration validation failed. Please check environment variables.\n\n",
                'error_config_exception': lambda e: f"## ❌ Error\n\nConfiguration validation exception: {e}\n\n",
                'error_llm_init': lambda e: f"## ❌ Error\n\nLLM client initialization failed: {e}\n\n",
                'error_embedding_init': lambda e: f"## ❌ Error\n\nEmbedding client initialization failed: {e}\n\n",
                'error_retriever_init': lambda e: f"## ❌ Error\n\nPaper retriever initialization failed: {e}\n\n",
                'error_pdf_parse': lambda e: f"## ❌ Error\n\nPDF parsing failed. Cannot continue: {e}\n\n",
                'error_key_extraction': "## ❌ Error\n\nKey information extraction failed.\n\n",
                'error_retrieval': lambda e: f"## ❌ Error\n\nPaper retrieval failed: {e}\n\n",
                'error_analysis': lambda e: f"## ❌ Error\n\nAnalysis failed: {e}\n\n",
                'error_review': lambda e: f"## ❌ Error\n\nReview report generation failed: {e}\n\n",
                'error_timeout': lambda t: f"## ❌ Timeout Error\n\nRequest processing exceeded {t} seconds. Automatically terminated.\n\n",
                'error_general': lambda e: f"## ❌ Error\n\nProcess execution failed: {e}\n\n",
                'pdf_timeout': "⚠️ PDF parsing timeout, using fallback method to extract basic information\n\n",
                'key_extraction_timeout': "⚠️ Key information extraction timeout, using fallback method\n\n",
                'pdf_fallback': "Basic information extraction completed\n\n",
                'pdf_warning': lambda e: f"⚠️ PDF parsing warning: {e}\n\n"
            }
    
        # 验证配置（不输出）
        # print("[DEBUG] 开始验证配置")
        try:
            config_valid = await asyncio.to_thread(Config.validate_config)
            if not config_valid:
                # print("[DEBUG] 配置验证失败")
                for chunk in stream_message(msg_templates['error_config']):
                    yield chunk
                return
            # print("[DEBUG] 配置验证成功")
        except Exception as e:
            # print(f"[DEBUG] 配置验证异常: {e}")
            for chunk in stream_message(msg_templates['error_config_exception'](e)):
                yield chunk
            return
    
        # 创建组件（不输出初始化信息）
        # print("[DEBUG] 开始初始化LLM客户端")
        try:
            llm_client = LLMClient()
            # print("[DEBUG] LLM客户端初始化成功")
        except Exception as e:
            # print(f"[DEBUG] LLM客户端初始化失败: {e}")
            import traceback
            print(traceback.format_exc())
            for chunk in stream_message(msg_templates['error_llm_init'](e)):
                yield chunk
            return
        
        # print("[DEBUG] 开始初始化Embedding客户端")
        try:
            embedding_client = EmbeddingClient()
            # print("[DEBUG] Embedding客户端初始化成功")
        except Exception as e:
            # print(f"[DEBUG] Embedding客户端初始化失败: {e}")
            import traceback
            print(traceback.format_exc())
            for chunk in stream_message(msg_templates['error_embedding_init'](e)):
                yield chunk
            return
        
        # print("[DEBUG] 开始初始化论文检索器")
        try:
            retriever = PaperRetriever()
            # print("[DEBUG] 论文检索器初始化成功")
        except Exception as e:
            # print(f"[DEBUG] 论文检索器初始化失败: {e}")
            import traceback
            print(traceback.format_exc())
            for chunk in stream_message(msg_templates['error_retriever_init'](e)):
                yield chunk
            return
        
        # 创建解析器、分析器和评阅器
        # print("[DEBUG] 创建解析器、分析器和评阅器")
        pdf_parser = PDFParser(llm_client)
        paper_analyzer = PaperAnalyzer(llm_client, embedding_client, retriever)
        reviewer = Reviewer(llm_client)
        
        # 阶段1: PDF解析（简化输出，增加心跳）
        # print("[DEBUG] 开始阶段1: PDF解析")
        structured_info = None
        try:
            # 增加超时时间，因为使用了reasoner模型需要更长时间
            parse_timeout = Config.PDF_PARSE_TIMEOUT * 2  # 将超时时间翻倍
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
            # print("[DEBUG] PDF解析超时，尝试使用备用方法提取基本信息")
            for chunk in stream_message(msg_templates['pdf_timeout']):
                yield chunk
            # 超时时，尝试提取基本信息
            try:
                # 直接提取PDF文本，不进行结构化解析
                pdf_bytes = await asyncio.to_thread(pdf_parser.decode_base64_pdf, pdf_content)
                pdf_text = await asyncio.to_thread(pdf_parser.extract_text_from_pdf, pdf_bytes)
                
                # 创建基本的结构化信息
                structured_info = {
                    "raw_text": pdf_text[:10000],  # 保留前10000字符
                    "Title": "",
                    "Abstract": pdf_text[:500] if len(pdf_text) > 0 else "",  # 使用前500字符作为摘要
                    "error": "PDF结构化解析超时，已使用备用方法提取基本信息"
                }
                
                # 尝试从文本中提取标题（简单方法：取第一行或前100个字符）
                lines = pdf_text.split('\n')
                for line in lines[:10]:  # 检查前10行
                    line = line.strip()
                    if len(line) > 10 and len(line) < 200:  # 标题通常在10-200字符之间
                        structured_info["Title"] = line
                        break
                
                if not structured_info["Title"]:
                    structured_info["Title"] = pdf_text[:100].strip().replace('\n', ' ')
                
                # print("[DEBUG] 备用方法提取基本信息完成")
                for chunk in stream_message(msg_templates['pdf_fallback']):
                    yield chunk
            except Exception as e:
                # print(f"[DEBUG] 备用方法也失败: {e}")
                for chunk in stream_message(msg_templates['error_pdf_parse'](e)):
                    yield chunk
                return
        except Exception as e:
            # print(f"[DEBUG] PDF解析失败: {e}")
            import traceback
            print(traceback.format_exc())
            # 尝试使用备用方法
            try:
                pdf_bytes = await asyncio.to_thread(pdf_parser.decode_base64_pdf, pdf_content)
                pdf_text = await asyncio.to_thread(pdf_parser.extract_text_from_pdf, pdf_bytes)
                structured_info = {
                    "raw_text": pdf_text[:10000],
                    "Title": pdf_text[:100].strip().replace('\n', ' ') if pdf_text else "",
                    "Abstract": pdf_text[:500] if len(pdf_text) > 0 else "",
                    "error": f"PDF解析失败: {str(e)}"
                }
                # print("[DEBUG] 使用备用方法提取基本信息")
                for chunk in stream_message(msg_templates['pdf_timeout']):
                    yield chunk
                for chunk in stream_message(msg_templates['pdf_fallback']):
                    yield chunk
            except Exception as e2:
                # print(f"[DEBUG] 备用方法也失败: {e2}")
                for chunk in stream_message(msg_templates['error_pdf_parse'](e2)):
                    yield chunk
                return
        
        if structured_info is None:
            for chunk in stream_message(msg_templates['error_pdf_parse']("PDF parsing returned empty result")):
                yield chunk
            return
        
        # PDF解析完成后的debug信息
        print("\n" + "="*80)
        print("[DEBUG] PDF解析完成 - 初步结果")
        print("="*80)
        print(f"[DEBUG] structured_info的键: {list(structured_info.keys())}")
        if "error" in structured_info:
            print(f"[DEBUG] ⚠️ 检测到error字段: {structured_info.get('error')}")
        if "raw_text" in structured_info:
            raw_text_len = len(structured_info.get("raw_text", ""))
            print(f"[DEBUG] raw_text长度: {raw_text_len} 字符")
        if "raw_response" in structured_info:
            raw_response_len = len(structured_info.get("raw_response", ""))
            print(f"[DEBUG] raw_response长度: {raw_response_len} 字符")
            # 显示raw_response的前500字符，帮助诊断LLM输出格式
            raw_response_preview = structured_info.get("raw_response", "")[:500]
            print(f"[DEBUG] raw_response预览:\n{raw_response_preview}...")
        print("="*80 + "\n")
        
        # 检查是否有错误
        # print("[DEBUG] 检查PDF解析结果")
        if "error" in structured_info:
            # print(f"[DEBUG] PDF解析有警告: {structured_info.get('error')}")
            for chunk in stream_message(msg_templates['pdf_warning'](structured_info.get('error'))):
                yield chunk
            # 如果只有错误信息，无法继续
            if not structured_info.get("raw_text"):
                # print("[DEBUG] PDF解析失败，无法继续")
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
        
        # 详细的debug检查
        debug_info = paper_analyzer.debug_core_content_check(structured_info)
        has_core_sections = debug_info["has_core_content"]
        has_error = debug_info["has_error"]
        degraded_parse = (not has_core_sections) or has_error
        
        # 输出详细的debug信息
        print("\n" + "="*80)
        print("[DEBUG] PDF解析结果诊断")
        print("="*80)
        print(f"[DEBUG] has_core_content: {has_core_sections}")
        print(f"[DEBUG] has_error字段: {has_error}")
        if has_error:
            print(f"[DEBUG] error消息: {debug_info['error_message']}")
        print(f"[DEBUG] degraded_parse: {degraded_parse}")
        print(f"[DEBUG] structured_info中的所有键: {debug_info['all_keys']}")
        print("\n[DEBUG] 核心章节字段检查结果:")
        for section, exists in debug_info['core_sections_status'].items():
            status = "✓ 存在" if exists else "✗ 缺失"
            value_preview = ""
            if exists:
                value = structured_info.get(section, "")
                value_preview = f" (内容预览: {value[:50]}...)" if len(value) > 50 else f" (内容: {value})"
            print(f"  {status}: {section}{value_preview}")
        print(f"\n[DEBUG] 缺失的核心章节字段: {debug_info['missing_core_sections']}")
        if degraded_parse:
            print("\n[DEBUG] ⚠️ 触发degraded_parse的原因:")
            if not has_core_sections:
                print("  - 原因1: has_core_content() 返回 False (所有核心章节字段都缺失)")
            if has_error:
                print(f"  - 原因2: structured_info 中存在 'error' 字段: {debug_info['error_message']}")
        print("="*80 + "\n")
        
        # 阶段2: 关键信息提取与查询构建（简化输出，增加心跳）
        # print("[DEBUG] 开始阶段2: 关键信息提取")
        try:
            # 只提取关键词，不进行完整分析（节省时间）
            # 增加超时时间，因为使用了reasoner模型需要更长时间
            extraction_timeout = Config.KEY_EXTRACTION_TIMEOUT * 2  # 将超时时间翻倍
            heartbeat_interval = 15
            keywords = []
            async for item in run_with_heartbeat(
                paper_analyzer.extract_keywords,
                structured_info,
                extraction_timeout,
                language,
                heartbeat_interval=heartbeat_interval,
                timeout=extraction_timeout + 10
            ):
                if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                    keywords = item[1] or []
                    break
                else:
                    yield item
            query = await asyncio.to_thread(paper_analyzer.build_query, keywords, structured_info)
            # print(f"[DEBUG] 关键词提取完成: {keywords}")
        except asyncio.TimeoutError:
            # print("[DEBUG] 关键信息提取超时，使用备用方法")
            for chunk in stream_message(msg_templates['key_extraction_timeout']):
                yield chunk
            # 使用备用方法提取关键词
            keywords = await asyncio.to_thread(paper_analyzer._extract_fallback_keywords, structured_info)
            query = await asyncio.to_thread(paper_analyzer.build_query, keywords, structured_info)
            # print(f"[DEBUG] 备用方法提取关键词完成: {keywords}")
        except Exception as e:
            # print(f"[DEBUG] 关键信息提取失败: {e}")
            for chunk in stream_message(msg_templates['error_key_extraction']):
                yield chunk
            return
        
        # 输出步骤2完成
        for chunk in stream_message(msg_templates['step2']):
            yield chunk
        
        # 阶段3: 相关论文检索（简化输出）
        # print("[DEBUG] 开始阶段3: 相关论文检索")
        related_papers = []
        skip_reason_key = None
        if not query:
            skip_reason_key = 'step3_skip_no_query'
        elif degraded_parse:
            skip_reason_key = 'step3_skip_degraded'
        
        if skip_reason_key:
            for chunk in stream_message(msg_templates[skip_reason_key]):
                yield chunk
        else:
            if query:
                try:
                    heartbeat_interval = 15
                    async for item in run_with_heartbeat(
                        paper_analyzer.retrieve_related_papers,
                        query,
                        keywords,
                        Config.RETRIEVAL_TIMEOUT,
                        heartbeat_interval=heartbeat_interval,
                        timeout=Config.RETRIEVAL_TIMEOUT + 10
                    ):
                        if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                            related_papers = item[1] or []
                            break
                        else:
                            yield item
                except Exception as e:
                    import traceback
                    print(traceback.format_exc())
                    related_papers = []
            for chunk in stream_message(msg_templates['step3'](len(related_papers))):
                yield chunk
        
        # 阶段4: 语义相似度分析与创新点识别（简化输出，增加心跳防止超时）
        # print("[DEBUG] 开始阶段4: 语义分析与创新点识别")
        innovation_analysis = ""
        
        # 格式化结构化信息为文本
        paper_text = paper_analyzer._format_structured_info(structured_info)
        semantic_similarities = []
        heartbeat_interval = 15
        
        if related_papers:
            # 有相关论文时，先计算语义相似度，再进行创新点分析
            try:
                async for item in run_with_heartbeat(
                    paper_analyzer.calculate_semantic_similarity,
                    paper_text,
                    related_papers,
                    heartbeat_interval=heartbeat_interval,
                    timeout=Config.SEMANTIC_ANALYSIS_TIMEOUT
                ):
                    if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                        semantic_similarities = item[1] or []
                    else:
                        yield item
                
                async for item in run_with_heartbeat(
                    paper_analyzer.analyze_innovation,
                    structured_info,
                    related_papers,
                    Config.SEMANTIC_ANALYSIS_TIMEOUT,
                    language,
                    heartbeat_interval=heartbeat_interval,
                    timeout=Config.SEMANTIC_ANALYSIS_TIMEOUT + 10
                ):
                    if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                        innovation_analysis = item[1] or ""
                    else:
                        yield item
            except asyncio.TimeoutError:
                # print("[DEBUG] 语义分析阶段超时")
                for chunk in stream_message(msg_templates['error_analysis']("语义分析阶段超时")):
                    yield chunk
                if language == 'zh':
                    innovation_analysis = "语义分析阶段超时，使用论文自身信息进行基本创新点总结。"
                else:
                    innovation_analysis = "Semantic analysis timed out. Falling back to a basic innovation summary based on the paper content only."
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                for chunk in stream_message(msg_templates['error_analysis'](e)):
                    yield chunk
                innovation_analysis = ""
        else:
            # 没有相关论文时，基于论文本身进行创新点分析，同时发送心跳
            try:
                async for item in run_with_heartbeat(
                    paper_analyzer.analyze_innovation,
                    structured_info,
                    [],
                    Config.SEMANTIC_ANALYSIS_TIMEOUT,
                    language,
                    heartbeat_interval=heartbeat_interval,
                    timeout=Config.SEMANTIC_ANALYSIS_TIMEOUT + 10
                ):
                    if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                        innovation_analysis = item[1] or ""
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
        
        # 输出步骤4完成
        for chunk in stream_message(msg_templates['step4']):
            yield chunk
        
        # 阶段5: 多维度深度评估（简化输出，在reviewer.review中完成）
        # print("[DEBUG] 开始阶段5: 多维度深度评估")
        # 输出步骤5完成（评估在reviewer.review中完成）
        for chunk in stream_message(msg_templates['step5']):
            yield chunk
        
        # 阶段6: 生成评阅报告（完整输出）
        # print("[DEBUG] 开始阶段6: 生成评阅报告")
        for chunk in stream_message(msg_templates['step6']):
            yield chunk
        
        # 发送进度提示
        if language == 'zh':
            progress_msg = "🔄 正在生成评阅报告，请稍候...\n\n"
        else:
            progress_msg = "🔄 Generating review report, please wait...\n\n"
        for chunk in stream_message(progress_msg):
            yield chunk
        
        try:
            # print(f"[DEBUG] 开始生成评阅报告，超时时间: {Config.EVALUATION_TIMEOUT + Config.REPORT_GENERATION_TIMEOUT + 20}秒")
            review = None
            async for item in run_with_heartbeat(
                reviewer.review,
                structured_info, innovation_analysis, related_papers, 
                Config.EVALUATION_TIMEOUT + Config.REPORT_GENERATION_TIMEOUT, language,
                heartbeat_interval=25,
                timeout=Config.EVALUATION_TIMEOUT + Config.REPORT_GENERATION_TIMEOUT + 20
            ):
                if isinstance(item, tuple) and len(item) == 2 and item[0] == "RESULT":
                    review = item[1]
                    # print(f"[DEBUG] 评阅报告生成完成，长度: {len(review) if review else 0} 字符")
                    break
                else:
                    yield item
            
            if not review or review.strip() == "":
                # print(f"[DEBUG] 评阅报告为空: review={review}")
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
            # print("[DEBUG] 评阅报告生成超时")
            if language == 'zh':
                error_msg = "## ❌ 错误\n\n评阅报告生成超时\n\n"
            else:
                error_msg = "## ❌ Error\n\nReview report generation timeout\n\n"
            for chunk in stream_message(error_msg):
                yield chunk
            return
        except Exception as e:
            # print(f"[DEBUG] 评阅报告生成失败: {e}")
            import traceback
            print(traceback.format_exc())
            for chunk in stream_message(msg_templates['error_review'](e)):
                yield chunk
            return
    
        elapsed = time.time() - start_time
        # print(f"[DEBUG] 论文评阅完成，总耗时: {elapsed:.2f}秒")
        # 不输出总耗时到流式响应，保持输出简洁
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ [_generate_review_internal] 未捕获的异常: {e}\n{error_trace}")
        # 确保异常信息通过SSE流发送
        try:
            # 检测语言以使用正确的错误消息
            try:
                language = await asyncio.to_thread(detect_language, query)
                if language == 'zh':
                    error_msg = f"## ❌ 错误\n\n程序执行失败: {e}\n\n```\n{error_trace}\n```\n\n"
                else:
                    error_msg = f"## ❌ Error\n\nProcess execution failed: {e}\n\n```\n{error_trace}\n```\n\n"
            except:
                # 如果检测语言失败，使用英文
                error_msg = f"## ❌ Error\n\nProcess execution failed: {e}\n\n```\n{error_trace}\n```\n\n"
            for chunk in stream_message(error_msg):
                yield chunk
        except Exception as send_error:
            print(f"❌ 发送错误信息时失败: {send_error}")
            # 如果发送失败，至少尝试发送一个简单的错误消息
            try:
                yield format_sse_data(f"## ❌ Error\n\nProcess execution failed: {e}\n\n")
            except:
                pass


async def generate_review_stream(query: str, pdf_content: str) -> AsyncGenerator[str, None]:
    """生成评阅的流式输出生成器（带超时控制）"""
    start_time = time.time()
    # print(f"[DEBUG] [generate_review_stream] 生成器启动，query长度: {len(query)}, pdf_content长度: {len(pdf_content)}")
    
    try:
        item_count = 0
        async for item in _generate_review_internal(query, pdf_content):
            item_count += 1
            # if item_count % 100 == 0:
            #     print(f"[DEBUG] [generate_review_stream] 已yield {item_count} 个chunk")
            
            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed > REQUEST_TIMEOUT:
                # print(f"[DEBUG] [generate_review_stream] 请求超时，已处理 {item_count} 个chunk")
                # 检测语言以使用正确的错误消息
                try:
                    language = await asyncio.to_thread(detect_language, query)
                    if language == 'zh':
                        timeout_msg = f"## ❌ 超时错误\n\n请求处理超过 {REQUEST_TIMEOUT} 秒，已自动终止\n\n"
                    else:
                        timeout_msg = f"## ❌ Timeout Error\n\nRequest processing exceeded {REQUEST_TIMEOUT} seconds. Automatically terminated.\n\n"
                except:
                    timeout_msg = f"## ❌ Timeout Error\n\nRequest processing exceeded {REQUEST_TIMEOUT} seconds. Automatically terminated.\n\n"
                for chunk in stream_message(timeout_msg):
                    yield chunk
                yield format_sse_done()
                return
            yield item
        
        # print(f"[DEBUG] [generate_review_stream] 生成器正常完成，共yield {item_count} 个chunk")
        # 发送结束标记
        yield format_sse_done()
                
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ [generate_review_stream] 生成器错误: {e}\n{error_trace}")
        try:
            # 检测语言以使用正确的错误消息
            try:
                language = await asyncio.to_thread(detect_language, query)
                if language == 'zh':
                    error_msg = f"## ❌ 错误\n\n程序执行失败: {e}\n\n```\n{error_trace}\n```\n\n"
                else:
                    error_msg = f"## ❌ Error\n\nProcess execution failed: {e}\n\n```\n{error_trace}\n```\n\n"
            except:
                # 如果检测语言失败，使用英文
                error_msg = f"## ❌ Error\n\nProcess execution failed: {e}\n\n```\n{error_trace}\n```\n\n"
            for chunk in stream_message(error_msg):
                yield chunk
            yield format_sse_done()
        except Exception as send_error:
            print(f"❌ [generate_review_stream] 发送错误信息时失败: {send_error}")
            try:
                yield format_sse_data(f"## ❌ Error\n\nProcess execution failed: {e}\n\n")
                yield format_sse_done()
            except:
                pass


@app.post("/paper_review")
async def paper_review(request: PaperReviewRequest):
    """
    论文评阅API端点
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not request.pdf_content or not request.pdf_content.strip():
        raise HTTPException(status_code=400, detail="PDF content cannot be empty")
    
    return StreamingResponse(
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

