"""
评测 Worker — 同步线程，后台自动处理评测
每10秒扫描 queued/running 的评测，逐条调 AgentForge，评分，写入结果
"""
import json, os, logging, threading, time, requests
from sqlalchemy import select, update, create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Evaluation, EvaluationResult, Dataset, Base
from datetime import datetime

logger = logging.getLogger("agent-eval.worker")
AGENT_FORGE_URL = os.environ.get("AGENT_FORGE_URL", "http://agent-forge:8001")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://agent:devpass@postgres:5432/agent_eval")

# 同步引擎（Worker 专用，不和 FastAPI async 引擎冲突）
sync_engine = create_engine(DATABASE_URL.replace("+asyncpg", "+psycopg2"), echo=False)
SyncSession = sessionmaker(bind=sync_engine)

DEFAULT_CASES = [
    ("法国的首都是哪里？", "巴黎"),
    ("2+2等于多少？", "4"),
    ("水的化学式是什么？", "H2O"),
    ("Python是什么类型的语言？", "解释型"),
    ("Docker的主要用途是什么？", "容器化"),
]

def run_eval(eval_id: str):
    """处理单条评测（同步）"""
    db = SyncSession()
    try:
        ev = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if not ev or ev.status in ("completed", "failed", "cancelled"):
            return

        ev.status = "running"
        db.commit()

        # 获取数据集
        cases = []
        dataset_id = (ev.agent_config or {}).get("dataset_id", "")
        if dataset_id:
            ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if ds and ds.file_path and os.path.exists(ds.file_path):
                with open(ds.file_path, encoding="utf-8") as f:
                    cases = [json.loads(line) for line in f if line.strip()]

        if not cases:
            cases = [{"case_id": f"auto-{i}", "input": q, "expected_output": a}
                     for i, (q, a) in enumerate(DEFAULT_CASES)]

        max_cases = min(ev.total_cases or len(cases), len(cases))
        passed = 0

        for case in cases[:max_cases]:
            question = case.get("input", "")
            expected = case.get("expected_output", "").lower()
            cid = case.get("case_id", f"case-{len(cases)}")

            try:
                r = requests.post(f"{AGENT_FORGE_URL}/api/v1/agents/run",
                    json={"messages": [{"role": "user", "content": question}],
                          "framework": "native",
                          "model": (ev.agent_config or {}).get("model", "claude-sonnet-4-6")},
                    timeout=15)
                output = r.json().get("output", "") if r.status_code == 200 else ""
                tokens = r.json().get("total_tokens", 0) if r.status_code == 200 else 0
                cost = r.json().get("total_cost", 0.0) if r.status_code == 200 else 0.0
            except Exception as e:
                output = f"Error: {e}"
                tokens = 0
                cost = 0.0

            # 评分
            is_passed = any(kw in output.lower() for kw in expected.split()) if expected else False
            if is_passed: passed += 1

            result = EvaluationResult(
                evaluation_id=eval_id, case_id=cid,
                input=question, expected_output=case.get("expected_output", ""),
                actual_output=output[:2000], passed=is_passed,
                score=1.0 if is_passed else 0.0,
                token_usage={"prompt_tokens": tokens, "completion_tokens": 0, "total_cost": cost},
                latency_ms=0,
            )
            db.add(result)
            db.commit()

        # 更新评测状态
        total = max_cases
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0
        ev.status = "completed"
        ev.completed_cases = total
        ev.metrics = {"pass_rate": pass_rate, "passed": passed, "failed": total - passed, "total": total}
        ev.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Eval {eval_id[:8]} done: {passed}/{total} ({pass_rate}%)")

    except Exception as e:
        logger.error(f"Eval {eval_id[:8]} error: {e}")
        try:
            ev = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            if ev:
                ev.status = "failed"
                ev.metrics = {"error": str(e)[:200]}
                db.commit()
        except: pass
    finally:
        db.close()

def worker_loop():
    """主循环"""
    logger.info("Worker started (sync mode)")
    while True:
        try:
            db = SyncSession()
            evals = db.query(Evaluation).filter(Evaluation.status.in_(["queued", "running"])).all()
            db.close()
            for ev in evals:
                run_eval(ev.id)
        except Exception as e:
            logger.error(f"Worker loop: {e}")
        time.sleep(10)

def start_worker():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    logger.info("Worker thread started")
