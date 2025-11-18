"""
评阅生成模块 V2 - 基于大模型能力的论文评阅系统（不涉及文件检索）
多维度评估、评阅报告生成
"""
import time
from typing import Dict, Optional
from llm_client import LLMClient
from prompt_template_v2 import (
    get_innovation_analysis_prompt_v2,
    get_evaluation_prompt_v2,
    get_review_generation_prompt_v2
)
from config import Config


class ReviewerV2:
    """论文评阅器 V2 - 基于大模型能力，不涉及文件检索"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化评阅器
        
        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client
        self.config = Config

    def analyze_innovation(self, structured_info: Dict[str, str], timeout: Optional[int] = None, language: str = 'en') -> str:
        """
        分析论文的创新点（基于论文内容本身）
        
        Args:
            structured_info: 结构化的论文信息
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            创新点分析结果文本
        """
        timeout = timeout or self.config.SEMANTIC_ANALYSIS_TIMEOUT
        
        try:
            # 格式化相关信息
            info_text = self._format_structured_info(structured_info)
            
            prompt = get_innovation_analysis_prompt_v2(info_text, language=language)
            
            # 使用推理模型进行深度分析
            response = self.llm_client.get_response(
                prompt,
                use_reasoning_model=True,
                temperature=0.5,
                timeout=timeout
            )
            
            return response
        except Exception as e:
            print(f"⚠️  创新点分析失败: {e}")
            if language == 'zh':
                return f"创新点分析失败: {str(e)}"
            else:
                return f"Innovation analysis failed: {str(e)}"

    def evaluate(self, structured_info: Dict[str, str], innovation_analysis: str, timeout: Optional[int] = None, language: str = 'en') -> str:
        """
        多维度评估论文（基于论文内容本身，不依赖相关论文）
        
        Args:
            structured_info: 结构化的论文信息
            innovation_analysis: 创新点分析结果
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            评估结果文本
        """
        timeout = timeout or self.config.EVALUATION_TIMEOUT
        
        try:
            # 格式化相关信息
            info_text = self._format_structured_info(structured_info)
            
            prompt = get_evaluation_prompt_v2(info_text, innovation_analysis, language=language)
            
            # 使用推理模型进行深度评估
            response = self.llm_client.get_response(
                prompt,
                use_reasoning_model=True,
                temperature=0.5,
                timeout=timeout
            )
            
            return response
        except Exception as e:
            print(f"⚠️  评估失败: {e}")
            if language == 'zh':
                return f"评估失败: {str(e)}"
            else:
                return f"Evaluation failed: {str(e)}"

    def generate_review(self, structured_info: Dict[str, str], evaluation: str, innovation_analysis: str, timeout: Optional[int] = None, language: str = 'en') -> str:
        """
        生成评阅报告（带重试机制）
        
        Args:
            structured_info: 结构化的论文信息
            evaluation: 评估结果
            innovation_analysis: 创新点分析结果
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            Markdown格式的评阅报告
        """
        timeout = timeout or self.config.REPORT_GENERATION_TIMEOUT
        
        # 格式化相关信息
        info_text = self._format_structured_info(structured_info)
        prompt = get_review_generation_prompt_v2(info_text, evaluation, innovation_analysis, language=language)
        
        # 重试机制：最多重试3次，针对502/503错误
        max_retries = 3
        retry_delays = [2, 4, 8]  # 指数退避：2秒、4秒、8秒
        
        for attempt in range(max_retries):
            try:
                # 使用推理模型生成评阅报告
                response = self.llm_client.get_response(
                    prompt,
                    use_reasoning_model=True,
                    temperature=0.5,
                    timeout=timeout
                )
                
                # 如果成功，返回结果
                if response and response.strip():
                    return response
                else:
                    # 如果返回空内容，也视为失败，继续重试
                    if attempt < max_retries - 1:
                        if language == 'zh':
                            print(f"⚠️  评阅报告生成返回空内容，{retry_delays[attempt]}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        else:
                            print(f"⚠️  Review generation returned empty content, retrying in {retry_delays[attempt]} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delays[attempt])
                        continue
                    
            except Exception as e:
                error_str = str(e)
                # 检查是否是502/503错误（服务器错误，可以重试）
                is_retryable = (
                    "502" in error_str or 
                    "503" in error_str or 
                    "Bad Gateway" in error_str or
                    "Service Unavailable" in error_str or
                    "timeout" in error_str.lower()
                )
                
                if is_retryable and attempt < max_retries - 1:
                    if language == 'zh':
                        print(f"⚠️  评阅报告生成失败（可重试错误）: {e}，{retry_delays[attempt]}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    else:
                        print(f"⚠️  Review generation failed (retryable error): {e}, retrying in {retry_delays[attempt]} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delays[attempt])
                    continue
                else:
                    # 不可重试的错误或已达到最大重试次数
                    print(f"⚠️  评阅报告生成失败: {e}")
                    if attempt == max_retries - 1:
                        # 最后一次尝试失败，使用fallback
                        return self._generate_fallback_review(structured_info, evaluation, innovation_analysis, language=language)
                    raise
        
        # 所有重试都失败，使用fallback
        return self._generate_fallback_review(structured_info, evaluation, innovation_analysis, language=language)

    def review(self, structured_info: Dict[str, str], timeout: Optional[int] = None, language: str = 'en') -> str:
        """
        完整的评阅流程 V2
        
        Args:
            structured_info: 结构化的论文信息
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            Markdown格式的评阅报告
        """
        try:
            # 1. 创新点分析
            innovation_analysis = self.analyze_innovation(structured_info, timeout, language=language)
            
            # 2. 多维度评估
            evaluation = self.evaluate(structured_info, innovation_analysis, timeout, language=language)
            
            # 3. 生成评阅报告
            review = self.generate_review(structured_info, evaluation, innovation_analysis, timeout, language=language)
            
            return review
        except Exception as e:
            print(f"⚠️  评阅流程失败: {e}")
            return self._generate_fallback_review(structured_info, "", "", language=language)

    def _generate_fallback_review(self, structured_info: Dict[str, str], evaluation: str, innovation_analysis: str, language: str = 'en') -> str:
        """生成备用评阅报告（当LLM生成失败时），利用已有的结构化信息"""
        title = structured_info.get("Title", "Unknown Paper")
        abstract = structured_info.get("Abstract", "No abstract available.")
        introduction = structured_info.get("Introduction", "")
        methodology = structured_info.get("Methodology", "")
        results = structured_info.get("Results", "")
        conclusion = structured_info.get("Conclusion", "")
        core_contributions = structured_info.get("Core Contributions", "")
        technical_approach = structured_info.get("Technical Approach", "")
        
        # 提取摘要的关键信息
        abstract_summary = abstract[:300] if abstract and len(abstract) > 200 else abstract
        
        # 从evaluation中提取评分信息（如果有）
        evaluation_scores = ""
        if evaluation:
            if language == 'zh' and "评分" in evaluation:
                lines = evaluation.split('\n')
                score_lines = [line for line in lines if any(keyword in line for keyword in ["评分", "Score", "Overall", "总体", "/10", "/5"])]
                if score_lines:
                    evaluation_scores = "\n".join(score_lines[:10])
            elif language == 'en' and "Score" in evaluation:
                lines = evaluation.split('\n')
                score_lines = [line for line in lines if any(keyword in line for keyword in ["Score", "Overall", "/10", "/5"])]
                if score_lines:
                    evaluation_scores = "\n".join(score_lines[:10])
        
        # 从innovation_analysis中提取关键创新点
        innovation_summary = ""
        if innovation_analysis and len(innovation_analysis) > 50:
            innovation_summary = innovation_analysis[:200] + "..." if len(innovation_analysis) > 200 else innovation_analysis
        
        if language == 'zh':
            strengths = []
            if core_contributions:
                strengths.append(f"- 论文提出了以下核心贡献：{core_contributions[:150]}...")
            if technical_approach:
                strengths.append(f"- 技术方法：{technical_approach[:150]}...")
            if not strengths:
                strengths = ["- 论文解决了一个重要的研究问题。", "- 方法论看起来合理。"]
            
            weaknesses = []
            if not results:
                weaknesses.append("- 实验结果部分信息不足，需要更多细节。")
            if not methodology:
                weaknesses.append("- 方法论描述可能不够详细。")
            if not weaknesses:
                weaknesses = ["- 需要进一步分析以评估技术质量。", "- 可能需要额外的实验验证。"]
            
            questions = []
            if not methodology:
                questions.append("1. 您能否提供更多关于方法论的细节？")
            if not results:
                questions.append("2. 您能否提供更多关于实验结果的细节？")
            if len(questions) < 2:
                questions.append("3. 这项工作与现有方法相比如何？")
            
            # 构建创新点部分
            innovation_section = ""
            if innovation_summary:
                innovation_section = f"## 核心创新点\n\n{innovation_summary}\n\n"
            
            # 构建主要发现部分
            findings_section = ""
            if results:
                findings_section = f"## 主要发现\n\n{results[:200]}...\n\n"
            
            # 构建评分部分
            score_section = ""
            if evaluation_scores:
                score_section = f"- {evaluation_scores}\n"
            
            return f"""# 摘要（Summary）

