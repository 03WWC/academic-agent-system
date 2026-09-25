# 教务多 Agent 学生服务系统

这是一个面向 AI Agent 岗位作品集的教务服务项目。项目基于 LangGraph 构建多 Agent 工作流，让主助手根据学生意图把问题分发给不同的教务专业助手，并通过工具查询真实数据库或政策文档。

原始开源项目保留在旁边目录，方便对照学习：

```text
C:\Users\Administrator\Desktop\ai_study\agent_project_study\langgraph_multi-agent-rag-customer-support-proxy
```

## 核心能力

- 学生档案助手：查询学号、姓名、专业、年级、学籍状态、GPA、导师和课程状态。
- 课程政策助手：查询补考、缓考、退课、选课、成绩复核等教务政策。
- 学业预警助手：分析低分、需补考、低 GPA、休学等风险，并给出处理建议。
- 工单助手：创建和查询请假、补考、成绩复核、申诉等教务工单。
- 安全护栏：在主流程前检查越狱风险和业务相关性。
- Web 流式对话：FastAPI 提供 `/chat/stream`，前端按 NDJSON 流式展示回复。

## 技术栈

- Python 3.12
- FastAPI
- LangGraph
- LangChain
- SQLite
- Poetry
- DeepSeek / OpenAI-compatible Chat API

## 主要目录

```text
customer_support_chat/app/graph.py
```

LangGraph 主流程，包含用户信息加载、护栏检查、主助手路由和 4 个专业助手节点。

```text
customer_support_chat/app/services/assistants/
```

专业助手提示词和工具绑定：

- `primary_assistant.py`
- `student_profile_assistant.py`
- `course_policy_assistant.py`
- `academic_warning_assistant.py`
- `ticket_assistant.py`

```text
customer_support_chat/app/services/tools/
```

教务工具：

- `students.py`
- `academic_policy.py`
- `academic_warning.py`
- `tickets.py`

```text
academic_policy_documents/
```

教务政策知识库，目前使用 Markdown 文件作为轻量检索源。

```text
setup_academic_database.py
```

初始化教务 SQLite 示例数据库。

## 本地运行

安装依赖：

```powershell
poetry install
```

初始化教务数据库：

```powershell
poetry run python setup_academic_database.py
```

启动 Web 服务：

```powershell
poetry run uvicorn web_app.app.main:app --host 127.0.0.1 --port 8001 --log-level warning
```

访问：

```text
http://127.0.0.1:8001/
```

命令行运行：

```powershell
poetry run python customer_support_chat/app/main.py
```

## 环境变量

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
MAX_TOKENS=1000
SQLITE_DB_PATH=./customer_support_chat/data/academic.sqlite
```

## 测试

```powershell
poetry run python -m unittest discover -s tests
```

当前测试覆盖：

- LangGraph 能正常导入和编译。
- 4 个专业教务助手能正常导入。
- 旧业务运行文件已从改造项目中清理。
- 学生档案查询、政策检索、学业预警、工单创建和查询工具可用。

## 简历描述

可以写成：

```text
基于 LangGraph 和 FastAPI 设计并改造教务多 Agent 学生服务系统，实现主助手意图路由、学生档案查询、教务政策检索、学业预警分析和工单流转；通过 SQLite 工具调用与 Markdown 政策知识库保证回答可追溯，并支持 Web 端流式输出和安全护栏检查。
```

## 后续优化

- 将政策检索从关键词匹配升级为 Qdrant 向量检索。
- 给工单创建增加 Human-in-the-Loop 审批。
- 增加学生登录态和多学生会话切换。
- 补充端到端 Web 测试和示例截图。
