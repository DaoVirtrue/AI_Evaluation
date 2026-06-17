"""token-core FastAPI — Rust PyO3 backend with Python fallback"""
import logging, traceback, json, os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}')
logger = logging.getLogger("token-core")

# Try importing Rust PyO3 module
USE_RUST = False
try:
    import token_core_py as tcr
    USE_RUST = True
    logger.info("Using Rust PyO3 backend")
except ImportError:
    logger.warning("Rust PyO3 not available, using Python fallback")

app = FastAPI(title="token-core", version="0.1.0")

# ===== Pure Python fallback pricing =====
PURE_PRICING = {
    "claude-fable-5":{"provider":"anthropic","input":10.00,"output":50.00,"limit":1_000_000,"max_out":128000},
    "claude-opus-4-8":{"provider":"anthropic","input":5.00,"output":25.00,"cache":0.50,"batch_in":2.50,"batch_out":12.50,"limit":1_000_000,"max_out":128000},
    "claude-sonnet-4-6":{"provider":"anthropic","input":3.00,"output":15.00,"cache":0.30,"batch_in":1.50,"batch_out":7.50,"limit":1_000_000,"max_out":64000},
    "claude-haiku-4-5":{"provider":"anthropic","input":1.00,"output":5.00,"cache":0.10,"batch_in":0.50,"batch_out":2.50,"limit":200000,"max_out":64000},
    "gpt-5.5":{"provider":"openai","input":5.00,"output":30.00,"cache":0.50,"batch_in":2.50,"batch_out":15.00,"limit":1_050_000,"max_out":128000,"long_thresh":272000,"long_mult":(2.0,1.5)},
    "gpt-5.4":{"provider":"openai","input":2.50,"output":15.00,"batch_in":1.25,"batch_out":7.50,"limit":1_050_000,"max_out":128000},
    "gpt-4.1":{"provider":"openai","input":2.00,"output":8.00,"cache":0.50,"batch_in":1.00,"batch_out":4.00,"limit":1_047_576,"max_out":32768},
    "gpt-4.1-mini":{"provider":"openai","input":0.40,"output":1.60,"limit":1_047_576,"max_out":32768},
    "gpt-4.1-nano":{"provider":"openai","input":0.10,"output":0.40,"limit":1_047_576,"max_out":16384},
    "deepseek-v4-pro":{"provider":"deepseek","input":0.435,"output":0.87,"cache":0.003625,"limit":1_000_000,"max_out":384000},
    "deepseek-v4-pro-standard":{"provider":"deepseek","input":1.74,"output":3.48,"cache":0.0145,"limit":1_000_000,"max_out":384000},
    "deepseek-v4-flash":{"provider":"deepseek","input":0.14,"output":0.28,"cache":0.0028,"limit":1_000_000,"max_out":384000},
    "gemini-3.1-pro":{"provider":"google","input":2.00,"output":12.00,"cache":0.20,"limit":2_000_000,"max_out":64000,"long_thresh":200000,"long_mult":(2.0,1.5)},
    "gemini-3.5-flash":{"provider":"google","input":1.50,"output":9.00,"limit":1_000_000,"max_out":64000},
    "gemini-3.1-flash-lite":{"provider":"google","input":0.25,"output":1.50,"limit":1_000_000,"max_out":64000},
    "qwen3-235b-a22b":{"provider":"alibaba","input":0.10,"output":0.10,"limit":131072,"max_out":8192},
    "llama-4-maverick":{"provider":"meta","input":0.20,"output":0.80,"limit":1_000_000,"max_out":8192},
}

def py_count(text: str) -> int:
    if not text: return 0
    cjk = sum(1 for c in text if c > '⺀')
    return max(1, int(cjk / 1.5 + (len(text) - cjk) / 3.5))

def py_tokens_to_cost(tokens: int, price_per_m: float) -> float:
    return round(tokens / 1_000_000 * price_per_m, 8)

# ===== Models =====
class TextInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=10_000_000)
    model: str = Field(default="claude-sonnet-4-6")

class MsgItem(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    content: str = Field(..., min_length=1)
    index: int = 0

class BatchInput(BaseModel):
    messages: list[MsgItem] = Field(..., min_length=1)
    model: str = Field(default="claude-sonnet-4-6")

class UsageInput(BaseModel):
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    cache_hit_tokens: int = 0
    thinking_tokens: int = 0

class CostInput(BaseModel):
    usage: UsageInput
    model: str
    mode: str = Field(default="online", pattern="^(online|batch)$")

class CompareInput(BaseModel):
    input_tokens: int = Field(..., ge=0)
    estimated_output: int = Field(..., ge=0)
    candidates: list[str] = Field(..., min_length=1)

class TruncateInput(BaseModel):
    messages: list[MsgItem]
    model: str = Field(default="claude-sonnet-4-6")

# ===== Error handler =====
@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled: {traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"code": 500, "msg": "Internal error", "detail": None})

# ===== Routes =====
@app.get("/health")
async def health():
    return {"status": "ok", "models": len(PURE_PRICING), "backend": "rust" if USE_RUST else "python"}

@app.post("/api/v1/count")
async def count(input: TextInput):
    if input.model not in PURE_PRICING:
        raise HTTPException(status_code=400, detail={"code": 400, "msg": f"Unknown model: {input.model}"})
    if USE_RUST:
        tokens = tcr.count_tokens(input.text, input.model)
    else:
        tokens = py_count(input.text)
    logger.info(f"count: model={input.model}, chars={len(input.text)}, tokens={tokens}, rust={USE_RUST}")
    return {"tokens": tokens, "model": input.model, "chars": len(input.text), "backend": "rust" if USE_RUST else "python"}

