"""
论文分析模块 - 关键信息提取、查询构建、语义相似度分析、创新点识别
"""
from typing import Dict, List, Optional, Tuple
import numpy as np
from llm_client import LLMClient
from embedding_client import EmbeddingClient
from retriever import PaperRetriever
from prompt_template import get_keyword_extraction_prompt, get_innovation_analysis_prompt
from config import Config


class PaperAnalyzer:
    """论文分析器"""

    def __init__(self, llm_client: LLMClient, embedding_client: EmbeddingClient, retriever: PaperRetriever):
        """
        初始化论文分析器
        
        Args:
            llm_client: LLM客户端实例
            embedding_client: Embedding客户端实例
            retriever: 论文检索器实例
        """
        self.llm_client = llm_client
        self.embedding_client = embedding_client
        self.retriever = retriever
        self.config = Config

    def extract_keywords(self, structured_info: Dict[str, str], timeout: Optional[int] = None) -> List[str]:
        """
        提取论文关键词
        
        Args:
            structured_info: 结构化的论文信息
            timeout: 超时时间（秒）
        
        Returns:
            关键词列表
        """
        timeout = timeout or self.config.KEY_EXTRACTION_TIMEOUT
        
        try:
            # 构建结构化信息文本
            info_text = self._format_structured_info(structured_info)
            
            prompt = get_keyword_extraction_prompt(info_text)
            
            response = self.llm_client.get_response(
                prompt,
                use_reasoning_model=False,
                temperature=0.3,
                timeout=timeout
            )
            
            # 解析关键词
            keywords = [kw.strip().lower() for kw in response.split(',')]
            keywords = [kw for kw in keywords if kw]  # 过滤空字符串
            
            # 限制关键词数量
            keywords = keywords[:5]
            
            return keywords if keywords else []
        except Exception as e:
            print(f"⚠️  关键词提取失败: {e}")
            # 从结构化信息中提取备用关键词
            return self._extract_fallback_keywords(structured_info)

    def _extract_fallback_keywords(self, structured_info: Dict[str, str]) -> List[str]:
        """备用关键词提取方法"""
        keywords = []
        
        # 从Keywords字段提取
        if "Keywords" in structured_info:
            kw_text = structured_info["Keywords"]
            keywords.extend([kw.strip().lower() for kw in kw_text.split(',')[:3]])
        
        # 从Title提取
        if "Title" in structured_info:
            title = structured_info["Title"]
            # 简单提取：取前几个重要词
            words = title.lower().split()[:3]
            keywords.extend(words)
        
        return list(set(keywords))[:5]  # 去重并限制数量

    def build_query(self, keywords: List[str], structured_info: Dict[str, str]) -> str:
        """
        构建检索查询字符串
        
        Args:
            keywords: 关键词列表
            structured_info: 结构化的论文信息
        
        Returns:
            查询字符串
        """
        if not keywords:
            # 如果没有关键词，使用标题
            title = structured_info.get("Title", "")
            if title:
                return title[:100]  # 限制长度
        
        if len(keywords) == 1:
            return keywords[0]
        else:
            # 使用 | 分隔多个关键词
            return " | ".join(f'"{kw}"' for kw in keywords[:3])  # 最多使用3个关键词

    def retrieve_related_papers(self, query: str, keywords: List[str], timeout: Optional[int] = None) -> List[Dict]:
        """
        检索相关论文
        
        Args:
            query: 查询字符串
            keywords: 关键词列表
            timeout: 超时时间（秒）
        
        Returns:
            相关论文列表
        """
        timeout = timeout or self.config.RETRIEVAL_TIMEOUT
        
        try:
            # 使用混合检索策略
            papers = self.retriever.hybrid_retrieve(query, keywords)
            return papers[:10]  # 最多返回10篇
        except Exception as e:
            print(f"⚠️  论文检索失败: {e}")
            return []

    def calculate_semantic_similarity(self, paper_text: str, related_papers: List[Dict]) -> List[Tuple[Dict, float]]:
        """
        计算语义相似度
        
        Args:
            paper_text: 待评论文本
            related_papers: 相关论文列表
        
        Returns:
            (论文, 相似度) 元组列表
        """
        if not related_papers:
            return []
        
        try:
            # 计算待评论文的embedding
            paper_embedding = self.embedding_client.encode(paper_text, show_progress_bar=False)
            
            if paper_embedding is None or len(paper_embedding) == 0:
                return [(paper, 0.0) for paper in related_papers]
            
            # 计算相关论文的embedding
            related_texts = []
            for paper in related_papers:
                title = paper.get('title', '') or ''
                abstract = paper.get('abstract', '') or ''
                text = f"{title} {abstract}".strip()
                related_texts.append(text if text else " ")
            
            related_embeddings = self.embedding_client.encode(related_texts, show_progress_bar=False)
            
            if related_embeddings is None or len(related_embeddings) == 0:
                return [(paper, 0.0) for paper in related_papers]
            
            # 确保是2D数组
            if related_embeddings.ndim == 1:
                related_embeddings = related_embeddings.reshape(1, -1)
            
            # 计算相似度
            similarities = []
            for i, related_emb in enumerate(related_embeddings):
                similarity = np.dot(paper_embedding, related_emb) / (
                    np.linalg.norm(paper_embedding) * np.linalg.norm(related_emb) + 1e-8
                )
                similarities.append((related_papers[i], float(similarity)))
            
            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities
        except Exception as e:
            print(f"⚠️  语义相似度计算失败: {e}")
            return [(paper, 0.0) for paper in related_papers]

    def analyze_innovation(self, structured_info: Dict[str, str], related_papers: List[Dict], timeout: Optional[int] = None) -> str:
        """
        分析创新点
        
        Args:
            structured_info: 结构化的论文信息
            related_papers: 相关论文列表
            timeout: 超时时间（秒）
        
        Returns:
            创新点分析文本
        """
        timeout = timeout or self.config.SEMANTIC_ANALYSIS_TIMEOUT
        
        try:
            # 格式化相关信息
            info_text = self._format_structured_info(structured_info)
            related_text = self._format_related_papers(related_papers)
            
            prompt = get_innovation_analysis_prompt(info_text, related_text)
            
            response = self.llm_client.get_response(
                prompt,
                use_reasoning_model=True,  # 使用推理模型进行深度分析
                temperature=0.5,
                timeout=timeout
            )
            
            return response
        except Exception as e:
            print(f"⚠️  创新点分析失败: {e}")
            return f"创新点分析失败: {str(e)}"

    def _format_structured_info(self, structured_info: Dict[str, str]) -> str:
        """格式化结构化信息为文本"""
        parts = []
        for key, value in structured_info.items():
            if key not in ["raw_text", "raw_response", "error"] and value:
                parts.append(f"{key}:\n{value}\n")
        return "\n".join(parts)

    def _format_related_papers(self, related_papers: List[Dict]) -> str:
        """格式化相关论文为文本"""
        if not related_papers:
            return "No related papers found."
        
        parts = []
        for i, paper in enumerate(related_papers[:5], 1):  # 最多5篇
            title = paper.get('title', 'N/A')
            abstract = paper.get('abstract', 'N/A')
            parts.append(f"Paper {i}:\nTitle: {title}\nAbstract: {abstract}\n")
        
        return "\n".join(parts)

    def analyze(self, structured_info: Dict[str, str], timeout: Optional[int] = None) -> Dict:
        """
        完整的论文分析流程
        
        Args:
            structured_info: 结构化的论文信息
            timeout: 超时时间（秒）
        
        Returns:
            分析结果字典，包含：
            - keywords: 关键词列表
            - query: 查询字符串
            - related_papers: 相关论文列表
            - semantic_similarities: 语义相似度列表
            - innovation_analysis: 创新点分析
        """
        result = {
            "keywords": [],
            "query": "",
            "related_papers": [],
            "semantic_similarities": [],
            "innovation_analysis": ""
        }
        
        try:
            # 1. 提取关键词
            keywords = self.extract_keywords(structured_info, timeout)
            result["keywords"] = keywords
            
            # 2. 构建查询
            query = self.build_query(keywords, structured_info)
            result["query"] = query
            
            # 3. 检索相关论文
            related_papers = self.retrieve_related_papers(query, keywords, timeout)
            result["related_papers"] = related_papers
            
            # 4. 计算语义相似度
            paper_text = self._format_structured_info(structured_info)
            semantic_similarities = self.calculate_semantic_similarity(paper_text, related_papers)
            result["semantic_similarities"] = semantic_similarities
            
            # 5. 分析创新点
            innovation_analysis = self.analyze_innovation(structured_info, related_papers, timeout)
            result["innovation_analysis"] = innovation_analysis
            
        except Exception as e:
            print(f"⚠️  论文分析失败: {e}")
            result["error"] = str(e)
        
        return result