本文研究了**{title}**。

{abstract_summary}

{innovation_section}# 优点（Strengths）

{chr(10).join(strengths)}

# 缺点/关注点（Weaknesses / Concerns）

{chr(10).join(weaknesses)}

{findings_section}# 给作者的问题（Questions for Authors）

{chr(10).join(questions[:3])}

# 评分（Score）

{score_section}- 总体（Overall）: 待评估
- 新颖性（Novelty）: 待评估
- 技术质量（Technical Quality）: 待评估
- 清晰度（Clarity）: 待评估
- 置信度（Confidence）: 3/5

---

*注：这是由于API调用失败而生成的备用评阅报告。报告基于PDF解析的结构化信息生成，可能不够完整。请手动审查并根据需要补充详细信息。*"""
        else:
            strengths = []
            if core_contributions:
                strengths.append(f"- The paper presents the following core contributions: {core_contributions[:150]}...")
            if technical_approach:
                strengths.append(f"- Technical approach: {technical_approach[:150]}...")
            if not strengths:
                strengths = ["- The paper addresses an important research question.", "- The methodology appears sound."]
            
            weaknesses = []
            if not results:
                weaknesses.append("- Experimental results section lacks sufficient detail.")
            if not methodology:
                weaknesses.append("- Methodology description may be insufficient.")
            if not weaknesses:
                weaknesses = ["- Further analysis needed to assess technical quality.", "- Additional experimental validation may be required."]
            
            questions = []
            if not methodology:
                questions.append("1. Could you provide more details on the methodology?")
            if not results:
                questions.append("2. Could you provide more details on the experimental results?")
            if len(questions) < 2:
                questions.append("3. How does this work compare to existing approaches?")
            
            # 构建创新点部分
            innovation_section = ""
            if innovation_summary:
                innovation_section = f"## Core Innovations\n\n{innovation_summary}\n\n"
            
            # 构建主要发现部分
            findings_section = ""
            if results:
                findings_section = f"## Key Findings\n\n{results[:200]}...\n\n"
            
            # 构建评分部分
            score_section = ""
            if evaluation_scores:
                score_section = f"- {evaluation_scores}\n"
            
            return f"""# Summary

