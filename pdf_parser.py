"""
PDF解析模块 - 处理Base64编码的PDF，提取文本并进行结构化解析
"""
import base64
import io
from typing import Dict, Optional
import pdfplumber
from llm_client import LLMClient
from prompt_template import get_pdf_parse_prompt
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
        
        # 尝试提取各个字段
        sections = {
            "Title": ["Title", "title"],
            "Authors": ["Authors", "authors", "Author"],
            "Abstract": ["Abstract", "abstract"],
            "Keywords": ["Keywords", "keywords", "Keyword"],
            "Introduction": ["Introduction", "introduction"],
            "Methodology": ["Methodology", "methodology", "Method", "Methods"],
            "Experiments": ["Experiments", "experiments", "Experimental", "Experiment"],
            "Results": ["Results", "results", "Result"],
            "Conclusion": ["Conclusion", "conclusions", "Conclusions"],
            "References": ["References", "references", "Reference"],
            "Paper Type": ["Paper Type", "paper type", "Type"],
            "Core Contributions": ["Core Contributions", "contributions", "Contributions"],
            "Technical Approach": ["Technical Approach", "technical approach", "Approach"]
        }
        
        lines = response.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # 检查是否是新的section标题
            found_section = False
            for section_name, keywords in sections.items():
                for keyword in keywords:
                    if line_stripped.startswith(keyword) or line_stripped.startswith(f"**{keyword}"):
                        # 保存之前的section
                        if current_section:
                            structured_info[current_section] = "\n".join(current_content).strip()
                        # 开始新section
                        current_section = section_name
                        current_content = []
                        # 提取该行的内容（去掉标题部分）
                        content_part = line_stripped.split(':', 1)
                        if len(content_part) > 1:
                            current_content.append(content_part[1].strip())
                        found_section = True
                        break
                if found_section:
                    break
            
            if not found_section and current_section:
                current_content.append(line_stripped)
        
        # 保存最后一个section
        if current_section:
            structured_info[current_section] = "\n".join(current_content).strip()
        
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

