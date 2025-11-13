import requests
import time
from typing import Optional
from config import Config


class LLMClient:
    """LLM客户端 - 支持自定义API端点"""

    def __init__(self, llm: Optional[str] = None, **kwargs):
        """
        初始化LLM客户端

        Args:
            llm: 模型名称
            **kwargs: 其他参数
        """
        self.config = Config

        # 验证配置
        if not self.config.validate_config():
            raise ValueError("LLM配置验证失败")

        # 设置模型
        self.llm = llm or self.config.LLM_MODEL
        self.endpoint = self.config.LLM_API_ENDPOINT
        self.api_key = self.config.LLM_API_KEY

        # 设置参数
        self.temperature = kwargs.get('temperature', self.config.DEFAULT_TEMPERATURE)
        self.max_retries = kwargs.get('max_retries', self.config.MAX_RETRIES)
        self.timeout = kwargs.get('timeout', self.config.LLM_REQUEST_TIMEOUT)

    def _make_api_call(self, prompt: str) -> str:
        """使用自定义API端点调用"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.llm,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "stream": False
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.endpoint}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()
                
                # 检查响应格式
                if "choices" not in result or not result["choices"]:
                    raise Exception(f"API响应格式错误: 缺少choices字段或choices为空。响应: {result}")
                
                if "message" not in result["choices"][0] or "content" not in result["choices"][0]["message"]:
                    raise Exception(f"API响应格式错误: 缺少message或content字段。响应: {result}")
                
                content = result["choices"][0]["message"]["content"]
                if content is None:
                    raise Exception("API返回的content为None")
                
                return content

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"API超时，{wait_time}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"API调用超时，已重试{self.max_retries}次")

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"API调用失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"API调用失败: {e}")

    def get_response(self, prompt: str, use_reasoning_model: bool = False, **kwargs) -> str:
        """获取LLM响应
        
        Args:
            prompt: 提示词
            use_reasoning_model: 是否使用推理模型，如果为True则使用Config.LLM_REASONING_MODEL
            **kwargs: 其他参数（temperature, max_retries等）
        """
        temperature = kwargs.get('temperature', self.temperature)
        max_retries = kwargs.get('max_retries', self.max_retries)

        # 临时更新参数
        original_temp = self.temperature
        original_retries = self.max_retries
        original_llm = self.llm
        self.temperature = temperature
        self.max_retries = max_retries
        
        # 如果使用推理模型，临时替换模型名称
        if use_reasoning_model:
            self.llm = self.config.LLM_REASONING_MODEL

        try:
            return self._make_api_call(prompt)
        finally:
            # 恢复原始参数
            self.temperature = original_temp
            self.max_retries = original_retries
            self.llm = original_llm

    def validate_config(self) -> bool:
        """验证配置是否正确"""
        try:
            # 尝试一个简单的请求来验证配置
            test_response = self.get_response("Hello", max_retries=1)
            return True
        except Exception as e:
            print(f"配置验证失败: {e}")
            return False

    def get_config_info(self) -> dict:
        """获取配置信息"""
        return {
            "model": self.llm,
            "endpoint": self.endpoint,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "timeout": self.timeout
        }

