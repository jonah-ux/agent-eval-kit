from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    task = sys.argv[1] if len(sys.argv) > 1 else "demo"
    output = Path(os.environ["AGENT_EVAL_WORKSPACE"]) / "result.json"
    output.write_text(
        json.dumps({"task": task, "status": "failed"}) + "\n", encoding="utf-8"
    )
    print(f"task={task} deliberately failing fixture", file=sys.stderr)
    return 7


if __name__ == "__main__":
    raise SystemExit(main())