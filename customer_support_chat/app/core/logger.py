import logging
from .settings import get_settings

config = get_settings()


def _resolve_log_level(value) -> int:
    """把配置里的日志级别名解析成 logging 级别常量。

    不能直接 getattr(logging, name)，它有两个坑：
    - 小写名字取到的是 logging.debug / logging.info 这些**函数**而不是常量，
      传给 setLevel 会抛 TypeError；
    - 拼错的名字直接抛 AttributeError。
    两者都会让应用在导入阶段崩溃，而报错完全看不出是 LOG_LEVEL 写错了。
    """
    level = getattr(logging, str(value).strip().upper(), None)
    if isinstance(level, int):
        return level

    logging.getLogger(__name__).warning(
        "无法识别的 LOG_LEVEL=%r，回退到 INFO；可用值：DEBUG/INFO/WARNING/ERROR/CRITICAL。",
        value,
    )
    return logging.INFO


LOG_LEVEL = _resolve_log_level(config.LOG_LEVEL)

logger = logging.getLogger("customer_support_chat")
logger.setLevel(LOG_LEVEL)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(LOG_LEVEL)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
)
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
