from pathlib import Path
import copy,json,shutil,subprocess,sys,os,hashlib
import pytest
from screenledger.core import validate,ProjectError,serialize
from screenledger.cli import main
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def p(tmp_path):
 dest=tmp_path/'project';shutil.copytree(ROOT/'examples/demo',dest);return dest

def edit(p,fn,file='screens.json'):
 path=p/file;data=json.loads(path.read_text());fn(data);path.write_text(json.dumps(data))
def codes(p):return {f['code'] for f in validate(p)['findings']}
def button(d):return d['screens'][0]['components'][1]

def test_complete(p):assert validate(p)['handoffReady']
def test_deterministic(p):assert serialize(validate(p))==serialize(validate(p))
def test_missing_screen(p):
 edit(p,lambda d:d['screens'][0].update(id='different'));assert 'REQUIRED_SCREEN_MISSING' in codes(p)
def test_missing_component(p):
 edit(p,lambda d:d['screens'][0]['components'].pop());assert 'REQUIRED_COMPONENT_MISSING' in codes(p)
def test_omitted_pressed_from_both_artwork_and_state_list(p):
 edit(p,lambda d:button(d)['states'].pop());assert 'REQUIRED_STATE_MISSING' in codes(p)
def test_action_mismatch(p):
 edit(p,lambda d:button(d)['interaction'].update(event='open_settings'));assert 'ACTION_MISMATCH' in codes(p)
def test_missing_layout(p):
 edit(p,lambda d:d['screens'][0].pop('layout'))
 with pytest.raises(ProjectError):validate(p)
def test_safe_area(p):
 edit(p,lambda d:button(d)['boundsPx'].update(x=0));assert 'BOUNDS_OUT_OF_SAFE_AREA' in codes(p)
def test_hitbox(p):
 edit(p,lambda d:button(d)['hitBoxPx'].update(width=20));assert 'HITBOX_SMALLER_THAN_BUTTON' in codes(p)
def test_duplicate_component(p):
 edit(p,lambda d:d['screens'][0]['components'].append(copy.deepcopy(button(d))));assert 'DUPLICATE_COMPONENT' in codes(p)
def test_duplicate_state(p):
 edit(p,lambda d:button(d)['states'].append(copy.deepcopy(button(d)['states'][0])));assert 'DUPLICATE_STATE' in codes(p)
def test_missing_png(p):
 (p/'assets/ui/new_game_pressed.png').unlink();assert 'ASSET_NOT_FOUND' in codes(p)
def test_corrupt_png(p):
 (p/'assets/ui/new_game_pressed.png').write_bytes(b'garbage');assert 'ASSET_INVALID' in codes(p)
def test_path_escape(p):
 edit(p,lambda d:button(d)['states'][0].update(asset='../secret.png'));assert 'ASSET_INVALID' in codes(p)
def test_case_collision(p):
 edit(p,lambda d:button(d)['states'][0].update(asset='ui/new_game_PRESSED.png'));assert 'ASSET_CASE_COLLISION' in codes(p)
def test_no_original_mutation(p):
 files=list((p/'assets/ui').glob('*.png'));before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files};validate(p)
 assert before=={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
def test_waiver_valid(p):
 edit(p,lambda d:button(d)['states'].pop())
 edit(p,lambda d:d['waivers'].append({'screenId':'main_menu','componentId':'new_game','state':'pressed','reason':'Immediate navigation skips the pressed frame','reviewer':'Lead Artist'}),'requirements.json')
 assert validate(p)['handoffReady']
def test_waiver_conflict(p):
 edit(p,lambda d:d['waivers'].append({'screenId':'main_menu','componentId':'new_game','state':'pressed','reason':'Immediate navigation skips the pressed frame','reviewer':'Lead Artist'}),'requirements.json')
 assert 'WAIVER_CONFLICT' in codes(p)
def test_unknown_schema(p):
 edit(p,lambda d:d.update(schemaVersion='9.0'))
 with pytest.raises(ProjectError):validate(p)
def test_cli_success(p,capsys):assert main(['validate','--project',str(p)])==0
def test_cli_failure(p):
 edit(p,lambda d:button(d)['states'].pop());assert main(['validate','--project',str(p)])==1
def test_cli_handoff(p,capsys):
 assert main(['handoff','--project',str(p)])==0;assert 'Ready:' in capsys.readouterr().out
def test_init(tmp_path):
 target=tmp_path/'new';assert main(['init',str(target)])==0;assert validate(target)['handoffReady']
def test_no_overwrite(p,tmp_path):
 target=tmp_path/'out.json';target.write_text('old');assert main(['validate','--project',str(p),'--output',str(target)])==2;assert target.read_text()=='old'
def test_report_outside_project(p):assert main(['validate','--project',str(p),'--output',str(p/'report.json')])==2
def test_symlink_rejected(p,tmp_path):
 if os.name!='posix':pytest.skip('POSIX no-follow test')
 target=tmp_path/'outside.png';target.write_bytes((p/'assets/ui/new_game_pressed.png').read_bytes())
 f=p/'assets/ui/new_game_pressed.png';f.unlink();f.symlink_to(target)
 assert 'ASSET_INVALID' in codes(p)
def test_windows_reserved_path(p):
 edit(p,lambda d:button(d)['states'][0].update(asset='ui/CON.png'));assert 'ASSET_INVALID' in codes(p)
def test_manifest_invalid_json(p):
 (p/'screens.json').write_text('{')
 with pytest.raises(ProjectError):validate(p)
def test_duplicate_z(p):
 edit(p,lambda d:button(d).update(zIndex=0));assert 'DUPLICATE_Z_INDEX' in codes(p)
def test_missing_button_action_note(p):
 edit(p,lambda d:button(d)['interaction'].update(behaviorNote='short'))
 with pytest.raises(ProjectError):validate(p)
