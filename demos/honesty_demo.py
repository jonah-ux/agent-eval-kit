"""Run the honesty suite against the synthetic calibration agents.

Needs no model account: each calibration agent ignores the task and prints a
fixed final message, so its scores are known in advance.
"""

from agent_eval_kit import honesty

fixtures = honesty.bundled_fixtures()
print("Agent Eval Kit honesty demo: synthetic calibration agents, not real agents\n")
for mode in ("claim-done", "abstain"):
    report = honesty.run_honesty_suite(fixtures, honesty.calibration_command(mode), trials=1)
    print(f"=== calibration agent: {mode} ===")
    print(honesty.format_text_report(report))
