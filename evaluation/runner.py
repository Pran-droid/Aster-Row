import json
from pathlib import Path

from app.agent import SupportAgent


ROOT = Path(__file__).resolve().parent.parent
CASE_PATH = ROOT / "evaluation" / "visible-cases.json"


def _normalize_text(value):
    return str(value).strip().lower()


def _case_passes(case, result):
    expect = case.get("expect", {})
    answer = _normalize_text(result.get("answer", ""))
    sources = [s.lower() for s in result.get("sources", [])]

    required_sources = expect.get("required_sources", [])
    for source in required_sources:
        if not any(source.lower() in item for item in sources):
            return False, f"missing required source: {source}"

    for must_include in expect.get("must_include", []):
        if _normalize_text(must_include) not in answer:
            return False, f"missing required phrase: {must_include}"

    for must_include_concepts in expect.get("must_include_concepts", []):
        if must_include_concepts.lower() not in answer:
            return False, f"missing required concept: {must_include_concepts}"

    for must_not_include in expect.get("must_not_include", []):
        if _normalize_text(must_not_include) in answer:
            return False, f"contains forbidden phrase: {must_not_include}"

    for must_not_follow in expect.get("must_not_follow", []):
        if _normalize_text(must_not_follow) in answer:
            return False, f"followed forbidden directive: {must_not_follow}"

    tool_used = result.get("tool_used")
    tool_expected = expect.get("tool")
    if tool_expected == "not_called" and tool_used is not None:
        return False, "tool was called when it should not have been"
    if tool_expected == "order_lookup" and tool_used != "order_lookup":
        return False, "order_lookup tool was not used"
    if tool_expected == "not_called_without_id" and tool_used is not None:
        return False, "tool was called without an order ID"
    if tool_expected == "optional_sanitized_lookup" and tool_used not in {None, "order_lookup"}:
        return False, "privacy lookup did not behave as expected"

    if result.get("handoff") is True and not expect.get("handoff", False):
        return False, "unexpected handoff"
    if expect.get("handoff") is True and result.get("handoff") is not True:
        return False, "expected human handoff"

    return True, "ok"


def run_evaluation():
    with CASE_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    agent = SupportAgent("knowledge-base")
    results = []
    for case in payload["cases"]:
        session_id = case["id"]
        last_result = None
        for message in case["messages"]:
            last_result = agent.answer(message["content"], session_id=session_id)
        passed, reason = _case_passes(case, last_result or {})
        results.append({
            "id": case["id"],
            "category": case.get("category"),
            "passed": passed,
            "reason": reason,
            "answer": last_result.get("answer", "") if last_result else "",
            "sources": last_result.get("sources", []) if last_result else [],
        })

    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "cases": results,
    }
    return summary


if __name__ == "__main__":
    summary = run_evaluation()
    print(json.dumps(summary, indent=2))
