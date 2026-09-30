import json,tempfile,pathlib
from agent_eval_kit.cli import main
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/'fixture.json'; p.write_text(json.dumps({'task':'hello','expect_stdout':['hello']}))
 print('Agent Eval Kit demo: one task, one reproducible scorecard')
 main(['run',str(p),'--command','printf hello'])
