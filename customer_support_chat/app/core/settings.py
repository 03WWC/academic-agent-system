from os import environ
from dotenv import load_dotenv

load_dotenv()

# 导入模块不应该依赖真实凭据：缺少 API Key 时用占位值初始化 LLM 客户端，
# 保证 import 可用（单元测试、静态分析、IDE 索引）；
# 真正发起模型调用时，仍会因为密钥无效而明确报错。
PLACEHOLDER_API_KEY = "not-configured"


class Config:
    OPENAI_API_KEY: str = environ.get("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = environ.get("OPENAI_BASE_URL", "")
    
    # 模型配置，用于控制调用成本
    OPENAI_MODEL: str = environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    MAX_TOKENS: int = int(environ.get("MAX_TOKENS", "1000"))  # 限制输出长度，控制调用成本
    
    DATA_PATH: str = "./customer_support_chat/data"
    LOG_LEVEL: str = environ.get("LOG_LEVEL", "DEBUG")
    SQLITE_DB_PATH: str = environ.get(
        "SQLITE_DB_PATH", "./customer_support_chat/data/academic.sqlite"
    )
    QDRANT_URL: str = environ.get("QDRANT_URL", "http://localhost:6333")
    QDRANT_KEY: str = environ.get("QDRANT_KEY", "")
    RECREATE_COLLECTIONS: bool = environ.get("RECREATE_COLLECTIONS", "False")
    LIMIT_ROWS: int = environ.get("LIMIT_ROWS", "100")
    

def get_settings():
    return Config()
