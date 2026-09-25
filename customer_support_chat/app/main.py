import os
import uuid

from langchain_core.messages import AIMessage

from customer_support_chat.app.core.logger import logger
from customer_support_chat.app.graph import multi_agentic_graph


def main():
    """命令行方式运行教务多 Agent 学生服务系统。"""
    try:
        graph = multi_agentic_graph.get_graph(xray=True)
        graph_image = graph.draw_mermaid_png()
        graphs_dir = "./graphs"
        os.makedirs(graphs_dir, exist_ok=True)
        image_path = os.path.join(graphs_dir, "academic-agent-system-graph.png")
        with open(image_path, "wb") as f:
            f.write(graph_image)
        print(f"教务 Agent 图结构已保存到：{image_path}")
    except Exception as e:
        logger.error(f"生成图结构可视化时出错：{e}")
        print("图结构可视化生成失败，将继续运行主程序。")

    config = {
        "configurable": {
            "student_id": "20240001",
            "thread_id": str(uuid.uuid4()),
        }
    }

    printed_message_ids = set()

    try:
        while True:
            user_input = input("学生：")
            if user_input.strip().lower() in ["quit", "exit", "q"]:
                print("再见！")
                break

            events = multi_agentic_graph.stream(
                {"messages": [("user", user_input)]},
                config,
                stream_mode="values",
            )

            for event in events:
                for message in event.get("messages", []):
                    if message.id in printed_message_ids:
                        continue
                    if isinstance(message, AIMessage) and message.content:
                        print(f"助手：{message.content}")
                    printed_message_ids.add(message.id)

    except Exception as e:
        logger.error(f"运行过程中出现异常：{e}")
        print("运行过程中出现异常，请查看日志获取更多细节。")


if __name__ == "__main__":
    main()
