"""Pure-ish, read-only project validation. Input is untrusted local data.

The v1 scope is static PNG, single reference viewport, uniform fit scaling,
image and button components, and an independently reviewed requirements file.
No GUI, engine import, arbitrary scripting, or image rewriting.
"""
from __future__ import annotations
from pathlib import Path
from io import BytesIO
import json, os, re, stat, unicodedata, warnings
from PIL import Image

MAX_JSON=2_000_000
MAX_FILE=16_000_000
MAX_PIXELS=16_000_000
Image.MAX_IMAGE_PIXELS=MAX_PIXELS
ID=re.compile(r'^[a-z][a-z0-9_]{1,63}$')
RESERVED=re.compile(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$')
PROFILES={'mobile_touch_v1':{'button':('default','pressed'),'image':('default',)}}

class ProjectError(Exception): pass

def read_json(root:Path, name:str)->dict:
    p=root/name
    if p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_JSON:
        raise ProjectError(f'{name}: missing, symlinked or over 2 MB')
    try:
        d=json.loads(p.read_bytes().decode('utf-8'))
    except (UnicodeError,ValueError,OSError) as e:
        raise ProjectError(f'{name}: invalid JSON/UTF-8') from e
    if not isinstance(d,dict):raise ProjectError(f'{name}: must be object')
    return d

def ident(value):
    return isinstance(value,str) and bool(ID.fullmatch(value))

def validate_model(req:dict, scr:dict):
    if req.get('schemaVersion')!='1.0' or scr.get('schemaVersion')!='1.0':raise ProjectError('Unsupported schemaVersion (expected 1.0)')
    if not ident(req.get('projectId')) or not ident(scr.get('projectId')):raise ProjectError('Invalid projectId')
    if req.get('profile') not in PROFILES:raise ProjectError('Unknown requirements profile')
    if scr.get('assetRoot')!='assets':raise ProjectError('assetRoot must equal assets')
    for d,key in [(req,'requiredScreens'),(scr,'screens')]:
        if not isinstance(d.get(key),list) or not 1<=len(d[key])<=100:raise ProjectError(f'{key}: expected 1..100 screens')
    if not isinstance(req.get('waivers',[]),list):raise ProjectError('waivers must be an array')
    for screen in req['requiredScreens']:
        if not isinstance(screen,dict) or not ident(screen.get('id')):raise ProjectError('Invalid required screen')
        comps=screen.get('requiredComponents')
        if not isinstance(comps,list) or not 1<=len(comps)<=1000:raise ProjectError('Invalid requiredComponents')
        for c in comps:
            if not isinstance(c,dict) or not ident(c.get('id')) or c.get('kind') not in ('button','image'):
                raise ProjectError('Invalid required component')
            if c['kind']=='button' and not ident(c.get('actionEvent')):raise ProjectError('Button requirement needs actionEvent')
    for screen in scr['screens']:
        if not isinstance(screen,dict) or not ident(screen.get('id')):raise ProjectError('Invalid screen ID')
        layout=screen.get('layout')
        if not isinstance(layout,dict):raise ProjectError('Missing layout')
        viewport=layout.get('referenceViewport')
        if not isinstance(viewport,dict) or any(type(viewport.get(k)) is not int or not 1<=viewport[k]<=8192 for k in ('width','height')):
            raise ProjectError('Invalid reference viewport')
        if layout.get('scaling')!='uniform_fit_center':raise ProjectError('Only uniform_fit_center scaling is supported')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(layout.get('letterboxColor',''))):raise ProjectError('Invalid letterboxColor')
        inset=layout.get('safeAreaInsetsPx')
        if not isinstance(inset,dict) or any(type(inset.get(k)) is not int or not 0<=inset[k]<=8192 for k in ('left','right','top','bottom')):
            raise ProjectError('Invalid safe area insets')
        comps=screen.get('components')
        if not isinstance(comps,list) or not 1<=len(comps)<=1000:raise ProjectError('Invalid screen components')
        for c in comps:
            if not isinstance(c,dict) or not ident(c.get('id')) or c.get('kind') not in ('button','image'):
                raise ProjectError('Invalid component')
            if c.get('fitMode') not in ('contain','cover','stretch'):raise ProjectError('Invalid fitMode')
            if type(c.get('zIndex')) is not int or not -100<=c['zIndex']<=1000:raise ProjectError('Invalid zIndex')
            for field in ('boundsPx',)+(('hitBoxPx',) if c['kind']=='button' else ()):
                r=c.get(field)
                if not isinstance(r,dict) or any(type(r.get(k)) is not int or not 0<=r[k]<=8192 for k in ('x','y')) or any(type(r.get(k)) is not int or not 1<=r[k]<=8192 for k in ('width','height')):
                    raise ProjectError(f'Invalid {field}')
            if c['kind']=='button':
                inter=c.get('interaction')
                if not isinstance(inter,dict) or not ident(inter.get('event')) or len(str(inter.get('behaviorNote','')).strip())<12:
                    raise ProjectError('Button needs event and behaviorNote (12+ characters)')
                if c.get('allowUnsafeArea',False):raise ProjectError('Buttons cannot bypass safe area')
            elif c.get('interaction') or c.get('hitBoxPx'):raise ProjectError('Image component cannot have interaction/hitBox')
            if c.get('allowUnsafeArea',False) and len(str(c.get('unsafeAreaReason','')).strip())<12:
                raise ProjectError('Unsafe area exemption needs reason')
            states=c.get('states')
            if not isinstance(states,list) or len(states)>12:raise ProjectError('Invalid states')
            for state in states:
                if not isinstance(state,dict) or state.get('name') not in ('default','pressed','disabled') or not isinstance(state.get('asset'),str):
                    raise ProjectError('Invalid state')
    for waiver in req.get('waivers',[]):
        if not isinstance(waiver,dict) or any(not ident(waiver.get(k)) for k in ('screenId','componentId')) or waiver.get('state')!='pressed' or len(str(waiver.get('reason','')).strip())<12 or len(str(waiver.get('reviewer','')).strip())<2:
            raise ProjectError('Invalid waiver')

