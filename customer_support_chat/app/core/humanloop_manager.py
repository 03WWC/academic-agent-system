import os
from gohumanloop  import DefaultHumanLoopManager , APIProvider
from gohumanloop.adapters.langgraph_adapter import HumanloopAdapter
from gohumanloop.providers.terminal_provider import TerminalProvider 
from gohumanloop.utils import get_secret_from_env

# 初始化 GoHumanLoop 管理器和适配器
# 放在独立文件中，避免循环导入

# 创建 GoHumanLoopManager 实例
humanloop_manager = DefaultHumanLoopManager(
    APIProvider(
        name="ApiProvider",
        api_base_url=os.environ.get("GOHUMANLOOP_API_BASE_URL", "http://127.0.0.1:9800/api"), # 审批服务地址
        api_key=get_secret_from_env("GOHUMANLOOP_API_KEY"),
        default_platform="feishu"
    )
)
# 创建 LangGraphAdapter 实例
humanloop_adapter = HumanloopAdapter(
    manager=humanloop_manager,
    default_timeout=300,  # 默认超时时间为 5 分钟
)
