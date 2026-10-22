"""Build a single WeiDU installer from pinned, independently downloaded sources.

Only Python's standard library is required. Original source trees are never edited.
Generated integration sources/assets stay in build/, outside the Git repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TP2 = 'combined-kit-revisions/combined-kit-revisions.tp2'
INSTALLERS = {
    'RR': 'rr/setup-rr.tp2',
    'BW': 'BardicWonders/Setup-BardicWonders.tp2',
    'AK': 'ArtisansKitpack/ArtisansKitpack.TP2',
    'AK_TWEAK': 'ArtisansKitpack_tweak/ArtisansKitpack_tweak.TP2',
    'AK_NPC': 'ArtisansKitpack_npc/ArtisansKitpack_npc.TP2',
}
LIBRARIES = {
    'RR': ['rr#afix.tph', 'rr#bg1v.tpa', 'rr#sp2in.tph', 'fl#bg1pal.tpa', 'lib.tpa'],
    'AK': ['2daHandling.tph', 'alter_script.tpa', 'ClassSpellTool.tpa', 'a7#add_kit_ex.tpa',
           'kit_strref.tpa', 'RA_SPHERE_COMPAT.tpa', 'eet.tph', 'functions.tph',
           'hla_actions.tpa', 'replace_multiline.tpa', 'x_force.tph', 'extend_tables.tpa'],
    'BW': ['a7#add_kit_ex.tpa', 'kit_strref.tpa', 'alter_script.tpa', 'functions.tph',
           'hla_actions.tpa', 'more_hla.tpa', 'macros.tpa', 'ClassSpellTool.tpa', 'replace_multiline.tpa'],
}
TEXT_EXTENSIONS = {'.tpa', '.tph', '.tp2', '.baf', '.d'}

def read_text(path):
    data = path.read_bytes()
    try: return data.decode('utf-8-sig')
    except UnicodeDecodeError: return data.decode('cp1252')

def mask_comments(text):
    """Blank comments, preserving strings, offsets and newlines for declaration slicing."""
    chars = list(text)
    i = 0
    quote = None
    while i < len(text):
        if quote:
            if text.startswith(quote, i): i += len(quote); quote = None
            else: i += 1
        elif text.startswith('~~~~~', i): quote = '~~~~~'; i += 5
        elif text[i] in '~"': quote = text[i]; i += 1
        elif text.startswith('//', i):
            end = text.find('\n', i)
            if end < 0: end = len(text)
            for j in range(i, end): chars[j] = ' '
            i = end
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            if end < 0: raise ValueError('Unterminated block comment')
            end += 2
            for j in range(i, end):
                if chars[j] not in '\r\n': chars[j] = ' '
            i = end
        else: i += 1
    return ''.join(chars)

def mask_literals(text):
    chars=list(text)
    i=0
    while i<len(text):
        delimiter='~~~~~' if text.startswith('~~~~~',i) else text[i] if text[i] in '~"' else None
        if not delimiter: i+=1; continue
        end=text.find(delimiter,i+len(delimiter))
        if end<0: raise ValueError('Unterminated WeiDU string')
        end+=len(delimiter)
        for j in range(i,end):
            if chars[j] not in '\r\n':chars[j]=' '
        i=end
    return ''.join(chars)

def parse_components(text):
    masked = mask_comments(text)
    code_only = mask_literals(masked)
    pattern = re.compile(r'^BEGIN\s+(~[^~]*~|"[^"]*"|@\d+)\s+DESIGNATED\s+(\d+)', re.M)
    matches = [m for m in pattern.finditer(masked) if code_only[m.start():m.start()+5]=='BEGIN']
    result = {}
    for i, m in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        body = text[m.end():end]
        flags = []
        kept = []
        # Upstream component flags occupy individual lines; reject unsupported forms.
        body_mask=mask_comments(body)
        for line, clean_line, code_line in zip(body.splitlines(keepends=True), body_mask.splitlines(keepends=True),mask_literals(body_mask).splitlines(keepends=True)):
            clean = clean_line.strip()
            if re.match(r'^(GROUP|SUBCOMPONENT|REQUIRE_COMPONENT|FORBID_COMPONENT|REQUIRE_PREDICATE|INSTALL_BY_DEFAULT|DEPRECATED|NO_LOG_RECORD)\b', code_line.strip()):
                flags.append(clean)
            else: kept.append(line)
        result[int(m[2])] = {'label': m[1], 'body': ''.join(kept), 'flags': flags}
    if not result: raise ValueError('No installer declarations found')
    return result

def acquire(entry, local):
    destination = ROOT/'.cache'/entry['id']
    if entry['id'] in local:
        source = Path(local[entry['id']]).resolve()
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        if head != entry['commit']: raise ValueError(f"Wrong commit for {entry['id']}: {head}")
        status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=source, text=True)
        if status.strip(): raise ValueError(f"Modified tracked source files in {source}")
        return source
    stamp = destination/'.ckr-commit'
    if stamp.exists() and stamp.read_text().strip() == entry['commit']: return destination
    if destination.exists(): raise ValueError(f'Refusing to replace mismatched source cache {destination}')
    archive = ROOT/'.cache'/f"{entry['id']}-{entry['commit']}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://codeload.github.com/{entry['repository']}/zip/{entry['commit']}"
    print(f"Downloading {entry['id']} at {entry['commit']}", flush=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Combined-Kit-Revisions'}), timeout=120) as response:
        archive.write_bytes(response.read())
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        top = members[0].filename.split('/')[0]
        for member in members:
            relative = Path(*Path(member.filename).parts[1:])
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe archive path')
            target = destination/relative
            if member.is_dir(): target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(member))
    stamp.write_text(entry['commit']+'\n')
    return destination

def original_provider(path):
    name = path.replace('\\', '/').lower()
    if 'artisanskitpack_tweak' in name: return 'AK_TWEAK'
    if 'artisanskitpack_npc' in name: return 'AK_NPC'
    if 'artisanskitpack' in name: return 'AK'
    if 'bardicwonders' in name: return 'BW'
    if name.rsplit('/',1)[-1] in ('setup-rr.tp2','rr.tp2'): return 'RR'
    return None

def build(args):
    lock = json.loads((ROOT/'upstream.lock.json').read_text())
    rules = json.loads((ROOT/'rules.json').read_text())
    local = dict(value.split('=',1) for value in args.source)
    inputs = {e['id']: acquire(e, local) for e in lock['upstreams']}
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Never erase the destination or a source tree; stage into a new/owned build directory.
    stamp = out/'.ckr-build'
    if any(out.iterdir()) and not stamp.exists(): raise ValueError('Output must be empty or an existing CKR build')
    stamp.write_text(rules['version']+'\n')
    for e in lock['upstreams']:
        for folder in e['folders']:
            shutil.copytree(inputs[e['id']]/folder, out/folder, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('backup', '*.DEBUG', '__pycache__'))
    module = out/'combined-kit-revisions'
    generated = module/'generated'
    generated.mkdir(parents=True, exist_ok=True)
    components = {p:parse_components(read_text(out/file)) for p,file in INSTALLERS.items()}
    base = [tuple(x) for x in rules['base_order']]
    excluded = {(p,n) for p,ns in rules['excluded'].items() for n in ns}
    optional = {(p,n): rules['id_offsets'][p]+n for p,cs in components.items()
                for n in cs if (p,n) not in base and (p,n) not in excluded}
    if len(set(optional.values())) != len(optional): raise ValueError('Optional component ID collision')

    def check(p, n):
        if (p,n) in base: return f'(CKR_{p}_{n} = 1)'
        if (p,n) in optional: return f'(MOD_IS_INSTALLED ~{TP2}~ ~{optional[p,n]}~)'
        if n not in components.get(p, {}): raise ValueError(f'Unknown dependency {p}:{n}')
        return '0'  # Deliberately excluded alternative, not an upstream installer to run.

    mod_pattern = re.compile(r'MOD_IS_INSTALLED\s+(~[^~]+~|"[^"]+")\s+(~\d+~|"\d+"|\d+)',re.I)
    def transform(text, folder):
        text = text.replace('%MOD_FOLDER%', folder)
        def rewrite(m):
            if m[1][1:-1].replace('\\','/').lower().rsplit('/',1)[-1]=='eeex.tp2' and int(m[2].strip('~"'))==0:
                return '(CKR_EEEX = 1)'
            p = original_provider(m[1][1:-1])
            if not p: return m[0]
            return check(p,int(m[2].strip('~"')))
        return mod_pattern.sub(rewrite,text)

    # Runtime includes must use the same ownership/dependency mapping as their callers.
    for e in lock['upstreams']:
        for folder in e['folders']:
            effective_folder = 'ArtisansKitpack' if e['id']=='AK' else folder
            for file in (out/folder).rglob('*'):
                if file.is_file() and file.suffix.lower() in TEXT_EXTENSIONS:
                    file.write_text(transform(read_text(file),effective_folder),encoding='utf-8',newline='\n')
    # Upstream embeds a Garrick prompt inside the Troubadour kit. The dedicated
    # AK NPC component already provides this choice; never prompt/change him in base.
    troubadour=out/'BardicWonders/lib/troubadour.tpa'
    text=read_text(troubadour)
    anchor='ACTION_IF FILE_EXISTS_IN_GAME ~garric.cre~'
    if text.count(anchor)!=1: raise ValueError('Troubadour NPC boundary changed upstream')
    troubadour.write_text(text[:text.index(anchor)],encoding='utf-8')

    # Companion spellbook grants belong in their own NPC component, not the spell pack.
    spells=out/'BardicWonders/lib/new_spells.tpa'
    text=read_text(spells)
    start=text.index('COPY_EXISTING_REGEXP GLOB ~.+\\.CRE~',text.index('~JADERMIN.cre~'))
    end=text.index('ACTION_IF ',text.index('~VOGHILN~',start))
    companion_spells=text[start:end]
    if '~HAERDALIS~' not in companion_spells or '~VOGHILN~' not in companion_spells:
        raise ValueError('Companion spell grant boundary changed upstream')
    spells.write_text(text[:start]+text[end:],encoding='utf-8')
    # English is the first supported language. Convert legacy RR English strings to UTF-8.
    for tra in (out/'rr/tra/english').glob('*.tra'):
        tra.write_text(read_text(tra),encoding='utf-8',newline='\n')

    init_files={}
    for p in ['RR','AK','BW']:
        folder={'RR':'rr','AK':'ArtisansKitpack','BW':'BardicWonders'}[p]
        available={f.name.lower():f.name for f in (out/folder/'lib').iterdir()}
        init=f'ACTION_IF NOT (~%CKR_PROVIDER%~ STRING_EQUAL ~{p}~) BEGIN\nOUTER_SPRINT MOD_FOLDER ~{folder}~\n'
        for lib in LIBRARIES[p]:
            init+=f'INCLUDE ~{folder}/lib/{available[lib.lower()]}~\n'
        if p=='RR':
            init+='LOAD_TRA ~rr/tra/english/game.tra~\nLOAD_TRA ~rr/tra/english/setup.tra~\nLOAD_TRA ~rr/tra/ee/english/game.tra~\n'
        init+=f'OUTER_SPRINT CKR_PROVIDER ~{p}~\nEND\n'
        (generated/f'init-{p}.tpa').write_text(init,encoding='utf-8')
        init_files[p]=f'combined-kit-revisions/generated/init-{p}.tpa'

    def flag_condition(flag):
        match = re.match(r'(REQUIRE_COMPONENT|FORBID_COMPONENT)\s+(~[^~]+~|"[^"]+")\s+(~\d+~|"\d+"|\d+)\s+(.+)',flag)
        if match:
            verb,path,num,message=match.groups()
            p=original_provider(path[1:-1]);n=int(num.strip('~"'))
            cond=check(p,n) if p else f'MOD_IS_INSTALLED {path} {num}'
            cond=transform(cond,'')
            if verb=='FORBID_COMPONENT': cond=f'NOT ({cond})'
            return cond,message
        if flag.startswith('REQUIRE_PREDICATE '):
            rest=flag[len('REQUIRE_PREDICATE '):]
            match=re.match(r'(.+?)\s+(~[^~]*~|"[^"]*"|@\d+)\s*$',rest)
            if not match: raise ValueError(f'Unsupported predicate {flag}')
            return transform(match[1],''),match[2]
        return None

    def stable_condition(condition):
        # WeiDU evaluates menu predicates before ALWAYS. Menu expressions must
        # inspect installed state, never the transient per-base action variables.
        def stable_base(m):
            p,n=m[1],int(m[2])
            predicate=f'(MOD_IS_INSTALLED ~{TP2}~ ~0~)'
            if any('EEEX' in f.upper() for f in components[p][n]['flags']):
                predicate+=' AND (FILE_EXISTS_IN_GAME ~M___EEex.lua~ OR MOD_IS_INSTALLED ~EEex/EEex.tp2~ ~1~)'
            return '('+predicate+')'
        condition=re.sub(r'CKR_(AK|BW|RR)_(\d+)\s*=\s*1',stable_base,condition)
        condition=condition.replace('CKR_EEEX = 1','(FILE_EXISTS_IN_GAME ~M___EEex.lua~ OR MOD_IS_INSTALLED ~EEex/EEex.tp2~ ~1~)')
        return condition

    catalog=[]
    for p,cs in components.items():
        for n,c in cs.items():
            folder='ArtisansKitpack' if p.startswith('AK') else 'rr' if p=='RR' else 'BardicWonders'
            conditions=[flag_condition(f) for f in c['flags']]
            conditions=[x for x in conditions if x]
            body=transform(c['body'],folder)
            provider=p.split('_')[0]
            action=f'INCLUDE ~{init_files[provider]}~\n'+body
            (generated/f'{p}-{n}.tpa').write_text(action,encoding='utf-8')
            catalog.append({'origin':p,'upstream_component':n,'label':c['label'],
                            'mode':'base' if (p,n) in base else 'excluded' if (p,n) in excluded else 'optional',
                            'component':0 if (p,n) in base else optional.get((p,n)),
                            'conditions':conditions})

    # Human-readable labels are resolved without loading game files.
    rr_labels={int(m[1]):m[2] for m in re.finditer(r'@(\d+)\s*=\s*~([^~]*)~',read_text(out/'rr/tra/english/setup.tra'),re.S)}
    def label(p,c):
        value=c['label']
        return rr_labels[int(value[1:])] if value.startswith('@') else value[1:-1]

    header=f'''BACKUP ~weidu_external/backup/combined-kit-revisions~
AUTHOR ~zach-hopkins; integration of aVENGER/Wisp and The Artisan~
VERSION ~{rules['version']}~
README ~combined-kit-revisions/README.md~
ALWAYS
  OUTER_SPRINT CKR_PROVIDER ~~
  OUTER_SET CKR_EEEX = FILE_EXISTS_IN_GAME ~M___EEex.lua~ OR MOD_IS_INSTALLED ~EEex/EEex.tp2~ ~1~
  OUTER_SET CKR_BASE_PRESENT = MOD_IS_INSTALLED ~{TP2}~ ~0~
'''
    for p,n in base:
        guard=' AND CKR_EEEX' if any('EEEX' in x.upper() for x in components[p][n]['flags']) else ''
        header+=f'  OUTER_SET CKR_{p}_{n} = CKR_BASE_PRESENT{guard}\n'
    header+='END\nLANGUAGE ~English~ ~english~ ~rr/tra/english/game.tra~ ~rr/tra/english/setup.tra~ ~rr/tra/ee/english/game.tra~\n\n'
    main=header+'''BEGIN ~Combined Kit Revisions: Opinionated class and kit base (RR bard spell progression included)~ DESIGNATED 0
GROUP ~Classes and kits~
REQUIRE_PREDICATE GAME_IS ~bg2ee eet~ ~Combined Kit Revisions currently supports BG2EE and EET.~
'''
    # Refuse existing competing originals rather than stacking/replacing an installed campaign.
    for p,file in INSTALLERS.items():
        for n in components[p]:
            if p in ['AK_NPC','AK_TWEAK']:continue
            main+=f'ACTION_IF MOD_IS_INSTALLED ~{file}~ ~{n}~ BEGIN FAIL ~Remove the standalone {p} installation before installing Combined Kit Revisions on a new build.~ END\n'
    for p,n in base:
        conditions=next(x['conditions'] for x in catalog if x['origin']==p and x['upstream_component']==n)
        condition=' AND '.join(f'({x[0]})' for x in conditions) or '1'
        main+=f'''\nPRINT ~[CKR base / {p}] {label(p,components[p][n]).replace('~','-')}~
ACTION_IF {condition} BEGIN
  INCLUDE ~combined-kit-revisions/generated/{p}-{n}.tpa~
  OUTER_SET CKR_{p}_{n} = 1
END ELSE BEGIN
  PRINT ~[CKR] Skipped {p}:{n}: game/engine or kit prerequisite is unavailable.~
END
'''
    main+='INCLUDE ~combined-kit-revisions/lib/curated.tpa~\n'
    for (p,n),new_id in optional.items():
        c=components[p][n]
        title=label(p,c).replace("Artisan's Kitpack: ",'').replace('Bardic Wonders: ','')
        group='NPC choices' if p=='AK_NPC' else 'Optional tweaks and content'
        origin=p.split('_')[0]
        main+=f'\nBEGIN ~[{origin}] {title}~ DESIGNATED {new_id}\nGROUP ~{group}~\n'
        main+=f'REQUIRE_COMPONENT ~{TP2}~ ~0~ ~Install the Combined Kit Revisions base first.~\n'
        for f in c['flags']:
            condition=flag_condition(f)
            if condition: main+=f'REQUIRE_PREDICATE {stable_condition(condition[0])} {condition[1]}\n'
            elif f.startswith('SUBCOMPONENT '):
                sub_label=label(p,{'label':f[len('SUBCOMPONENT '):].strip()})
                main+='SUBCOMPONENT ~['+origin+'] '+sub_label+'~\n'
        main+=f'INCLUDE ~combined-kit-revisions/generated/{p}-{n}.tpa~\n'
        # Reconcile tables and inherited rules after any optional component.
        main+='INCLUDE ~combined-kit-revisions/lib/finalize.tpa~\n'
    main+=f'''\nBEGIN ~[BW] Teach new bard spells to Haer'Dalis and Voghiln~ DESIGNATED 90001
GROUP ~NPC choices~
REQUIRE_COMPONENT ~{TP2}~ ~0~ ~Install the CKR base first.~
REQUIRE_COMPONENT ~{TP2}~ ~{optional['BW',2008]}~ ~Install the BW new bard spells component first.~
INCLUDE ~combined-kit-revisions/generated/init-BW.tpa~
{companion_spells}
'''
    (module/'combined-kit-revisions.tp2').write_text(main,encoding='utf-8')
    for directory in ['lib','docs']:
        shutil.copytree(ROOT/'combined-kit-revisions'/directory,module/directory,dirs_exist_ok=True)
    (module/'README.md').write_text((ROOT/'README.md').read_text(encoding='utf-8').replace('combined-kit-revisions/docs/','docs/'),encoding='utf-8')
    shutil.copy2(ROOT/'upstream.lock.json',module/'upstream.lock.json')
    shutil.copy2(ROOT/'rules.json',module/'rules.json')
    (module/'component-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    menu=[{'id':0,'name':'Opinionated class and kit base (RR bard spell progression included)','group':'Classes and kits'}]
    for (p,n),new_id in optional.items():
        menu.append({'id':new_id,'name':'['+p.split('_')[0]+'] '+label(p,components[p][n]),
                     'group':'NPC choices' if p=='AK_NPC' else 'Optional tweaks and content'})
    menu.append({'id':90001,'name':"[BW] Teach new bard spells to Haer'Dalis and Voghiln",'group':'NPC choices'})
    if len({x['id'] for x in menu})!=len(menu):raise ValueError('Final menu ID collision')
    (module/'component-menu.json').write_text(json.dumps(menu,indent=2)+'\n',encoding='utf-8')
    (module/'build-provenance.json').write_text(json.dumps({'version':rules['version'],'upstreams':lock['upstreams'],
        'installer_sha256':hashlib.sha256(main.encode()).hexdigest()},indent=2)+'\n')
    if args.weidu:
        shutil.copy2(args.weidu,out/'setup-combined-kit-revisions.exe')
    # The assembled package exposes CKR only; imported standalone installers
    # would otherwise offer competing menus against transformed dependency code.
    for file in INSTALLERS.values():
        target=(out/file).resolve()
        target.relative_to(out)
        target.unlink()
    print(f'Built {len(base)} base selections and {len(optional)+1} optional components in {out}',flush=True)
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',action='append',default=[],metavar='ID=CHECKOUT',help='Use a clean local checkout at the locked commit')
    parser.add_argument('--output',default=str(ROOT/'build/package'))
    parser.add_argument('--weidu',help='Path to WeiDU executable to include in local Windows package')
    build(parser.parse_args())
