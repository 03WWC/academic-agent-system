from os import environ
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 导入模块不应该依赖真实凭据：缺少 API Key 时用占位值初始化 LLM 客户端，
# 保证 import 可用（单元测试、静态分析、IDE 索引）；
# 真正发起模型调用时，仍会因为密钥无效而明确报错。
PLACEHOLDER_API_KEY = "not-configured"

# 默认数据库位于包内，基于 __file__ 计算成绝对路径：
# 不依赖当前工作目录，从任何目录启动都能定位到同一个文件。
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "academic.sqlite"


class Config:
    OPENAI_API_KEY: str = environ.get("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = environ.get("OPENAI_BASE_URL", "")

    # 模型配置，用于控制调用成本
    OPENAI_MODEL: str = environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    MAX_TOKENS: int = int(environ.get("MAX_TOKENS", "1000"))  # 限制输出长度，控制调用成本

    LOG_LEVEL: str = environ.get("LOG_LEVEL", "DEBUG")
    # 允许用 SQLITE_DB_PATH 覆盖默认路径；相对路径按当前工作目录解析。
    SQLITE_DB_PATH: str = environ.get("SQLITE_DB_PATH", str(_DEFAULT_DB_PATH))


def get_settings():
    return Config()
