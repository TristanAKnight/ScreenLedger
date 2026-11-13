"""ScreenLedger CLI. No external network calls."""
import argparse,sys,shutil
from pathlib import Path
from importlib.resources import files
from .core import validate,serialize,ProjectError

def markdown(report):
    lines=['# ScreenLedger Handoff','',f"Project: `{report['projectId']}`",'',f"Ready: **{report['handoffReady']}**",'','## Checks','']
    lines += [f'- {k}: {v}' for k,v in sorted(report['assessment'].items())]
    lines += ['','## Findings','']
    lines += [f"- {f['code']} at {f['path']}: {f['detail']}" for f in report['findings']] or ['No findings.']
    return '\n'.join(lines)+'\n'

def main(argv=None):
    p=argparse.ArgumentParser(prog='screenledger');sub=p.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('directory',type=Path)
    for cmd in ('validate','handoff'):
        q=sub.add_parser(cmd);q.add_argument('--project',type=Path,required=True);q.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    try:
        if args.command=='init':
            dest=args.directory
            if dest.is_symlink() or (dest.exists() and any(dest.iterdir())):raise ProjectError('init target must be empty and not symlinked')
            dest.mkdir(parents=True,exist_ok=True)
            template=files('screenledger').joinpath('demo')
            for relative in ('requirements.json','screens.json','assets/ui/background.png','assets/ui/new_game_default.png','assets/ui/new_game_pressed.png'):
                target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(template.joinpath(*relative.split('/')).read_bytes())
            print(f'Initialized: {dest}')
            return 0
        report=validate(args.project)
        output=serialize(report) if args.command=='validate' else markdown(report)
        if args.output:
            target=args.output.resolve(strict=False)
            if target.is_relative_to(args.project.resolve()):raise ProjectError('Output must be outside project root')
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() or target.is_symlink():raise ProjectError('Output exists; refusing overwrite')
            with target.open('x',encoding='utf-8',newline='\n') as f:f.write(output)
        else:print(output,end='')
        return 0 if report['handoffReady'] else 1
    except ProjectError as e:print(f'INPUT_ERROR: {e}',file=sys.stderr);return 2
    except OSError as e:print(f'IO_ERROR: {type(e).__name__}',file=sys.stderr);return 3

if __name__=='__main__':raise SystemExit(main())
