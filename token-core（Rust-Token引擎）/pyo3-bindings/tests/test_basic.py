"""Basic tests for PyO3 token-core Python bindings"""
import sys
import json

def test_import():
    """Verify the module can be imported"""
    try:
        import token_core
        print("[PASS] import token_core")
        return True
    except ImportError as e:
        print(f"[SKIP] import token_core: {e} (build with: cd pyo3-bindings && maturin develop)")
        return None  # Not a failure, just not built

def test_list_models():
    try:
        import token_core
        models = token_core.list_models()
        assert len(models) > 0
        print(f"[PASS] list_models: {len(models)} models")
        return True
    except Exception as e:
        print(f"[FAIL] list_models: {e}")
        return False

def test_count_tokens():
    try:
        import token_core
        count = token_core.count_tokens("Hello, world!", "claude-sonnet-4-6")
        assert count > 0
        print(f"[PASS] count_tokens: {count}")
        return True
    except Exception as e:
        print(f"[FAIL] count_tokens: {e}")
        return False

def test_estimate():
    try:
        import token_core
        estimate = token_core.estimate_tokens("Hello, world!")
        assert estimate > 0
        print(f"[PASS] estimate_tokens: {estimate}")
        return True
    except Exception as e:
        print(f"[FAIL] estimate_tokens: {e}")
        return False

def test_truncate():
    try:
        import token_core
        messages = json.dumps([
            {"role": "system", "content": "You are helpful.", "index": 0},
            {"role": "user", "content": "Hello!", "index": 1}
        ])
        result = token_core.truncate_messages(messages, "claude-sonnet-4-6")
        data = json.loads(result)
        assert "tokens_kept" in data
        print(f"[PASS] truncate_messages")
        return True
    except Exception as e:
        print(f"[FAIL] truncate_messages: {e}")
        return False


if __name__ == "__main__":
    passed = 0
    failed = 0
    skipped = 0

    for name, fn in [
        ("import", test_import),
        ("list_models", test_list_models),
        ("count_tokens", test_count_tokens),
        ("estimate", test_estimate),
        ("truncate", test_truncate),
    ]:
        result = fn()
        if result is True:
            passed += 1
        elif result is False:
            failed += 1
        else:
            skipped += 1

    print(f"\n{'='*40}")
    print(f"PyO3 Bindings:   PASS  {passed}  FAIL  {failed}  SKIP  {skipped}")
    print(f"{'='*40}")
    sys.exit(0 if failed == 0 else 1)
