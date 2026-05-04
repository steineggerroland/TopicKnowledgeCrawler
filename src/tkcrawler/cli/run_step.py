from __future__ import annotations

import json
import sys

from tkcrawler.steps import STEP_REGISTRY
from tkcrawler.steps._runtime import StepError, fail, run_safely


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or argv[0] in {"-h", "--help"}:
        names = ", ".join(sorted(STEP_REGISTRY))
        print(f"Usage: python -m tkcrawler.cli.run_step <step>\n\nSteps: {names}", file=sys.stderr)
        return 2

    step_name = argv[0]
    step = STEP_REGISTRY.get(step_name)
    if step is None:
        result = fail(StepError("unknown_step", f"Unknown step: {step_name}", {"available": sorted(STEP_REGISTRY)}))
        print(json.dumps(result, ensure_ascii=False))
        return 1

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        result = fail(StepError("invalid_json", "stdin must contain valid JSON", {"error": str(exc)}))
        print(json.dumps(result, ensure_ascii=False))
        return 1

    result = run_safely(step, payload)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