def path_parts(s:str):
    if not s or len(s)>240 or s.startswith('/') or '\\' in s or ':' in s or '\x00' in s or unicodedata.normalize('NFC',s)!=s or not s.lower().endswith('.png'):
        raise ValueError('invalid asset path')
    parts=s.split('/')
    if any(p in ('','.','..') or p.endswith(('.', ' ')) or RESERVED.fullmatch(p) or any(ord(c)<32 for c in p) for p in parts):
        raise ValueError('invalid asset path')
    return parts

def load_png(root:Path, rel:str):
    parts=path_parts(rel)
    base=root/'assets'
    if base.is_symlink():raise ValueError('symlink asset root')
    if os.name=='posix' and hasattr(os,'O_NOFOLLOW'):
        fds=[]
        try:
            fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
            for part in ['assets']+parts[:-1]:
                fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
            filefd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
            try:
                info=os.fstat(filefd)
                if not stat.S_ISREG(info.st_mode):raise ValueError('not regular file')
                if info.st_size>MAX_FILE:raise ValueError('file too large')
                with os.fdopen(filefd,'rb',closefd=False) as f: data=f.read(MAX_FILE+1)
            finally:os.close(filefd)
        finally:
            for fd in reversed(fds):os.close(fd)
    else:
        p=root.resolve()
        for part in ['assets']+parts:
            p=p/part
            if p.is_symlink():raise ValueError('symlink asset')
            if not p.resolve().is_relative_to(root.resolve()):raise ValueError('path escape')
        if not p.is_file() or p.stat().st_size>MAX_FILE:raise ValueError('not regular file or too large')
        data=p.read_bytes()
    if len(data)>MAX_FILE:raise ValueError('file too large')
    with warnings.catch_warnings():
        warnings.simplefilter('error',Image.DecompressionBombWarning)
        with Image.open(BytesIO(data),formats=['PNG']) as im:
            if im.format!='PNG' or im.width>8192 or im.height>8192 or im.width*im.height>MAX_PIXELS:
                raise ValueError('unsupported PNG dimensions')
            im.load()
    return True

def inside(r,box):
    x,y,x2,y2=box
    return r['x']>=x and r['y']>=y and r['x']+r['width']<=x2 and r['y']+r['height']<=y2

