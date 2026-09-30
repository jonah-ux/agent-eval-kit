import argparse,json,subprocess,time,shlex

def main(argv=None):
 p=argparse.ArgumentParser(prog="agent-eval"); p.add_argument("command",choices=["run"]); p.add_argument("fixture"); p.add_argument("--command",dest="cmd",required=True); a=p.parse_args(argv)
 f=json.load(open(a.fixture)); started=time.time(); cmd=a.cmd.replace("{task}",shlex.quote(f.get("task",""))); r=subprocess.run(cmd,shell=True,text=True,capture_output=True,timeout=f.get("timeout",30)); expected=f.get("expect_exit",0); ok=r.returncode==expected and all(x in r.stdout for x in f.get("expect_stdout",[])); out={"schema":"agent-eval/v1","ok":ok,"exit_code":r.returncode,"expected_exit":expected,"duration_ms":round((time.time()-started)*1000),"stdout":r.stdout,"stderr":r.stderr}; print(json.dumps(out,indent=2,sort_keys=True)); return 0 if ok else 1
