"""工具包入口。

这里使用懒加载，避免导入某一个轻量工具时，把旧业务的向量库、数据库、
第三方 API 依赖全部提前初始化。
"""

_TOOL_MODULES = {
    "get_student_profile": "students",
    "lookup_academic_policy": "academic_policy",
    "analyze_academic_warning": "academic_warning",
    "create_academic_ticket": "tickets",
    "search_academic_tickets": "tickets",
}

__all__ = list(_TOOL_MODULES)


def __getattr__(name):
    if name not in _TOOL_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    # 真正访问工具时才导入对应模块，减少包初始化阶段的副作用。
    module_name = _TOOL_MODULES[name]
    module = __import__(f"{__name__}.{module_name}", fromlist=[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
