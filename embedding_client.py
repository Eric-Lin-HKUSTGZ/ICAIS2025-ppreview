"""
Embedding客户端 - 通过API调用embedding模型
"""
from openai import OpenAI
import os
import time
import json
from typing import List, Optional, Union
import numpy as np
import requests
from config import Config


class EmbeddingClient:
    """Embedding客户端 - 通过API调用embedding模型"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化Embedding客户端
        
        Args:
            api_key: API密钥（优先从环境变量读取）
            model: 嵌入模型名称（优先从环境变量读取）
            base_url: API基础URL（优先从环境变量读取）
        """
        self.config = Config
        
        # 优先从环境变量读取配置
        self.base_url = base_url or self.config.LLM_API_ENDPOINT
        self.api_key = api_key or self.config.LLM_API_KEY
        self.model = model or self.config.EMBEDDING_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("API密钥未找到，请设置 SCI_MODEL_API_KEY 环境变量")
        
        if not self.base_url:
            raise ValueError("API端点未找到，请设置 SCI_MODEL_BASE_URL 环境变量")
        
        # 确保base_url以/v1结尾（OpenAI客户端会自动添加/embeddings）
        if not self.base_url.endswith("/v1"):
            if self.base_url.endswith("/v1/embeddings"):
                self.base_url = self.base_url.replace("/v1/embeddings", "/v1")
            elif self.base_url.endswith("/"):
                self.base_url = self.base_url.rstrip("/") + "/v1"
            else:
                self.base_url = self.base_url.rstrip("/") + "/v1"
        
        # 创建OpenAI客户端
        try:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                max_retries=0
            )
        except Exception as e:
            print(f"⚠️  OpenAI客户端初始化警告: {e}，尝试使用默认配置")
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )
        
        print(f"✅ Embedding客户端初始化成功:")
        print(f"  API端点: {self.base_url}")
        print(f"  模型: {self.model}")
    
    def encode(self, texts: Union[List[str], str], show_progress_bar: bool = False, device: Optional[str] = None) -> np.ndarray:
        """
        获取文本的向量嵌入
        
        Args:
            texts: 输入文本（字符串或字符串列表）
            show_progress_bar: 是否显示进度条（API调用时忽略）
            device: 设备（API调用时忽略）
        
        Returns:
            向量数组，单个文本返回1D数组，多个文本返回2D数组
        """
        # 处理单个文本
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False
        
        # 过滤空文本
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            if single_text:
                return np.array([])
            else:
                return np.array([[]] * len(texts))
        
        # 批量获取embedding
        embeddings = []
        for i, text in enumerate(texts):
            if text and text.strip():
                embedding = self._get_embedding(text)
                if embedding is not None:
                    embeddings.append(embedding)
                else:
                    embeddings.append([0.0] * 1024)
            else:
                embeddings.append([0.0] * 1024)
        
        # 转换为numpy数组
        embeddings_array = np.array(embeddings)
        
        # 如果是单个文本，返回1D数组
        if single_text:
            return embeddings_array[0] if len(embeddings_array) > 0 else np.array([])
        
        return embeddings_array
    
    def _get_embedding(self, text: str, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[List[float]]:
        """
        获取单个文本的向量嵌入
        
        Args:
            text: 输入文本
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒），会指数增长
        
        Returns:
            向量列表，失败时返回None
        """
        if not text or not text.strip():
            return None
        
        for attempt in range(max_retries):
            try:
                try:
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=text,
                        encoding_format="float"
                    )
                except (ValueError, TypeError) as pydantic_error:
                    error_msg = str(pydantic_error)
                    if "leading underscores" in error_msg or "pydantic" in error_msg.lower():
                        print(f"⚠️  检测到 Pydantic 兼容性问题，尝试使用原始 HTTP 请求...")
                        return self._get_embedding_via_http(text, max_retries - attempt, retry_delay)
                    else:
                        raise
                
                if not hasattr(response, 'data') or not response.data:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                    return None
                
                embedding_obj = response.data[0]
                if not hasattr(embedding_obj, 'embedding'):
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                    return None
                
                embedding = embedding_obj.embedding
                
                if not embedding or not isinstance(embedding, list) or len(embedding) == 0:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                    return None
                
                return embedding
                
            except Exception as e:
                error_msg = str(e)
                if "leading underscores" in error_msg or "pydantic" in error_msg.lower():
                    if attempt < max_retries - 1:
                        print(f"⚠️  检测到 Pydantic 兼容性问题，尝试使用原始 HTTP 请求...")
                        return self._get_embedding_via_http(text, max_retries - attempt, retry_delay)
                    else:
                        print(f"⚠️  Embedding API调用最终失败（Pydantic兼容性问题）: {e}")
                        return None
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"⚠️  Embedding API调用失败: {e}，{wait_time:.1f}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  Embedding API调用最终失败: {e}")
                    return None
        
        return None
    
    def _get_embedding_via_http(self, text: str, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[List[float]]:
        """
        使用原始 HTTP 请求获取 embedding（用于避免 Pydantic 兼容性问题）
        """
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": text,
            "encoding_format": "float"
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if 'data' in data and len(data['data']) > 0:
                    embedding = data['data'][0].get('embedding')
                    if embedding and isinstance(embedding, list) and len(embedding) > 0:
                        return embedding
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                return None
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"⚠️  HTTP Embedding API调用失败: {e}，{wait_time:.1f}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  HTTP Embedding API调用最终失败: {e}")
                    return None
        
        return None

