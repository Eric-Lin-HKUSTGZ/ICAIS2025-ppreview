import requests
import time
import numpy as np
from typing import List, Dict, Optional
from config import Config
from embedding_client import EmbeddingClient


class PaperRetriever:
    """论文检索器 - 基于Semantic Scholar API"""

    def __init__(self):
        self.config = Config
        self.embedding_client = None
        self._init_embedding_client()

    def _init_embedding_client(self):
        """初始化embedding客户端"""
        try:
            self.embedding_client = EmbeddingClient()
        except Exception as e:
            print(f"⚠️  Embedding客户端初始化失败: {e}，将跳过语义重排序")
            self.embedding_client = None

    def get_newest_paper(self, query: str, max_results: Optional[int] = None, max_retries: Optional[int] = None) -> List[Dict]:
        """获取最新论文"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        max_retries = max_retries or self.config.SEMANTIC_SCHOLAR_MAX_RETRIES

        url = "http://api.semanticscholar.org/graph/v1/paper/search/bulk"
        params = {"query": query, "fields": "title,abstract,paperId", "sort": "publicationDate:desc"}

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.config.SEMANTIC_SCHOLAR_TIMEOUT)
                data = response.json()

                if 'data' in data:
                    papers = data['data'][:max_results] if data['data'] else []
                    if papers:
                        return papers
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                    continue
                else:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                    continue
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 5)
                    time.sleep(wait_time)
                    continue
                else:
                    return []
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 5)
                    time.sleep(wait_time)
                    continue
                else:
                    return []

        return []

    def get_highly_cited_paper(self, query: str, max_results: Optional[int] = None, max_retries: Optional[int] = None) -> List[Dict]:
        """获取高引用论文"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        max_retries = max_retries or self.config.SEMANTIC_SCHOLAR_MAX_RETRIES

        url = "http://api.semanticscholar.org/graph/v1/paper/search/bulk"
        params = {"query": query, "fields": "title,abstract,paperId", "sort": "citationCount:desc"}

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.config.SEMANTIC_SCHOLAR_TIMEOUT)
                data = response.json()

                if 'data' in data:
                    papers = data['data'][:max_results] if data['data'] else []
                    if papers:
                        return papers
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                    continue
                else:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                    continue
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 5)
                    time.sleep(wait_time)
                    continue
                else:
                    return []

        return []

    def get_relevant_paper(self, query: str, max_results: Optional[int] = None, max_retries: Optional[int] = None) -> List[Dict]:
        """获取相关论文"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        max_retries = max_retries or self.config.SEMANTIC_SCHOLAR_MAX_RETRIES

        url = "http://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": query, "fields": "title,abstract,paperId"}

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.config.SEMANTIC_SCHOLAR_TIMEOUT)
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                        continue
                    return []
                
                try:
                    data = response.json()
                except ValueError:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                        continue
                    return []

                if 'data' in data:
                    papers = data['data'][:max_results] if data['data'] else []
                    if papers:
                        return papers
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                    continue
                else:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 5)
                        time.sleep(wait_time)
                    continue
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 5)
                    time.sleep(wait_time)
                    continue
                else:
                    return []

        return []

    def merge_and_deduplicate(self, results: Dict[str, List[Dict]]) -> List[Dict]:
        """融合和去重论文"""
        seen_ids = set()
        all_papers = []

        for paper_list in results.values():
            for paper in paper_list:
                paper_id = paper.get('paperId') or paper.get('title', '')
                if paper_id and paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    all_papers.append(paper)

        return all_papers

    def rerank_by_similarity(self, papers: List[Dict], background_embedding: np.ndarray, background_text: str) -> List[Dict]:
        """基于语义相似度重排序论文"""
        if not self.embedding_client or len(papers) == 0:
            return papers

        try:
            paper_texts = []
            for paper in papers:
                abstract = paper.get('abstract', '') or ''
                title = paper.get('title', '') or ''
                text = f"{title} {abstract}".strip()
                paper_texts.append(text if text else " ")

            paper_embeddings = self.embedding_client.encode(paper_texts, show_progress_bar=False)
            
            if paper_embeddings.ndim == 1:
                paper_embeddings = paper_embeddings.reshape(1, -1)

            similarities = []
            for paper_emb in paper_embeddings:
                similarity = np.dot(background_embedding, paper_emb) / (
                    np.linalg.norm(background_embedding) * np.linalg.norm(paper_emb) + 1e-8
                )
                similarities.append(similarity)

            sorted_papers = sorted(
                zip(papers, similarities),
                key=lambda x: x[1],
                reverse=True
            )

            return [paper for paper, _ in sorted_papers]

        except Exception as e:
            print(f"⚠️  语义重排序失败: {e}，返回原始顺序")
            return papers

    def hybrid_retrieve(self, query_text: str, keywords: List[str]) -> List[Dict]:
        """
        混合检索策略 - 仅使用Semantic Scholar API
        """
        if len(keywords) == 1:
            query = keywords[0]
        else:
            query = " | ".join(f'"{item}"' for item in keywords)

        import concurrent.futures

        newest_papers = []
        highly_cited_papers = []
        relevant_papers = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_newest = executor.submit(self.get_newest_paper, query)
            future_highly_cited = executor.submit(self.get_highly_cited_paper, query)
            future_relevant = executor.submit(self.get_relevant_paper, query)

            try:
                newest_papers = future_newest.result(timeout=120)
            except Exception:
                newest_papers = []

            try:
                highly_cited_papers = future_highly_cited.result(timeout=120)
            except Exception:
                highly_cited_papers = []

            try:
                relevant_papers = future_relevant.result(timeout=120)
            except Exception:
                relevant_papers = []

        results = {
            "newest_papers": newest_papers or [],
            "highly_cited_papers": highly_cited_papers or [],
            "relevant_papers": relevant_papers or []
        }
        all_papers = self.merge_and_deduplicate(results)

        if not all_papers:
            return []

        if self.embedding_client:
            try:
                background_embedding = self.embedding_client.encode(query_text, show_progress_bar=False)
                if background_embedding is not None and len(background_embedding) > 0:
                    all_papers = self.rerank_by_similarity(all_papers, background_embedding, query_text)
            except Exception as e:
                print(f"⚠️  语义重排序失败: {e}，使用原始顺序")

        return all_papers[:self.config.MAX_TOTAL_PAPERS]

