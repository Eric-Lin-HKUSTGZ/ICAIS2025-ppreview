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
    
    CORE_SECTION_KEYS = [
        "Abstract",
        "Introduction",
        "Methodology",
        "Experiments",
        "Results",
        "Conclusion",
        "Core Contributions",
        "Technical Approach"
    ]
    FALLBACK_SNIPPET_LENGTH = 1800

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

    def extract_keywords(self, structured_info: Dict[str, str], timeout: Optional[int] = None, language: str = 'en') -> List[str]:
        """
        提取论文关键词
        
        Args:
            structured_info: 结构化的论文信息
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            关键词列表
        """
        timeout = timeout or self.config.KEY_EXTRACTION_TIMEOUT
        
        try:
            # 构建结构化信息文本
            info_text = self._format_structured_info(structured_info)
            
            prompt = get_keyword_extraction_prompt(info_text, language=language)
            
            # 使用推理模型进行深度理解，提升关键词提取的准确性
            response = self.llm_client.get_response(
                prompt,
                use_reasoning_model=True,
                temperature=0.3,
                timeout=timeout
            )
            
            # 解析关键词
            import re
            # 移除可能的前缀提示文本（如"现在请提取关键词："等）
            response_clean = response.strip()
            # 查找最后一个冒号或换行符后的内容（通常是实际的关键词列表）
            if ':' in response_clean:
                # 尝试找到最后一个冒号后的内容
                parts = response_clean.split(':')
                if len(parts) > 1:
                    response_clean = parts[-1].strip()
            # 移除可能的前缀文本（如"关键词："、"Keywords:"等）
            response_clean = re.sub(r'^(关键词|keywords|keyword)[:：]?\s*', '', response_clean, flags=re.IGNORECASE)
            
            # 按逗号分割
            raw_keywords = [kw.strip() for kw in response_clean.split(',')]
            # 只保留包含英文字母的关键词（过滤掉纯中文或其他非英文内容）
            keywords = []
            # 定义一些明显与任务相关的通用词，如果提取到这些词，可能是LLM误解了任务
            task_related_generic_words = {
                'keyword extraction', 'keyword', 'keywords', 'extraction',
                'natural language processing', 'nlp', 'text mining', 'text analysis',
                'information retrieval', 'information extraction', 'data mining'
            }
            
            for kw in raw_keywords:
                kw_lower = kw.lower().strip()
                # 只保留包含至少一个英文字母的关键词
                if kw_lower and re.search(r'[a-zA-Z]', kw_lower):
                    # 提取英文部分（去除可能的中文说明）
                    english_part = re.sub(r'[^\x00-\x7F]+', '', kw_lower).strip()
                    # 移除可能的标点符号
                    english_part = re.sub(r'^[^\w]+|[^\w]+$', '', english_part)
                    if english_part:
                        # 检查是否是任务相关的通用词（如果只有这些词，可能是误解了任务）
                        # 但如果关键词列表中有其他具体词，保留这些词作为备选
                        keywords.append(english_part)
            
            # 限制关键词数量
            keywords = keywords[:4]
            
            # 如果提取到的关键词都是任务相关的通用词，说明LLM可能误解了任务，使用备用方法
            if keywords and all(kw in task_related_generic_words for kw in keywords):
                print(f"⚠️  检测到可能提取了任务相关的通用词: {keywords}，使用备用方法重新提取")
                # 使用备用方法从论文内容中提取关键词
                fallback_keywords = self._extract_fallback_keywords(structured_info)
                if fallback_keywords:
                    return fallback_keywords
                # 如果备用方法也失败，返回原始关键词（总比没有好）
            
            return keywords if keywords else []
        except Exception as e:
            print(f"⚠️  关键词提取失败: {e}")
            # 从结构化信息中提取备用关键词
            return self._extract_fallback_keywords(structured_info)

    def _extract_fallback_keywords(self, structured_info: Dict[str, str]) -> List[str]:
        """备用关键词提取方法 - 只提取英文关键词（用于论文检索）"""
        import re
        keywords = []
        
        # 从Keywords字段提取（优先）
        if "Keywords" in structured_info:
            kw_text = structured_info["Keywords"]
            # 支持中英文关键词，按逗号、分号或空格分隔
            kw_list = re.split(r'[,;，；\s]+', kw_text)
            # 只保留英文关键词（包含至少一个英文字母）
            english_kws = [kw.strip().lower() for kw in kw_list if kw.strip() and re.search(r'[a-zA-Z]', kw.strip())]
            keywords.extend(english_kws[:3])
        
        # 从Abstract提取英文关键词（优先于Title，因为Abstract通常包含更多技术术语）
        if "Abstract" in structured_info:
            abstract = structured_info["Abstract"]
            # 提取英文单词（至少4个字符，排除停用词）
            words = re.findall(r'\b[a-zA-Z]{4,}\b', abstract.lower())
            stop_words = {'this', 'that', 'these', 'those', 'with', 'from', 'have', 'been', 'will', 'would', 'could', 'should', 'might', 'must', 'paper', 'study', 'research', 'method', 'approach', 'propose', 'present', 'show', 'demonstrate', 'result', 'experiment', 'evaluation', 'performance', 'improve', 'better', 'compared', 'previous', 'existing', 'novel', 'new', 'using', 'based', 'through', 'which', 'where', 'while', 'when', 'their', 'there', 'these', 'those'}
            words = [w for w in words if w not in stop_words]
            # 优先选择较长的词（通常是技术术语）
            words = sorted(words, key=len, reverse=True)
            keywords.extend(words[:3])
        
        # 从Title提取（如果关键词还不够）
        if len(keywords) < 2 and "Title" in structured_info:
            title = structured_info["Title"]
            # 只提取英文单词
            words = re.findall(r'\b[a-zA-Z]{4,}\b', title.lower())
            stop_words = {'this', 'that', 'with', 'from', 'paper', 'study', 'research', 'method', 'approach', 'novel', 'new', 'using', 'based'}
            words = [w for w in words if w not in stop_words]
            keywords.extend(words[:2])
        
        # 如果还是没有足够的关键词，尝试从Abstract提取更多
        if len(keywords) < 2 and "Abstract" in structured_info:
            abstract = structured_info["Abstract"]
            # 提取所有英文单词（至少3个字符）
            words = re.findall(r'\b[a-zA-Z]{3,}\b', abstract.lower())
            stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'this', 'that', 'with', 'from', 'have', 'been', 'will', 'would', 'could', 'should', 'might', 'must', 'paper', 'study', 'research', 'method', 'approach', 'propose', 'present', 'show', 'demonstrate', 'result', 'experiment', 'evaluation', 'performance', 'improve', 'better', 'compared', 'previous', 'existing', 'novel', 'new', 'using', 'based', 'through', 'which', 'where', 'while', 'when', 'their', 'there', 'these', 'those'}
            words = [w for w in words if w not in stop_words]
            keywords.extend(words[:2])
        
        # 去重并限制数量（最多4个）
        keywords = list(dict.fromkeys(keywords))[:4]  # 使用dict.fromkeys保持顺序并去重
        return keywords

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

    def analyze_innovation(self, structured_info: Dict[str, str], related_papers: List[Dict], timeout: Optional[int] = None, language: str = 'en') -> str:
        """
        分析创新点
        
        Args:
            structured_info: 结构化的论文信息
            related_papers: 相关论文列表
            timeout: 超时时间（秒）
            language: 语言，'zh'表示中文，'en'表示英文
        
        Returns:
            创新点分析文本
        """
        timeout = timeout or self.config.SEMANTIC_ANALYSIS_TIMEOUT
        
        try:
            # 格式化相关信息
            info_text = self._format_structured_info(structured_info)
            related_text = self._format_related_papers(related_papers)
            
            prompt = get_innovation_analysis_prompt(info_text, related_text, language=language)
            
            response = self.llm_client.get_response(
                prompt,
                use_reasoning_model=True,  # 使用推理模型进行深度分析
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

    def _format_structured_info(self, structured_info: Dict[str, str]) -> str:
        """格式化结构化信息为文本，必要时回退到原始文本片段"""
        parts = []
        for key, value in structured_info.items():
            if key not in ["raw_text", "raw_response", "error"] and value:
                parts.append(f"{key}:\n{value}\n")
        
        raw_text = structured_info.get("raw_text", "")
        if raw_text:
            snippet = raw_text[:self.FALLBACK_SNIPPET_LENGTH].strip()
            if snippet:
                parts.append("Raw PDF Excerpt:\n" + snippet + ("\n...\n" if len(raw_text) > len(snippet) else "\n"))
        
        if not parts:
            error_msg = structured_info.get("error") or "No structured sections could be extracted."
            minimal = raw_text[:400].strip() if raw_text else "Raw PDF text unavailable."
            parts.append(f"[Parser Warning] {error_msg}\n\n{minimal}")
        
        return "\n".join(parts)
    
    def has_core_content(self, structured_info: Dict[str, str]) -> bool:
        """判断结构化信息是否包含核心章节"""
        return any(structured_info.get(key) for key in self.CORE_SECTION_KEYS)

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

