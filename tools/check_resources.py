"""Assert installed resource contracts without modifying or launching the game."""
import argparse
import json
import struct
from pathlib import Path

def effects(path):
    data=path.read_bytes()
    assert data[:8]==b'SPL V1  ',str(path)
    offset=struct.unpack_from('<I',data,0x6a)[0]
    for start in range(offset,len(data)-47,48):
        yield {'opcode':struct.unpack_from('<H',data,start)[0],
               'p1':struct.unpack_from('<i',data,start+4)[0],
               'p2':struct.unpack_from('<I',data,start+8)[0],
               'special':struct.unpack_from('<I',data,start+44)[0],
               'save':struct.unpack_from('<I',data,start+36)[0],
               'bonus':struct.unpack_from('<i',data,start+40)[0],
               'resource':data[start+20:start+28].rstrip(b'\0').decode('ascii',errors='replace').upper()}

def check(game):
    override=game/'override'
    files={p.name.upper():p for p in override.iterdir() if p.is_file()}
    def file(name):return files[name.upper()]
    def rows(name):return [x.split() for x in file(name).read_text(errors='replace').splitlines()[3:] if x.strip()]
    stats={}
    for line in file('STATS.IDS').read_text(errors='replace').splitlines():
        fields=line.split()
        if len(fields)>=2:
            try:stats[fields[1].upper()]=int(fields[0],0)
            except ValueError:pass
    for name,value in {'MAXHITPOINTS':1,'THAC0':7,'PROFICIENCYLONGBOW':104,'LEVELDRAIN':200}.items():
        assert stats.get(name)==value,('Native stat registry corrupted',name,stats.get(name))
    equipment={k:v for k,v in stats.items() if k.startswith('C0_') or k=='IS_FAVORED_SOUL'}
    if 'C0PR#CL.SPL' in files:
        assert equipment and min(equipment.values())>202 and len(set(equipment.values()))==len(equipment),'Equipment stat collision'
        assert any(e['opcode']==401 and e['special']==stats['C0_PROFICIENCYLONGBOW'] for e in effects(file('C0PR#104.SPL'))),'Wrong longbow permission stat'
        assert any(e['opcode']==326 and e['p1']==12 and e['resource']=='C0PR#104' for e in effects(file('C0PR#CL.SPL'))),'Rangers missing longbow permission'
    bard={int(r[0]):[int(x) for x in r[1:]] for r in rows('MXSPLBRD.2DA')}
    assert bard[20][6]==0 and bard[21][6]==1,'RR level-7 spell access'
    assert bard[28][7]==0 and bard[29][7]==1,'RR level-8 spell access'
    hla=rows('LUABBR.2DA')
    assert len({r[1].upper() for r in hla})==len(hla),'Shared HLA tables'
    for row in hla:
        assert row[1].upper().startswith('CK'),row
        assert len('LU'+row[1])<=8,row
        table=file('LU'+row[1]+'.2DA')
        for line in table.read_text(errors='replace').splitlines()[3:]:
            cells=line.split()
            if len(cells)>1 and cells[1].startswith(('GA_','AP_')):
                ref=cells[1][3:].upper()
                if ref.startswith(('RR#','C0','CKR','SGAB')):
                    assert ref+'.SPL' in files,('Missing custom HLA resource',ref)
    for stem,cap,ops in [('RR#BSK00',3,[0,73,278]),('RR#BSK02',4,[0,73,278]),
                          ('C0BDI01B',2,[54]),('C0BDI03B',2,[0]),('C0BDI05B',2,[325]),('C0BDI06B',1,[189])]:
        selected=[x for x in effects(file(stem+'.SPL')) if x['opcode'] in ops]
        assert selected,stem
        assert max(x['p1'] for x in selected)<=cap,stem
    heckle=list(effects(file('CKRHECK.SPL')))
    assert not any(x['opcode']==3 for x in heckle),'Berserk rider remains'
    assert all(x['p1']==25 and x['save']==1 and x['bonus']==0 for x in heckle if x['opcode']==60)
    assert all(x['p1']==1 and x['save']==1 and x['bonus']==0 for x in heckle if x['opcode']==362)
    assert 'GA_CKRHECK' in file('CLABBA03.2DA').read_text(),'Missing Heckle grant'
    assert 'GA_C0A_A01' in file('CLABTH03.2DA').read_text(),'Missing Analyze grant'
    recurring=[p for n,p in files.items() if n.startswith('C0KM#') and n.endswith('.SPL')]
    assert recurring
    assert not any(x['opcode']==261 for p in recurring for x in effects(p)),'Recurring spell refill remains'
    for key,abbrev in hla:
        if key=='C0_KAPELLMEISTER':
            text=file('LU'+abbrev+'.2DA').read_text()
            assert 'RR#BHL05' in text and 'GA_SPCL913' not in text,'Unreconciled BW HLA table'
    clone='not applicable without EEex'
    if 'M_EKCF.LUA' in files:
        for name in ['PROJIMAG.SPL','SIMULACR.SPL']:
            callbacks=[x for x in effects(file(name)) if x['opcode']==402 and x['resource']=='EKCLNFIX']
            assert len(callbacks)==1,('Duplicated/missing EK clone callback',name,len(callbacks))
        clone='one callback per image spell'
    return {'game':str(game),'assertions':'passed','private_hla_tables':len(hla),
            'native_stat_ids':'preserved','distinct_equipment_stats':len(equipment),
            'rr_bard_level7_at':21,'rr_bard_level8_at':29,'heckle':'bounded/saveable',
            'skald_and_inspirations':'capped','recurring_spell_restoration':'removed','eldritch_clone_fix':clone}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('game',type=Path)
    args=parser.parse_args();print(json.dumps(check(args.game.resolve()),indent=2))