@app.post("/api/v1/count/batch")
async def count_batch(input: BatchInput):
    if input.model not in PURE_PRICING:
        raise HTTPException(status_code=400, detail={"code": 400, "msg": f"Unknown model: {input.model}"})
    if USE_RUST:
        msgs_json = json.dumps([m.model_dump() for m in input.messages])
        counts = tcr.count_batch(msgs_json, input.model)
    else:
        counts = [py_count(m.content) for m in input.messages]
    return {"counts": counts, "total_tokens": sum(counts), "model": input.model, "backend": "rust" if USE_RUST else "python"}

@app.post("/api/v1/estimate")
async def estimate(input: TextInput):
    if USE_RUST:
        tokens = tcr.estimate_tokens(input.text)
    else:
        tokens = py_count(input.text)
    return {"estimated_tokens": tokens, "chars": len(input.text)}

@app.post("/api/v1/cost")
async def cost(input: CostInput):
    if input.model not in PURE_PRICING:
        raise HTTPException(status_code=400, detail={"code": 400, "msg": f"Unknown model: {input.model}"})
    if USE_RUST:
        usage_json = json.dumps({"prompt_tokens": input.usage.prompt_tokens, "completion_tokens": input.usage.completion_tokens, "cache_hit_tokens": input.usage.cache_hit_tokens, "thinking_tokens": input.usage.thinking_tokens, "effective_output_tokens": 0})
        result_str = tcr.calculate_cost(usage_json, input.model, input.mode)
        result = json.loads(result_str)
    else:
        p = PURE_PRICING[input.model]
        is_batch = input.mode == "batch"
        inp = p.get("batch_in", p["input"]) if is_batch else p["input"]
        out = p.get("batch_out", p["output"]) if is_batch else p["output"]
        base = py_tokens_to_cost(input.usage.prompt_tokens, inp) + py_tokens_to_cost(input.usage.completion_tokens, out)
        cache_save = py_tokens_to_cost(input.usage.cache_hit_tokens, p["input"]) - py_tokens_to_cost(input.usage.cache_hit_tokens, p.get("cache", p["input"])) if p.get("cache") and input.usage.cache_hit_tokens > 0 else 0.0
        long_sur = 0.0
        if p.get("long_thresh") and input.usage.prompt_tokens > p["long_thresh"]:
            over = input.usage.prompt_tokens - p["long_thresh"]
            long_sur = py_tokens_to_cost(over, p["input"] * (p["long_mult"][0]-1)) + py_tokens_to_cost(input.usage.completion_tokens, p["output"] * (p["long_mult"][1]-1))
        result = {"base_input_cost": round(py_tokens_to_cost(input.usage.prompt_tokens, inp), 6), "base_output_cost": round(py_tokens_to_cost(input.usage.completion_tokens, out), 6), "cache_savings": round(cache_save, 6), "long_context_surcharge": round(long_sur, 6), "thinking_cost": 0, "total": round(base - cache_save + long_sur, 6)}
    logger.info(f"cost: model={input.model}, mode={input.mode}, total={result.get('total',0):.6f}, rust={USE_RUST}")
    return {**result, "backend": "rust" if USE_RUST else "python"}

@app.post("/api/v1/compare")
async def compare(input: CompareInput):
    if USE_RUST:
        result_str = tcr.compare_models(input.input_tokens, input.estimated_output, json.dumps(input.candidates))
        return json.loads(result_str)
    results = []
    for model in input.candidates:
        p = PURE_PRICING.get(model)
        if not p: continue
        cost = py_tokens_to_cost(input.input_tokens, p["input"]) + py_tokens_to_cost(input.estimated_output, p["output"])
        results.append({"model": model, "estimated_cost": round(cost, 6)})
    return sorted(results, key=lambda x: x["estimated_cost"])

@app.post("/api/v1/truncate")
async def truncate(input: TruncateInput):
    p = PURE_PRICING.get(input.model, {"limit": 1_000_000})
    limit = p["limit"]
    if USE_RUST:
        msgs_json = json.dumps([m.model_dump() for m in input.messages])
        result_str = tcr.truncate_messages(msgs_json, input.model)
        return json.loads(result_str)
    msgs = [m.model_dump() for m in input.messages]
    total = sum(py_count(m["content"]) for m in msgs)
    if total <= limit:
        return {"messages": msgs, "tokens_kept": total, "tokens_lost": 0, "truncated_count": 0, "warning": None}
    kept = [m for m in msgs if m["role"] == "system"]
    non_sys = sorted([m for m in msgs if m["role"] != "system"], key=lambda m: (0 if m["role"]=="tool" else 1 if m["index"]>=max(0,len([x for x in msgs if x["role"]!="system"])-6) else 2))
    budget = limit - sum(py_count(m["content"]) for m in kept)
    for m in non_sys:
        t = py_count(m["content"])
        if budget >= t: kept.append(m); budget -= t
    kept.sort(key=lambda m: m.get("index", 0))
    kept_tokens = sum(py_count(m["content"]) for m in kept)
    return {"messages": kept, "tokens_kept": kept_tokens, "tokens_lost": total-kept_tokens, "truncated_count": len(msgs)-len(kept), "warning": ">90% truncated" if kept_tokens < total*0.1 else None}

@app.get("/api/v1/models")
async def list_models():
    if USE_RUST:
        return {"models": tcr.list_models(), "count": len(tcr.list_models()), "backend": "rust"}
    return {"models": list(PURE_PRICING.keys()), "count": len(PURE_PRICING), "backend": "python"}

@app.get("/api/v1/pricing/{model}")
async def get_pricing(model: str):
    p = PURE_PRICING.get(model)
    if not p:
        raise HTTPException(status_code=404, detail={"code": 404, "msg": f"Unknown model: {model}"})
    return {"id": model, **{k: v for k, v in p.items() if k not in ("long_mult",)}}
