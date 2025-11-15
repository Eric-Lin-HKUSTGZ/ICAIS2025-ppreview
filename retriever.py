import requests
import time
import numpy as np
from typing import List, Dict, Optional
from config import Config
from embedding_client import EmbeddingClient


class PaperRetriever:
    """论文检索器 - 基于Semantic Scholar API，失败时fallback到OpenAlex"""

    def __init__(self):
        self.config = Config
        self.embedding_client = None
        print("🔄 正在初始化论文检索器...")
        self._init_embedding_client()
        # OpenAlex API headers（建议包含邮箱，但非必需）
        self.openalex_headers = {
            'User-Agent': 'ICAIS2025-PaperReview/1.0 ( https://github.com/your-repo )'
        }
        print("✅ 论文检索器初始化成功")

    def _init_embedding_client(self):
        """初始化embedding客户端"""
        try:
            print(f"🔄 正在初始化Embedding客户端: {self.config.EMBEDDING_MODEL_NAME}...")
            self.embedding_client = EmbeddingClient()
            print(f"✅ Embedding客户端初始化成功")
        except Exception as e:
            print(f"⚠️  Embedding客户端初始化失败: {e}，将跳过语义重排序")
            self.embedding_client = None

    def _convert_openalex_to_semanticscholar_format(self, openalex_work: Dict) -> Dict:
        """将OpenAlex的work格式转换为Semantic Scholar格式"""
        # 提取标题
        title = openalex_work.get('title', '') or ''
        
        # 提取摘要
        abstract = ''
        # OpenAlex的摘要可能在abstract字段中（字符串）或abstract_inverted_index中
        if 'abstract_inverted_index' in openalex_work and openalex_work['abstract_inverted_index']:
            try:
                inverted_index = openalex_work['abstract_inverted_index']
                # 创建位置到单词的映射
                pos_to_word = {}
                for word, positions in inverted_index.items():
                    for pos in positions:
                        pos_to_word[pos] = word
                # 按位置排序并拼接
                if pos_to_word:
                    sorted_positions = sorted(pos_to_word.keys())
                    abstract = ' '.join([pos_to_word[pos] for pos in sorted_positions])
            except Exception as e:
                print(f"⚠️  转换 OpenAlex 摘要失败: {e}")
                abstract = ''
        elif 'abstract' in openalex_work and isinstance(openalex_work['abstract'], str):
            abstract = openalex_work['abstract']
        # 如果没有abstract，使用空字符串
        if not abstract:
            abstract = ''
        
        # 提取paperId（使用OpenAlex的ID，去掉URL前缀）
        paper_id = openalex_work.get('id', '')
        if paper_id and isinstance(paper_id, str) and paper_id.startswith('https://openalex.org/'):
            paper_id = paper_id.replace('https://openalex.org/', '')
        elif not paper_id:
            # 如果没有ID，使用标题作为ID（用于去重）
            paper_id = title
        
        return {
            'paperId': paper_id,
            'title': title,
            'abstract': abstract
        }

    def _get_papers_from_openalex(self, query: str, sort: str, max_results: int, timeout: int = 30) -> List[Dict]:
        """从OpenAlex获取论文（内部方法）"""
        url = "https://api.openalex.org/works"
        
        # 清理查询字符串：移除引号和竖线，保留连字符和其他字符
        # 将 "keyword1" | "keyword2" | "keyword3" 转换为 keyword1 keyword2 keyword3
        cleaned_query = query.replace('"', '').replace(' | ', ' ').strip()
        # 清理多余的空格
        import re
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        
        params = {
            "search": cleaned_query,
            "sort": sort,
            "per_page": min(max_results, 200)  # OpenAlex最多返回200条
        }
        
        try:
            response = requests.get(
                url, 
                params=params, 
                headers=self.openalex_headers,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if 'results' in data and data['results']:
                papers = []
                for work in data['results'][:max_results]:
                    paper = self._convert_openalex_to_semanticscholar_format(work)
                    # 只添加有标题的论文
                    if paper.get('title', '').strip():
                        papers.append(paper)
                return papers
            return []
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"❌ OpenAlex 检索失败 (400 Bad Request): {e}")
                print(f"   请求 URL: {e.request.url}")
                try:
                    error_text = e.response.text[:200]
                    print(f"   响应内容: {error_text}...")
                except:
                    pass
            else:
                print(f"❌ OpenAlex 检索失败 (HTTP {e.response.status_code}): {e}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"⚠️  OpenAlex检索失败: {e}")
            return []
        except Exception as e:
            print(f"⚠️  OpenAlex检索异常: {e}")
            return []

    def get_newest_paper_openalex(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """使用OpenAlex获取最新论文"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        print(f"🔄 尝试使用OpenAlex获取最新论文...")
        return self._get_papers_from_openalex(query, "publication_date:desc", max_results)

    def get_highly_cited_paper_openalex(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """使用OpenAlex获取高引用论文"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        print(f"🔄 尝试使用OpenAlex获取高引用论文...")
        return self._get_papers_from_openalex(query, "cited_by_count:desc", max_results)

    def get_relevant_paper_openalex(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """使用OpenAlex获取相关论文（按相关性排序）"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        print(f"🔄 尝试使用OpenAlex获取相关论文...")
        # OpenAlex不支持"relevance"排序，使用cited_by_count作为替代（高引用通常更相关）
        return self._get_papers_from_openalex(query, "cited_by_count:desc", max_results)

    def get_newest_paper(self, query: str, max_results: Optional[int] = None, max_retries: Optional[int] = None) -> List[Dict]:
        """获取最新论文（Semantic Scholar失败时fallback到OpenAlex）"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        # 减少Semantic Scholar的重试次数，快速fallback到OpenAlex
        max_retries = min(max_retries or 2, 2)  # 最多重试2次

        url = "http://api.semanticscholar.org/graph/v1/paper/search/bulk"
        params = {"query": query, "fields": "title,abstract,paperId", "sort": "publicationDate:desc"}

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.config.SEMANTIC_SCHOLAR_TIMEOUT)
                
                # 检查HTTP状态码，特别是429错误
                if response.status_code == 429:
                    print(f"⚠️  Semantic Scholar返回429错误（请求过多），切换到OpenAlex...")
                    return self.get_newest_paper_openalex(query, max_results)
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)  # 减少等待时间
                        print(f"获取最新论文失败 (HTTP {response.status_code})，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"⚠️  Semantic Scholar获取最新论文最终失败，切换到OpenAlex...")
                        return self.get_newest_paper_openalex(query, max_results)
                
                data = response.json()

                if 'data' in data:
                    papers = data['data'][:max_results] if data['data'] else []
                    if papers:
                        return papers
                    # 如果返回空列表，继续重试
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)
                        print(f"获取最新论文返回空数据，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    continue
                else:
                    # 响应中没有'data'字段，继续重试
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)
                        print(f"获取最新论文响应格式异常，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    continue
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取最新论文超时，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取最新论文超时，切换到OpenAlex...")
                    return self.get_newest_paper_openalex(query, max_results)
            except requests.exceptions.RequestException as e:
                # 检查是否是429错误
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    print(f"⚠️  Semantic Scholar返回429错误（请求过多），切换到OpenAlex...")
                    return self.get_newest_paper_openalex(query, max_results)
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取最新论文失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取最新论文最终失败，切换到OpenAlex...")
                    return self.get_newest_paper_openalex(query, max_results)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取最新论文失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取最新论文最终失败，切换到OpenAlex...")
                    return self.get_newest_paper_openalex(query, max_results)

        # 如果所有重试都失败，fallback到OpenAlex
        print(f"⚠️  Semantic Scholar获取最新论文失败，切换到OpenAlex...")
        return self.get_newest_paper_openalex(query, max_results)

    def get_highly_cited_paper(self, query: str, max_results: Optional[int] = None, max_retries: Optional[int] = None) -> List[Dict]:
        """获取高引用论文（Semantic Scholar失败时fallback到OpenAlex）"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        # 减少Semantic Scholar的重试次数，快速fallback到OpenAlex
        max_retries = min(max_retries or 2, 2)  # 最多重试2次

        url = "http://api.semanticscholar.org/graph/v1/paper/search/bulk"
        params = {"query": query, "fields": "title,abstract,paperId", "sort": "citationCount:desc"}

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.config.SEMANTIC_SCHOLAR_TIMEOUT)
                
                # 检查HTTP状态码，特别是429错误
                if response.status_code == 429:
                    print(f"⚠️  Semantic Scholar返回429错误（请求过多），切换到OpenAlex...")
                    return self.get_highly_cited_paper_openalex(query, max_results)
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)  # 减少等待时间
                        print(f"获取高引用论文失败 (HTTP {response.status_code})，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"⚠️  Semantic Scholar获取高引用论文最终失败，切换到OpenAlex...")
                        return self.get_highly_cited_paper_openalex(query, max_results)
                
                data = response.json()

                if 'data' in data:
                    papers = data['data'][:max_results] if data['data'] else []
                    if papers:
                        return papers
                    # 如果返回空列表，继续重试
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)
                        print(f"获取高引用论文返回空数据，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    continue
                else:
                    # 响应中没有'data'字段，继续重试
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)
                        print(f"获取高引用论文响应格式异常，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    continue
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取高引用论文超时，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取高引用论文超时，切换到OpenAlex...")
                    return self.get_highly_cited_paper_openalex(query, max_results)
            except requests.exceptions.RequestException as e:
                # 检查是否是429错误
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    print(f"⚠️  Semantic Scholar返回429错误（请求过多），切换到OpenAlex...")
                    return self.get_highly_cited_paper_openalex(query, max_results)
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取高引用论文失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取高引用论文最终失败，切换到OpenAlex...")
                    return self.get_highly_cited_paper_openalex(query, max_results)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取高引用论文失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取高引用论文最终失败，切换到OpenAlex...")
                    return self.get_highly_cited_paper_openalex(query, max_results)

        # 如果所有重试都失败，fallback到OpenAlex
        print(f"⚠️  Semantic Scholar获取高引用论文失败，切换到OpenAlex...")
        return self.get_highly_cited_paper_openalex(query, max_results)

    def get_relevant_paper(self, query: str, max_results: Optional[int] = None, max_retries: Optional[int] = None) -> List[Dict]:
        """获取相关论文（Semantic Scholar失败时fallback到OpenAlex）"""
        max_results = max_results or self.config.MAX_PAPERS_PER_QUERY
        # 减少Semantic Scholar的重试次数，快速fallback到OpenAlex
        max_retries = min(max_retries or 2, 2)  # 最多重试2次

        url = "http://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": query, "fields": "title,abstract,paperId"}

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.config.SEMANTIC_SCHOLAR_TIMEOUT)
                
                # 检查HTTP状态码，特别是429错误
                if response.status_code == 429:
                    print(f"⚠️  Semantic Scholar返回429错误（请求过多），切换到OpenAlex...")
                    return self.get_relevant_paper_openalex(query, max_results)
                
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)  # 减少等待时间
                        print(f"获取相关论文失败 (HTTP {response.status_code})，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"⚠️  Semantic Scholar获取相关论文最终失败，切换到OpenAlex...")
                        return self.get_relevant_paper_openalex(query, max_results)
                
                try:
                    data = response.json()
                except ValueError:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)
                        print(f"获取相关论文JSON解析失败，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"⚠️  Semantic Scholar获取相关论文JSON解析失败，切换到OpenAlex...")
                        return self.get_relevant_paper_openalex(query, max_results)

                if 'data' in data:
                    papers = data['data'][:max_results] if data['data'] else []
                    if papers:
                        return papers
                    # 如果返回空列表，继续重试
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)
                        print(f"获取相关论文返回空数据，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    continue
                else:
                    # 响应中没有'data'字段，继续重试
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 2)
                        print(f"获取相关论文响应格式异常，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    continue
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取相关论文超时，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取相关论文超时，切换到OpenAlex...")
                    return self.get_relevant_paper_openalex(query, max_results)
            except requests.exceptions.RequestException as e:
                # 检查是否是429错误
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    print(f"⚠️  Semantic Scholar返回429错误（请求过多），切换到OpenAlex...")
                    return self.get_relevant_paper_openalex(query, max_results)
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取相关论文失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取相关论文最终失败，切换到OpenAlex...")
                    return self.get_relevant_paper_openalex(query, max_results)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 2)
                    print(f"获取相关论文失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Semantic Scholar获取相关论文最终失败，切换到OpenAlex...")
                    return self.get_relevant_paper_openalex(query, max_results)

        # 如果所有重试都失败，fallback到OpenAlex
        print(f"⚠️  Semantic Scholar获取相关论文失败，切换到OpenAlex...")
        return self.get_relevant_paper_openalex(query, max_results)

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
        混合检索策略 - 优先使用Semantic Scholar API，失败时自动fallback到OpenAlex
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

