import json
from tkinter import END
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient

# 多服务器配置（全部使用stdio）
multi_server_config = {
    "emadmin": {
        "command": "python",
        "args": ["code/mcp/emadmin_server.py"],
        "transport": "stdio",
    }
    # "nlweb": {
    #     "command": "python",
    #     "args": ["/Users/yehaitao/PythonProjects/nlweb_app/code/nlweb_server.py"],
    #     "transport": "stdio",
    # }
}

# 自定义系统提示词
SYSTEM_PROMPT = """您是一个智能助手，可以访问两个专用系统：
    1. [emadmin系统] - 提供环境管理、DNS配置等系统管理功能
    - 工具前缀: emadmin_
    - 示例: emadmin_query_dns, emadmin_create_env

    2. [nlweb系统] - 提供网页内容提取和操作功能
    - 工具前缀: nlweb_
    - 示例: nlweb_get_content, nlweb_click_button

    工作流程：
    1. 首先执行emadmin系统的工具，看看能否执行完成用户需求
    2. 然后去问nlweb系统要能实现用户需求的网页信息
    3. 结合前2步返回用户

    请根据问题类型选择正确的工具前缀！"""

# 初始化记忆存储
memory = MemorySaver()

# 全局缓存 agent_graph 和 tools，避免重复初始化
_cached_graph = None
_cached_tools = None


async def initialize_agent():
    global _cached_graph, _cached_tools

    if _cached_graph and _cached_tools:
        return _cached_graph, _cached_tools

    # 创建 MCP 客户端
    client = MultiServerMCPClient(multi_server_config)
    tools = await client.get_tools()

    # 创建状态图
    graph_builder = StateGraph(MessagesState)

    # 创建代理节点和工具节点
    agent = create_react_agent("openai:gpt-4.1", tools)
    graph_builder.add_node("agent", agent)
    tool_node = ToolNode(tools)
    graph_builder.add_node("tools", tool_node)

    # 设置图的边
    graph_builder.add_edge("tools", "agent")
    graph_builder.set_entry_point("agent")

    # 条件跳转：如果 agent 返回的是调用工具的动作，则跳转到 tools 节点
    def should_continue(state):
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
            return "tools"
        return END

    graph_builder.add_conditional_edges("agent", should_continue)

    # 编译图并启用 memory
    # agent_graph = graph_builder.compile(checkpointer=memory)
    agent_graph = graph_builder.compile()
    _cached_graph = agent_graph
    _cached_tools = tools

    return agent_graph, tools


async def run_agent(query: str, thread_id: str = "default"):
    """
    异步运行带记忆的代理
    :param query: 用户输入的自然语言指令
    :param thread_id: 会话 ID，用于区分不同用户的对话历史
    :return: 最终回复文本
    """
    try:
        agent_graph, tools = await initialize_agent()

        config = {"configurable": {"thread_id": thread_id}}

        # 构建初始状态
        input_state = {
            "messages": [{"role": "user", "content": query}]
        }

        # 运行图
        result_state = await agent_graph.ainvoke(input_state)
        # result_state = await agent_graph.ainvoke(input_state, config=config)

        # 提取最终回复
        final_response = extract_final_response(result_state)
        return final_response

    except Exception as e:
        return {"error": str(e)}


def extract_final_response(agent_result: dict) -> str:
    """
    从代理返回结果中提取最终的用户友好响应
    正确处理 LangChain 的消息对象

    参数:
        agent_result (dict): 代理返回的结果字典，包含 'messages' 字段

    返回:
        str: 最终的用户友好响应文本
    """
    messages = agent_result.get("messages", [])

    # 1. 查找最后一条 AIMessage
    last_ai_message = None
    for msg in messages:
        # 检查是否是 AIMessage 类型
        if hasattr(msg, 'type') and msg.type == "ai":
            last_ai_message = msg
        # 对于某些版本，可能是类名判断
        elif type(msg).__name__ == "AIMessage":
            last_ai_message = msg

    # 2. 如果找到最后一条 AIMessage
    if last_ai_message:
        # 获取内容 - 使用属性访问而不是 get()
        content = last_ai_message.content if hasattr(
            last_ai_message, 'content') else ""
        if content.strip():
            return content.strip()

    # 3. 如果没有有效的 AIMessage，尝试解析最后一条 ToolMessage
    last_tool_message = None
    for msg in reversed(messages):
        # 检查是否是 ToolMessage 类型
        if hasattr(msg, 'type') and msg.type == "tool":
            last_tool_message = msg
            break
        # 对于某些版本，可能是类名判断
        elif type(msg).__name__ == "ToolMessage":
            last_tool_message = msg
            break

    if last_tool_message:
        # 获取工具消息内容
        content = last_tool_message.content if hasattr(
            last_tool_message, 'content') else ""
        content = content.strip()

        if content:
            # 尝试解析 JSON 格式的工具响应
            try:
                tool_data = json.loads(content)
                if "error" in tool_data:
                    return f"操作失败: {tool_data['error']}"
                elif "message" in tool_data:
                    return tool_data["message"]
                elif "result" in tool_data:
                    return tool_data["result"]
            except json.JSONDecodeError:
                return content

    # 4. 所有回退方案都失败
    return "代理未返回明确的响应结果"
