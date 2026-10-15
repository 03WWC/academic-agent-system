"""日志配置的测试。

LOG_LEVEL 来自环境变量，取值写错不应该让应用在导入阶段崩溃。
原先直接用 getattr(logging, config.LOG_LEVEL)：小写名字会取到 logging.debug
这类函数（setLevel 抛 TypeError），拼错的名字会抛 AttributeError。
"""

import logging
import unittest

from customer_support_chat.app.core.logger import _resolve_log_level, logger


class ResolveLogLevelTest(unittest.TestCase):
    def test_upper_case_names_resolve_to_constants(self):
        self.assertEqual(_resolve_log_level("DEBUG"), logging.DEBUG)
        self.assertEqual(_resolve_log_level("WARNING"), logging.WARNING)
        self.assertEqual(_resolve_log_level("CRITICAL"), logging.CRITICAL)

    def test_lower_case_names_resolve_to_constants(self):
        """.env 里写小写是最常见的写法，不能因此崩溃。"""
        self.assertEqual(_resolve_log_level("debug"), logging.DEBUG)
        self.assertEqual(_resolve_log_level("info"), logging.INFO)
        self.assertEqual(_resolve_log_level("warning"), logging.WARNING)

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(_resolve_log_level("  error  "), logging.ERROR)

    def test_unknown_name_falls_back_to_info(self):
        self.assertEqual(_resolve_log_level("verbose"), logging.INFO)
        self.assertEqual(_resolve_log_level(""), logging.INFO)
        self.assertEqual(_resolve_log_level(None), logging.INFO)

    def test_function_attributes_are_not_accepted_as_levels(self):
        """logging.debug 是函数，不是级别；不能被当成合法取值。"""
        self.assertNotEqual(_resolve_log_level("debug"), logging.debug)
        self.assertIsInstance(_resolve_log_level("debug"), int)

    def test_configured_logger_level_is_an_integer(self):
        self.assertIsInstance(logger.level, int)


if __name__ == "__main__":
    unittest.main()
