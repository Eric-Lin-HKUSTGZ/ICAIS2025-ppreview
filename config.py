import os
from typing import Optional, Any


class ConfigMeta(type):
    """元类，用于实现类级别的__getattr__"""
    
    def __getattr__(cls, name: str) -> Any:
        """动态获取配置属性"""
        return cls._get_config_value(name)


class Config(metaclass=ConfigMeta):
    """应用配置类 - 使用元类实现延迟读取环境变量"""

    @staticmethod
    def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量"""
        return os.getenv(key, default)
    
    @staticmethod
    def _get_env_with_fallback(new_key: str, old_key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量，支持新旧变量名fallback"""
        return os.getenv(new_key) or os.getenv(old_key) or default

    @classmethod
    def _get_config_value(cls, name: str) -> Any:
        """动态获取配置属性"""
        # LLM服务配置（适配新的环境变量名称）
        if name == "LLM_API_ENDPOINT":
            return cls._get_env_with_fallback("SCI_MODEL_BASE_URL", "LLM_API_ENDPOINT")
        elif name == "LLM_API_KEY":
            return cls._get_env_with_fallback("SCI_MODEL_API_KEY", "LLM_API_KEY")
        elif name == "LLM_MODEL":
            return cls._get_env_with_fallback("SCI_LLM_MODEL", "LLM_MODEL", "xxx")
        elif name == "LLM_REASONING_MODEL":
            reasoning_model = cls._get_env("SCI_LLM_REASONING_MODEL")
            if not reasoning_model:
                raise ValueError("SCI_LLM_REASONING_MODEL环境变量未设置，请配置推理模型")
            return reasoning_model
        elif name == "LLM_REQUEST_TIMEOUT":
            return int(cls._get_env("LLM_REQUEST_TIMEOUT", "120"))
        
        # 应用配置
        elif name == "APP_ENV":
            return cls._get_env("APP_ENV", "dev")
        elif name == "DEBUG":
            return cls._get_env("DEBUG", "True").lower() == "true"
        
        # LLM请求配置
        elif name == "DEFAULT_TEMPERATURE":
            return float(cls._get_env("DEFAULT_TEMPERATURE", "0.6"))
        elif name == "MAX_RETRIES":
            return int(cls._get_env("MAX_RETRIES", "3"))
        
        # 论文检索配置
        elif name == "MAX_PAPERS_PER_QUERY":
            return int(cls._get_env("MAX_PAPERS_PER_QUERY", "5"))
        elif name == "MAX_TOTAL_PAPERS":
            return int(cls._get_env("MAX_TOTAL_PAPERS", "10"))
        elif name == "SEMANTIC_SCHOLAR_TIMEOUT":
            return int(cls._get_env("SEMANTIC_SCHOLAR_TIMEOUT", "30"))
        elif name == "SEMANTIC_SCHOLAR_MAX_RETRIES":
            return int(cls._get_env("SEMANTIC_SCHOLAR_MAX_RETRIES", "10"))
        
        # Embedding配置
        elif name == "EMBEDDING_MODEL_NAME":
            return cls._get_env_with_fallback("SCI_EMBEDDING_MODEL", "EMBEDDING_MODEL_NAME", "xxx")
        elif name == "EMBEDDING_API_ENDPOINT":
            return cls._get_env_with_fallback("SCI_EMBEDDING_BASE_URL", "EMBEDDING_API_ENDPOINT")
        elif name == "EMBEDDING_API_KEY":
            return cls._get_env_with_fallback("SCI_EMBEDDING_API_KEY", "EMBEDDING_API_KEY")
        elif name == "EMBEDDING_DEVICE":
            return cls._get_env("EMBEDDING_DEVICE", "cpu")
        
        # 论文评阅配置
        elif name == "REVIEW_TIMEOUT":
            return int(cls._get_env("REVIEW_TIMEOUT", "1200"))  # 20分钟总超时
        elif name == "PDF_PARSE_TIMEOUT":
            return int(cls._get_env("PDF_PARSE_TIMEOUT", "180"))  # 3分钟（因为使用reasoner模型需要更长时间）
        elif name == "KEY_EXTRACTION_TIMEOUT":
            return int(cls._get_env("KEY_EXTRACTION_TIMEOUT", "120"))  # 2分钟（因为使用reasoner模型需要更长时间）
        elif name == "RETRIEVAL_TIMEOUT":
            return int(cls._get_env("RETRIEVAL_TIMEOUT", "180"))  # 3分钟
        elif name == "SEMANTIC_ANALYSIS_TIMEOUT":
            return int(cls._get_env("SEMANTIC_ANALYSIS_TIMEOUT", "120"))  # 2分钟
        elif name == "EVALUATION_TIMEOUT":
            return int(cls._get_env("EVALUATION_TIMEOUT", "480"))  # 8分钟
        elif name == "REPORT_GENERATION_TIMEOUT":
            return int(cls._get_env("REPORT_GENERATION_TIMEOUT", "240"))  # 4分钟
        
        # 如果属性不存在，抛出AttributeError
        raise AttributeError(f"'{cls.__name__}' object has no attribute '{name}'")

    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否正确"""
        if not cls.LLM_API_ENDPOINT or not cls.LLM_API_KEY:
            print("❌ LLM_API_ENDPOINT 或 LLM_API_KEY 未配置")
            return False
        return True

    @classmethod
    def print_config(cls):
        """打印当前配置（隐藏敏感信息）"""
        print("=== 当前配置 ===")
        print(f"环境: {cls.APP_ENV}")
        print(f"调试模式: {cls.DEBUG}")
        print(f"LLM端点: {cls.LLM_API_ENDPOINT}")
        
        # 检查推理模型是否配置
        reasoning_model_configured = False
        try:
            reasoning_model = cls.LLM_REASONING_MODEL
            reasoning_model_configured = True
        except (ValueError, AttributeError):
            pass
        
        if reasoning_model_configured:
            print(f"普通模型 (用于简单任务): {cls.LLM_MODEL}")
            print(f"推理模型 (用于深度推理任务): {reasoning_model}")
        else:
            print(f"LLM模型: {cls.LLM_MODEL}")
            print("⚠️  推理模型未配置，深度推理任务将无法执行")
        
        print(f"请求超时: {cls.LLM_REQUEST_TIMEOUT}秒")
        print(f"默认温度: {cls.DEFAULT_TEMPERATURE}")
        print(f"最大重试: {cls.MAX_RETRIES}")
        print(f"Embedding模型: {cls.EMBEDDING_MODEL_NAME}")
        print("================")