def validate(root:Path)->dict:
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ProjectError('Project root missing or symlinked')
    req,scr=read_json(root,'requirements.json'),read_json(root,'screens.json')
    validate_model(req,scr)
    findings=[]
    def add(code,category,path,detail):findings.append({'code':code,'category':category,'severity':'error','path':path,'detail':detail})
    if req['projectId']!=scr['projectId']:add('PROJECT_ID_MISMATCH','requirements','projectId','Project IDs differ')
    rs={s['id']:s for s in req['requiredScreens']};ss={s['id']:s for s in scr['screens']}
    for collection,code in ((req['requiredScreens'],'DUPLICATE_REQUIRED_SCREEN'),(scr['screens'],'DUPLICATE_SCREEN')):
        seen=set()
        for s in collection:
            if s['id'] in seen:add(code,'requirements',s['id'],'Duplicate screen')
            seen.add(s['id'])
    for s in req['requiredScreens']:
        seen=set()
        for c in s['requiredComponents']:
            if c['id'] in seen:add('DUPLICATE_REQUIRED_COMPONENT','requirements',f"{s['id']}/{c['id']}",'Duplicate requirement')
            seen.add(c['id'])
        if s['id'] not in ss:add('REQUIRED_SCREEN_MISSING','requirements',s['id'],'Missing independently required screen')
    waivers={}
    for w in req.get('waivers',[]):
        key=(w['screenId'],w['componentId'],w['state'])
        if key in waivers:add('DUPLICATE_WAIVER','requirements','/'.join(key),'Repeated waiver')
        waivers[key]=w
    used=set();refs=set();case={}
    for s in scr['screens']:
        sid=s['id'];path=f'screens/{sid}'
        if sid not in rs:add('UNREVIEWED_SCREEN','requirements',path,'Screen not in approved requirements')
        required={c['id']:c for c in rs.get(sid,{}).get('requiredComponents',[])}
        comps={c['id']:c for c in s['components']}
        for cid in required:
            if cid not in comps:add('REQUIRED_COMPONENT_MISSING','requirements',path+'/'+cid,'Missing independently required component')
        layout=s['layout'];v=layout['referenceViewport'];i=layout['safeAreaInsetsPx'];w,h=v['width'],v['height']
        safe=(i['left'],i['top'],w-i['right'],h-i['bottom'])
        if safe[2]<=safe[0] or safe[3]<=safe[1]:add('SAFE_AREA_INVALID','layout',path,'Safe area has no positive dimensions')
        seen=set();zs=set()
        for c in s['components']:
            cid=c['id'];cp=path+'/'+cid
            if cid in seen:add('DUPLICATE_COMPONENT','requirements',cp,'Duplicate component ID')
            seen.add(cid)
            if c['zIndex'] in zs:add('DUPLICATE_Z_INDEX','layout',cp,'Ambiguous z-order')
            zs.add(c['zIndex'])
            rc=required.get(cid)
            if rc is None:add('UNREVIEWED_COMPONENT','requirements',cp,'Component not independently required')
            elif rc['kind']!=c['kind']:add('COMPONENT_KIND_MISMATCH','requirements',cp,'Kind differs from requirement')
            r=c['boundsPx']
            if not inside(r,(0,0,w,h)):add('BOUNDS_OUT_OF_VIEWPORT','layout',cp,'Bounds exceed reference viewport')
            if not c.get('allowUnsafeArea',False) and not inside(r,safe):add('BOUNDS_OUT_OF_SAFE_AREA','layout',cp,'Bounds exceed safe area')
            if c['kind']=='button':
                hb=c['hitBoxPx']
                if not inside(hb,safe):add('HITBOX_OUT_OF_SAFE_AREA','layout',cp,'Hitbox exceeds safe area')
                if not inside(r,(hb['x'],hb['y'],hb['x']+hb['width'],hb['y']+hb['height'])):add('HITBOX_SMALLER_THAN_BUTTON','layout',cp,'Hitbox must contain visible bounds')
                if rc and c['interaction']['event']!=rc.get('actionEvent'):add('ACTION_MISMATCH','interactions',cp,'Interaction differs from requirement')
            states=set()
            for st in c['states']:
                if st['name'] in states:add('DUPLICATE_STATE','requirements',cp+'/'+st['name'],'Duplicate state')
                states.add(st['name']);ref=st['asset'];refs.add(ref)
                k=unicodedata.normalize('NFC',ref).casefold()
                if k in case and case[k]!=ref:add('ASSET_CASE_COLLISION','assets',cp,'Case/Unicode collision')
                case[k]=ref
            for required_state in PROFILES[req['profile']][c['kind']]:
                key=(sid,cid,required_state)
                if key in waivers:
                    used.add(key)
                    if required_state in states:add('WAIVER_CONFLICT','requirements',cp,'Waived state also present')
                elif required_state not in states:add('REQUIRED_STATE_MISSING','requirements',cp+'/'+required_state,'Required by independent profile')
    for key in waivers:
        if key not in used:add('UNKNOWN_WAIVER','requirements','/'.join(key),'Waiver does not match required state')
    for ref in sorted(refs):
        try:load_png(root,ref)
        except FileNotFoundError:add('ASSET_NOT_FOUND','assets',ref,'Referenced file missing')
        except (ValueError,OSError,Image.UnidentifiedImageError):add('ASSET_INVALID','assets',ref,'PNG missing, unsafe, invalid or exceeds limits')
    findings.sort(key=lambda x:(x['path'],x['code'],x['detail']))
    categories=('requirements','assets','layout','interactions')
    assessment={cat:('fail' if any(f['category']==cat for f in findings) else 'pass') for cat in categories}
    return {'reportSchemaVersion':'1.0','projectId':scr['projectId'],'profile':req['profile'],'assessment':assessment,'findings':findings,'handoffReady':all(x=='pass' for x in assessment.values()),'statistics':{'screens':len(scr['screens']),'components':sum(len(s['components']) for s in scr['screens']),'referencedAssets':len(refs)}}

def serialize(report):return json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+'\n'
