"""
评阅生成模块 - 多维度评估、评阅报告生成
"""
from typing import Dict, Optional
from llm_client import LLMClient
from prompt_template import get_evaluation_prompt, get_review_generation_prompt
from config import Config


class Reviewer:
    """论文评阅器"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化评阅器
        
        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client
        self.config = Config

    def evaluate(self, structured_info: Dict[str, str], innovation_analysis: str, related_papers: list, timeout: Optional[int] = None, language: str = 'en') -> str:
        """
        多维度评估论文
        
        Args:
            structured_info: 结构化的论文信息
            innovation_analysis: 创新点分析结果
            related_papers: 相关论文列表
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            评估结果文本
        """
        timeout = timeout or self.config.EVALUATION_TIMEOUT
        
        try:
            # 格式化相关信息
            info_text = self._format_structured_info(structured_info)
            related_text = self._format_related_papers(related_papers)
            
            prompt = get_evaluation_prompt(info_text, innovation_analysis, related_text, language=language)
            
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
            return f"评估失败: {str(e)}"

    def generate_review(self, structured_info: Dict[str, str], evaluation: str, innovation_analysis: str, timeout: Optional[int] = None, language: str = 'en') -> str:
        """
        生成评阅报告
        
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
        
        try:
            # 格式化相关信息
            info_text = self._format_structured_info(structured_info)
            
            prompt = get_review_generation_prompt(info_text, evaluation, innovation_analysis, language=language)
            
            # 使用推理模型生成评阅报告
            response = self.llm_client.get_response(
                prompt,
                use_reasoning_model=True,
                temperature=0.5,
                timeout=timeout
            )
            
            return response
        except Exception as e:
            print(f"⚠️  评阅报告生成失败: {e}")
            return self._generate_fallback_review(structured_info, evaluation, innovation_analysis, language=language)

    def _generate_fallback_review(self, structured_info: Dict[str, str], evaluation: str, innovation_analysis: str, language: str = 'en') -> str:
        """生成备用评阅报告（当LLM生成失败时）"""
        title = structured_info.get("Title", "Unknown Paper")
        abstract = structured_info.get("Abstract", "No abstract available.")
        
        if language == 'zh':
            return f"""# 摘要（Summary）

本文研究了{title}。{abstract[:200]}...

# 优点（Strengths）

- 论文解决了一个重要的研究问题。
- 方法论看起来合理。

# 缺点/关注点（Weaknesses / Concerns）

- 需要进一步分析以评估技术质量。
- 可能需要额外的实验验证。

# 给作者的问题（Questions for Authors）

1. 您能否提供更多关于实验设置的细节？
2. 这项工作与现有方法相比如何？

# 评分（Score）

- 总体（Overall）: 6/10
- 新颖性（Novelty）: 6/10
- 技术质量（Technical Quality）: 6/10
- 清晰度（Clarity）: 6/10
- 置信度（Confidence）: 3/5

*注：这是由于处理错误而生成的备用评阅报告。请手动审查。*"""
        else:
            return f"""# Summary

This paper presents research on {title}. {abstract[:200]}...

# Strengths

- The paper addresses an important research question.
- The methodology appears sound.

# Weaknesses / Concerns

- Further analysis needed to assess technical quality.
- Additional experimental validation may be required.

# Questions for Authors

1. Could you provide more details on the experimental setup?
2. How does this work compare to existing approaches?

# Score

- Overall: 6/10
- Novelty: 6/10
- Technical Quality: 6/10
- Clarity: 6/10
- Confidence: 3/5

*Note: This is a fallback review generated due to processing errors. Please review manually.*"""

    def _format_structured_info(self, structured_info: Dict[str, str]) -> str:
        """格式化结构化信息为文本"""
        parts = []
        for key, value in structured_info.items():
            if key not in ["raw_text", "raw_response", "error"] and value:
                parts.append(f"{key}:\n{value}\n")
        return "\n".join(parts)

    def _format_related_papers(self, related_papers: list) -> str:
        """格式化相关论文为文本"""
        if not related_papers:
            return "No related papers found."
        
        parts = []
        # 处理可能是元组列表的情况
        papers_to_format = related_papers
        if related_papers and isinstance(related_papers[0], tuple):
            papers_to_format = [paper for paper, _ in related_papers]
        
        for i, paper in enumerate(papers_to_format[:5], 1):
            if isinstance(paper, dict):
                title = paper.get('title', 'N/A')
                abstract = paper.get('abstract', 'N/A')
                parts.append(f"Paper {i}:\nTitle: {title}\nAbstract: {abstract}\n")
        
        return "\n".join(parts)

    def review(self, structured_info: Dict[str, str], innovation_analysis: str, related_papers: list, timeout: Optional[int] = None, language: str = 'en') -> str:
        """
        完整的评阅流程
        
        Args:
            structured_info: 结构化的论文信息
            innovation_analysis: 创新点分析结果
            related_papers: 相关论文列表
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            Markdown格式的评阅报告
        """
        try:
            # 1. 多维度评估
            evaluation = self.evaluate(structured_info, innovation_analysis, related_papers, timeout, language=language)
            
            # 2. 生成评阅报告
            review = self.generate_review(structured_info, evaluation, innovation_analysis, timeout, language=language)
            
            return review
        except Exception as e:
            print(f"⚠️  评阅流程失败: {e}")
            return self._generate_fallback_review(structured_info, "", innovation_analysis, language=language)

