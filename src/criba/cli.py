from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .catalog import currents, methods
from .engine import activate, build_prompt
from .storage import Storage

def _query(args):
    if args.query: return args.query
    if args.file: return Path(args.file).read_text(encoding="utf-8")
    raise ValueError("Indica --query o --file.")
def _run(args, prompt=False):
    query=_query(args); packet=activate(query,args.current,args.mode,args.supporting_methods)
    store=Storage(args.database); store.save(query,packet,{"current":args.current,"mode":args.mode,"supporting_methods":args.supporting_methods})
    output=build_prompt(packet) if prompt else json.dumps(packet,ensure_ascii=False,indent=2)
    if getattr(args,"output",None): Path(args.output).write_text(output,encoding="utf-8")
    else: print(output)
    return 0
def main(argv=None):
    parser=argparse.ArgumentParser(prog="criba",description="CRIBA Current Engine local")
    parser.add_argument("--database",default=None,help="Ruta SQLite (por defecto artifacts/criba.sqlite3)")
    sub=parser.add_subparsers(dest="command",required=True)
    def activation(name):
        p=sub.add_parser(name); p.add_argument("--query"); p.add_argument("--file"); p.add_argument("--current",default="auto"); p.add_argument("--mode",default="balanced"); p.add_argument("--supporting-methods",type=int,default=4); return p
    activation("activate").add_argument("--json",action="store_true")
    activation("run")
    bp=activation("build-prompt"); bp.add_argument("--output")
    sub.add_parser("list-currents")
    ex=sub.add_parser("explain"); ex.add_argument("--session",required=True)
    cmp=sub.add_parser("compare"); cmp.add_argument("--session-a",required=True); cmp.add_argument("--session-b",required=True)
    sv=sub.add_parser("serve"); sv.add_argument("--host",default="127.0.0.1"); sv.add_argument("--port",type=int,default=8765)
    sub.add_parser("mcp"); sub.add_parser("gui")
    args=parser.parse_args(argv)
    try:
        if args.command in {"activate","run"}: return _run(args)
        if args.command=="build-prompt": return _run(args,True)
        if args.command=="list-currents": print(json.dumps(currents(),ensure_ascii=False,indent=2)); return 0
        if args.command=="explain": print(json.dumps(Storage(args.database).get(args.session),ensure_ascii=False,indent=2)); return 0
        if args.command=="compare": print(json.dumps(Storage(args.database).compare(args.session_a,args.session_b),ensure_ascii=False,indent=2)); return 0
        if args.command=="serve":
            from .api import serve; serve(args.host,args.port,args.database); return 0
        if args.command=="mcp":
            from .mcp_server import run_stdio; run_stdio(args.database); return 0
        if args.command=="gui":
            from .gui import run; return run(args.database)
    except (ValueError,OSError) as exc:
        print(f"Error: {exc}",file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())

