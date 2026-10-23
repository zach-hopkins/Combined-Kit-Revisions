"""Reproduce RR's registry corruption and validate preserved IDs/custom allocation."""
import argparse,re,shutil,struct,subprocess,tempfile
from pathlib import Path
from build import ROOT,preserve_rr_stats_ids,read_text

def main():
    p=argparse.ArgumentParser();p.add_argument('--weidu',type=Path,required=True);a=p.parse_args()
    source=read_text(ROOT/'.cache/RR/rr/lib/ds/ds.tph')
    original=re.search(r'DEFINE_ACTION_MACRO reorder_stats_ids BEGIN.*?\nEND\s*\n\s*END(?=\s*\n)',source,re.S)[0]
    repaired=re.search(r'DEFINE_ACTION_MACRO reorder_stats_ids BEGIN.*?\nEND(?=\s*\n)',preserve_rr_stats_ids(source),re.S)[0]
    entries=[f'{i} STAT_{i}' for i in range(1,203)]+[f'{i} ALIAS_{i}' for i in range(1,203)]+['104 PROFICIENCYLONGBOW','200 LEVELDRAIN']
    expected={line.split()[1]:int(line.split()[0]) for line in entries}
    for label,macro in [('original',original),('repaired',repaired)]:
        with tempfile.TemporaryDirectory(prefix='ckr-stat-registry-') as tmp:
            game=Path(tmp);(game/'override').mkdir();(game/'lang/en_US').mkdir(parents=True)
            (game/'chitin.key').write_bytes(b'KEY V1  '+struct.pack('<IIII',0,0,24,24))
            (game/'lang/en_US/dialog.tlk').write_bytes(b'TLK V1  '+struct.pack('<HII',0,0,18))
            (game/'engine.lua').write_text('engine_name = "BG EET registry test"\nengine_mode = 1\n')
            (game/'weidu.conf').write_text('lang_dir = en_US\n')
            (game/'override/stats.ids').write_text('\n'.join(entries)+'\n')
            shutil.copy2(ROOT/'.cache/AK/ArtisansKitpack/lib/functions.tph',game/'functions.tph')
            (game/'test.tp2').write_text('BACKUP ~backup~\nAUTHOR ~test~\nBEGIN ~Registry test~\nINCLUDE ~functions.tph~\n'+macro+'\nLAM reorder_stats_ids\n'+''.join(
                f'LAF ADD_IDS_ENTRY INT_VAR minValue = 1 preferredValue = 200 STR_VAR idsFile = ~stats.ids~ identifier = ~CUSTOM_{i}~ RET value END\n' for i in range(26))+'LAM reorder_stats_ids\n')
            r=subprocess.run([str(a.weidu.resolve()),'test.tp2','--noautoupdate','--no-exit-pause','--skip-at-view','--force-install-list','0'],cwd=game,input=b'',capture_output=True)
            assert not r.returncode and b'SUCCESSFULLY INSTALLED' in r.stdout,(r.stdout+r.stderr).decode(errors='replace')[-4000:]
            (ROOT/f'build/stats-{label}-test.log').write_bytes(r.stdout+r.stderr)
            result={line.split()[1]:int(line.split()[0]) for line in (game/'override/stats.ids').read_text().splitlines() if len(line.split())==2}
            intact=all(result.get(key)==value for key,value in expected.items())
            ids=[result.get(f'CUSTOM_{i}',-1) for i in range(26)]
            valid=len(set(ids))==26 and min(ids)>202 and max(ids)<=255
            print(label,'native intact',intact,'custom ids',ids)
            if label=='original':assert not intact and not valid;print('Reproduced: original RR macro renumbers native stats and collides custom equipment flags')
            else:assert intact and valid;print('PASS: all native IDs/aliases preserved; 26 independent custom stats allocated above 202')

if __name__=='__main__':main()