This paper presents research on **{title}**.

{abstract_summary}

{innovation_section}# Strengths

{chr(10).join(strengths)}

# Weaknesses / Concerns

{chr(10).join(weaknesses)}

{findings_section}# Questions for Authors

{chr(10).join(questions[:3])}

# Score

{score_section}- Overall: Pending
- Novelty: Pending
- Technical Quality: Pending
- Clarity: Pending
- Confidence: 3/5

---

*Note: This is a fallback review generated due to API call failures. The review is based on structured information extracted from the PDF and may be incomplete. Please review manually and supplement with additional details as needed.*"""

    def _format_structured_info(self, structured_info: Dict[str, str]) -> str:
        """格式化结构化信息为文本"""
        parts = []
        for key, value in structured_info.items():
            if key not in ["raw_text", "raw_response", "error"] and value:
                parts.append(f"{key}:\n{value}\n")
        raw_text = structured_info.get("raw_text", "")
        if raw_text:
            snippet = raw_text[:1800].strip()
            if snippet:
                parts.append("Raw PDF Excerpt:\n" + snippet + ("\n...\n" if len(raw_text) > len(snippet) else "\n"))
        if not parts:
            error_msg = structured_info.get("error") or "Structured sections unavailable."
            minimal = raw_text[:400].strip() if raw_text else "Raw PDF text unavailable."
            parts.append(f"[Parser Warning] {error_msg}\n\n{minimal}")
        return "\n".join(parts)

