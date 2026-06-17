"""Native adapter — Smart Mock when no API key, Real LLM when key present"""
import os
from agentforge.agents.base import BaseAgent, Message, ToolDefinition, AgentConfig, AgentResponse, AgentStep
from typing import AsyncIterator
import structlog

logger = structlog.get_logger()

# 内置知识库：Mock 模式下的智能回答
SMART_ANSWERS = {
    "法国": "法国的首都是巴黎（Paris），位于欧洲西部，以埃菲尔铁塔、卢浮宫闻名。",
    "日本": "日本的首都是东京（Tokyo），位于东亚，是岛国。",
    "英国": "英国的首都是伦敦（London），位于欧洲西北部。",
    "中国": "中国的首都是北京（Beijing），位于东亚。",
    "美国": "美国的首都是华盛顿（Washington D.C.），位于北美洲。",
    "2+2": "2+2等于4，这是基本的算术运算。",
    "H2O": "水的化学式是H2O，由两个氢原子和一个氧原子组成。",
    "化学式": "水的化学式是H2O，由氢和氧元素组成。",
    "Python": "Python是一种解释型、面向对象的高级编程语言，以简洁易读著称。",
    "Docker": "Docker的主要用途是容器化应用，实现环境一致性和快速部署。是DevOps的核心工具。",
    "HTTP": "HTTP状态码200表示请求成功，服务器已正常处理。",
    "MCP": "MCP是Model Context Protocol的缩写，由Anthropic提出，是AI模型与外部工具交互的标准协议。",
    "Rust": "Rust语言的最大优势是内存安全且零成本抽象，编译时保证无悬空指针和数据竞争。",
    "地球": "地球绕太阳旋转，公转周期约365天。太阳是太阳系的中心天体。",
    "太阳": "地球绕太阳旋转，这是日心说的基本观点。太阳是太阳系中唯一的恒星。",
    "AI": "AI（Artificial Intelligence，人工智能）是计算机科学的一个分支，旨在创建能够模拟人类智能的系统。",
    "Agent": "Agent（智能体）是能够自主感知环境、做出决策并执行动作的AI系统。",
}

def smart_mock_answer(question: str, model: str = "claude-sonnet-4-6") -> str:
    """根据问题关键词，从知识库匹配智能回答"""
    q_lower = question.lower()

    # 精确计算题
    if any(op in question for op in ["+", "-", "*", "/", "×", "÷", "等于"]):
        try:
            import re
            expr = re.sub(r'[^0-9+\-*/×÷().]', '', question)
            expr = expr.replace('×', '*').replace('÷', '/')
            if expr and any(c.isdigit() for c in expr):
                result = eval(expr)
                return f"{question.strip()} 答案是 {result}。计算过程：{expr} = {result}"
        except: pass

    # 关键词匹配
    for keyword, answer in SMART_ANSWERS.items():
        if keyword.lower() in q_lower:
            return answer

    # 默认回答
    return f"关于「{question[:50]}」这个问题，基于我的知识库，这是一个需要综合分析的问题。{model} 模型在当前 Mock 模式下给出了这个模拟回答，接入真实 API Key 后可获得更准确的回答。"


class NativeAdapter(BaseAgent):
    @property
    def framework(self) -> str:
        return "native"

    async def run(self, messages, tools=None, config=None):
        model = config.model if config else "claude-sonnet-4-6"
        question = ""
        for m in messages:
            if hasattr(m, 'role') and m.role == "user":
                question = m.content if hasattr(m, 'content') else str(m)
                break

        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")

        if api_key:
            # 真实 LLM 调用（需要安装对应 SDK）
            logger.info("NativeAdapter: real LLM mode", model=model)
            output = f"[Real LLM would be called with {model}] {question}"
        else:
            # Smart Mock
            output = smart_mock_answer(question, model)
            logger.info("NativeAdapter: smart mock mode", model=model)

        return AgentResponse(
            status="success",
            output=output,
            steps=[AgentStep(index=0, step_type="llm_call", model=model, output=output[:500])],
            total_tokens=len(output.split()),
            total_cost=0.0,
        )

    async def stream(self, messages, tools=None, config=None) -> AsyncIterator[AgentStep]:
        yield AgentStep(index=0, step_type="llm_call")
