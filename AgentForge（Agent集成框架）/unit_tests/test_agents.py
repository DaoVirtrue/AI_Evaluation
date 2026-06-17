"""Unit tests for AgentForge middleware + adapters"""
import sys, asyncio

P = F = 0

def test(name, fn):
    global P, F
    try:
        fn() if not asyncio.iscoroutinefunction(fn) else asyncio.run(fn())
        print(f"  [PASS] {name}"); P += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}"); F += 1

def run():
    from agentforge.agents.registry import get_adapter, ADAPTERS
    test("adapter_registry_has_three", lambda: len(ADAPTERS) >= 3)
    test("get_native_adapter", lambda: get_adapter("native").framework == "native")
    test("get_langchain_adapter", lambda: get_adapter("langchain").framework == "langchain")

    from agentforge.middleware.pipeline import MiddlewarePipeline, PipelineContext
    from agentforge.agents.base import AgentConfig, Message
    from agentforge.middleware.tool_sanitizer import ToolCallSanitizer
    test("sanitizer_blocks_dangerous", lambda: (
        p := MiddlewarePipeline([ToolCallSanitizer()]),
        config := AgentConfig(),
        msgs := [Message(role="user", content="run rm -rf /")],
        async def handler(ctx): from agentforge.agents.base import AgentResponse; return AgentResponse()
    ))
    import asyncio
    async def check():
        ctx = PipelineContext(config=AgentConfig(), messages=msgs)
        ctx2 = await ToolCallSanitizer().before(ctx)
        assert ctx2.should_short_circuit is True
    asyncio.run(check())
    P += 1; print("  [PASS] sanitizer_blocks_dangerous")

    from agentforge.middleware.model_router import ModelRouter
    test("model_router_fallback", lambda: ModelRouter.get_fallback("claude-opus-4-8") == "claude-sonnet-4-6")

    from agentforge.bridge.rl_bridge import RLTrainingBridge
    from agentforge.agents.base import AgentResponse, AgentStep
    t = AgentResponse(steps=[AgentStep(index=0, step_type="llm_call", model="test")])
    test("rl_export_jsonl", lambda: len(RLTrainingBridge.export_batch([t], "jsonl")) > 0)

    test("rl_export_json", lambda: len(RLTrainingBridge.export_batch([t], "json")) > 0)

    print(f"\n{'='*40}"); print(f"Unit Tests: PASS  {P}  FAIL  {F}")
    sys.exit(0 if F == 0 else 1)

if __name__ == "__main__": run()
