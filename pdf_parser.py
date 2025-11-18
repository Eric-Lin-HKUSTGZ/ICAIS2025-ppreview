"""
PDF解析模块 - 处理Base64编码的PDF，提取文本并进行结构化解析
"""
import base64
import io
import re
from typing import Dict, Optional, Tuple
import pdfplumber
from llm_client import LLMClient
# 优先从v2版本导入，如果没有则从v1版本导入
from prompt_template_v2 import get_pdf_parse_prompt
# from prompt_template import get_pdf_parse_prompt
from config import Config


class PDFParser:
    """PDF解析器"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化PDF解析器
        
        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client
        self.config = Config

    def decode_base64_pdf(self, base64_content: str) -> bytes:
        """
        解码Base64编码的PDF
        
        Args:
            base64_content: Base64编码的PDF字符串
        
        Returns:
            PDF二进制数据
        """
        try:
            # 处理可能包含data URL前缀的情况
            if base64_content.startswith('data:application/pdf;base64,'):
                base64_content = base64_content.split(',', 1)[1]
            elif base64_content.startswith('data:'):
                base64_content = base64_content.split(',', 1)[1]
            
            pdf_bytes = base64.b64decode(base64_content)
            return pdf_bytes
        except Exception as e:
            raise ValueError(f"Base64解码失败: {e}")

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        从PDF中提取文本
        
        Args:
            pdf_bytes: PDF二进制数据
        
        Returns:
            提取的文本内容
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            text_parts = []
            
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            full_text = "\n\n".join(text_parts)
            
            if not full_text or len(full_text.strip()) < 100:
                raise ValueError("PDF文本提取失败或内容过少")
            
            return full_text
        except Exception as e:
            raise ValueError(f"PDF文本提取失败: {e}")

    def parse_pdf_structure(self, pdf_text: str, timeout: Optional[int] = None, language: str = 'en') -> Dict[str, str]:
        """
        使用LLM解析PDF结构化信息
        
        Args:
            pdf_text: PDF文本内容
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            结构化的论文信息字典
        """
        timeout = timeout or self.config.PDF_PARSE_TIMEOUT
        
        try:
            # 限制文本长度，避免超出token限制
            max_text_length = 20000
            if len(pdf_text) > max_text_length:
                pdf_text = pdf_text[:max_text_length] + "\n\n[Text truncated due to length...]"
            
            prompt = get_pdf_parse_prompt(pdf_text, language=language)
            
            # 使用推理模型进行深度解析，提升结构化信息提取的准确性
            response = self.llm_client.get_response(
                prompt,
                use_reasoning_model=True,
                temperature=0.3,
                timeout=timeout
            )
            
            # 解析响应，提取结构化信息
            structured_info = self._parse_llm_response(response)
            
            return structured_info
        except Exception as e:
            # 如果解析失败，返回基本结构
            return {
                "raw_text": pdf_text[:5000],
                "error": f"结构化解析失败: {str(e)}"
            }

    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        """
        解析LLM响应，提取结构化信息
        
        Args:
            response: LLM响应文本
        
        Returns:
            结构化的信息字典
        """
        structured_info = {
            "raw_response": response
        }
        
        # 尝试提取各个字段，包含英文和中文关键词
        sections = {
            "Title": ["Title", "title", "标题"],
            "Authors": ["Authors", "authors", "Author", "作者"],
            "Abstract": ["Abstract", "abstract", "摘要"],
            "Keywords": ["Keywords", "keywords", "Keyword", "关键词"],
            "Introduction": ["Introduction", "introduction", "引言"],
            "Methodology": ["Methodology", "methodology", "Method", "Methods", "方法论", "方法"],
            "Experiments": ["Experiments", "experiments", "Experimental", "Experiment", "实验"],
            "Results": ["Results", "results", "Result", "结果"],
            "Conclusion": ["Conclusion", "conclusions", "Conclusions", "结论"],
            "References": ["References", "references", "Reference", "参考文献"],
            "Paper Type": ["Paper Type", "paper type", "Type", "论文类型", "类型"],
            "Core Contributions": ["Core Contributions", "contributions", "Contributions", "核心贡献", "贡献"],
            "Technical Approach": ["Technical Approach", "technical approach", "Approach", "技术方法", "技术 approach"]
        }
        
        lines = response.split('\n')
        current_section = None
        current_content = []
        matched_sections = []  # 用于debug：记录匹配到的section
        
        def normalize_line(line: str) -> str:
            """标准化行：去除编号、Markdown格式等"""
            # 去除开头的编号格式：1. 2. 3. 等
            line = re.sub(r'^\d+\.\s*', '', line)
            # 去除Markdown加粗：**text** -> text
            line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
            # 去除其他Markdown格式
            line = re.sub(r'^#+\s*', '', line)  # 去除标题标记
            return line.strip()
        
        def match_section(line: str) -> Tuple[Optional[str], str]:
            """
            尝试匹配section，返回 (section_name, remaining_content)
            如果匹配失败，返回 (None, None)
            """
            normalized = normalize_line(line)
            
            # 尝试匹配各个section
            for section_name, keywords in sections.items():
                for keyword in keywords:
                    # 检查是否以关键词开头（可能跟着冒号、破折号等）
                    # 使用不区分大小写的匹配
                    pattern = rf'^{re.escape(keyword)}\s*[：:]\s*(.*)$'
                    match = re.match(pattern, normalized, re.IGNORECASE)
                    if match:
                        return section_name, match.group(1).strip()
                    
                    # 也检查是否只包含关键词（后面可能换行）
                    # 使用不区分大小写的比较
                    keyword_lower = keyword.lower()
                    normalized_lower = normalized.lower()
                    if (normalized_lower == keyword_lower or 
                        normalized_lower.startswith(keyword_lower + ' ') or 
                        normalized_lower.startswith(keyword_lower + '：') or 
                        normalized_lower.startswith(keyword_lower + ':')):
                        # 从normalized中提取冒号后的内容
                        colon_match = re.search(r'[：:]\s*(.*)$', normalized)
                        if colon_match:
                            return section_name, colon_match.group(1).strip()
                        # 如果没有冒号，返回空内容（内容可能在下一行）
                        return section_name, ""
            
            return None, None
        
        for line in lines:
            line_stripped = line.strip()
            
            # 检查是否是新的section标题（即使行是空的，也要检查，因为空行可能是内容的一部分）
            section_name, content = match_section(line_stripped) if line_stripped else (None, None)
            
            if section_name:
                # 保存之前的section（即使内容为空也要保存，因为可能后续会被填充）
                if current_section:
                    section_content = "\n".join(current_content).strip()
                    # 只有当内容不为空时才保存，避免覆盖已有内容
                    if section_content or current_section not in structured_info:
                        structured_info[current_section] = section_content
                
                # 开始新section
                current_section = section_name
                current_content = []
                matched_sections.append(section_name)  # 记录匹配
                
                # 如果有内容，添加到当前section
                if content:
                    current_content.append(content)
                # 如果标题行没有内容，继续读取后续行（包括空行，因为空行可能是段落分隔）
            elif current_section:
                # 如果当前有section，将行添加到内容中
                # 空行也保留，因为它们可能是段落分隔
                if not line_stripped:
                    # 空行：如果前一个内容不为空，保留空行作为段落分隔
                    if current_content and current_content[-1].strip():
                        current_content.append("")
                else:
                    # 非空行：过滤掉明显不是内容的行（如说明性文字）
                    # 过滤规则：
                    # 1. 以"- "开头且很短（<100字符）的行，通常是说明性文字
                    # 2. 以"   -"开头（缩进的说明性文字）
                    # 3. 以"  -"开头（缩进的说明性文字）
                    # 4. 包含"未找到"或"Not found"的短行（可能是占位符）
                    is_explanatory = (
                        (line_stripped.startswith("- ") and len(line_stripped) < 100) or
                        (line_stripped.startswith("   -") and len(line_stripped) < 100) or
                        (line_stripped.startswith("  -") and len(line_stripped) < 100) or
                        (line_stripped in ["未找到", "Not found", "N/A", "无"])
                    )
                    if not is_explanatory:
                        current_content.append(line_stripped)
        
        # 保存最后一个section
        if current_section:
            structured_info[current_section] = "\n".join(current_content).strip()
        
        # Debug信息：记录解析结果
        extracted_sections = [key for key in structured_info.keys() if key not in ["raw_response"]]
        missing_core_sections = [key for key in ["Abstract", "Introduction", "Methodology", "Experiments", "Results", "Conclusion", "Core Contributions", "Technical Approach"] if key not in extracted_sections]
        
        print("\n" + "="*80)
        print("[DEBUG] PDF解析器 - LLM响应解析结果")
        print("="*80)
        print(f"[DEBUG] 响应总行数: {len(lines)}")
        print(f"[DEBUG] 成功匹配的section: {matched_sections}")
        print(f"[DEBUG] 提取到的所有字段: {extracted_sections}")
        print(f"[DEBUG] 缺失的核心章节字段: {missing_core_sections}")
        if missing_core_sections:
            print(f"[DEBUG] ⚠️ 警告: 以下核心章节字段未能从LLM响应中提取: {missing_core_sections}")
            print(f"[DEBUG] 可能原因: LLM输出格式不符合预期，或使用了不同的关键词")
            # 显示前10行，帮助诊断格式问题
            print(f"[DEBUG] 响应前10行预览:")
            for i, line in enumerate(lines[:10], 1):
                print(f"  {i}: {line[:100]}")
        print("="*80 + "\n")
        
        return structured_info

    def parse(self, base64_pdf: str, timeout: Optional[int] = None, language: str = 'en') -> Dict[str, str]:
        """
        完整的PDF解析流程
        
        Args:
            base64_pdf: Base64编码的PDF字符串
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            结构化的论文信息字典
        """
        try:
            # 1. 解码Base64
            pdf_bytes = self.decode_base64_pdf(base64_pdf)
            
            # 2. 提取文本
            pdf_text = self.extract_text_from_pdf(pdf_bytes)
            
            # 3. 结构化解析
            structured_info = self.parse_pdf_structure(pdf_text, timeout, language=language)
            
            # 添加原始文本（截断）
            structured_info["raw_text"] = pdf_text[:10000]  # 保留前10000字符
            
            return structured_info
        except Exception as e:
            # 返回错误信息，但不中断流程
            return {
                "error": f"PDF解析失败: {str(e)}",
                "raw_text": ""
            }

