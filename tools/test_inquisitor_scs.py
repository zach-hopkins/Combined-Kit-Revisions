"""Native WeiDU regression for the one-header SR/R + SCS Inquisitor case."""
import argparse,shutil,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def u16(b,o):return struct.unpack_from('<H',b,o)[0]
def u32(b,o):return struct.unpack_from('<I',b,o)[0]
def header(b,i):return b[u32(b,0x64)+40*i:u32(b,0x64)+40*(i+1)]
def effects(b,h):
    return [b[u32(b,0x6a)+48*(u16(h,32)+j):u32(b,0x6a)+48*(u16(h,32)+j+1)] for j in range(u16(h,30))]
def run(exe,game,name):
    r=subprocess.run([str(exe),name,'--noautoupdate','--no-exit-pause','--skip-at-view','--force-install-list','0'],cwd=game,capture_output=True,input=b'')
    if r.returncode:raise AssertionError((r.stdout+r.stderr).decode(errors='replace')[-5000:])
def main():
    p=argparse.ArgumentParser();p.add_argument('--weidu',type=Path,required=True);p.add_argument('--spell',type=Path,required=True);a=p.parse_args()
    before=a.spell.read_bytes();assert u16(before,0x68)==1
    with tempfile.TemporaryDirectory(prefix='ckr-inquisitor-') as tmp:
        game=Path(tmp);(game/'override').mkdir();(game/'lang/en_US').mkdir(parents=True)
        (game/'lang/en_US/dialog.tlk').write_bytes(b'TLK V1  '+struct.pack('<HII',0,0,18))
        (game/'chitin.key').write_bytes(b'KEY V1  '+struct.pack('<IIII',0,0,24,24))
        (game/'engine.lua').write_text('engine_name = "Baldur\'s Gate II - Enhanced Edition"\nengine_mode = 1\n')
        (game/'weidu.conf').write_text('lang_dir = en_US\n')
        shutil.copy2(ROOT/'combined-kit-revisions/lib/inquisitor-scs.tpa',game/'repair.tpa')
        (game/'override/SPCL231.SPL').write_bytes(before)
        (game/'test.tp2').write_text('BACKUP ~backup~\nAUTHOR ~native regression~\nBEGIN ~repair~\nINCLUDE ~repair.tpa~\n')
        run(a.weidu.resolve(),game,'test.tp2');after=(game/'override/SPCL231.SPL').read_bytes()
        assert u16(after,0x68)==255
        original_header=bytearray(header(before,0));original_header[16:18]=b'\0'*2;original_header[32:34]=b'\0'*2
        original_effects=effects(before,header(before,0))
        for i in range(255):
            h=header(after,i);assert u16(h,16)==i+1
            comparable=bytearray(h);comparable[16:18]=b'\0'*2;comparable[32:34]=b'\0'*2
            assert comparable==original_header
            for old,new in zip(original_effects,effects(after,h)):
                if u16(old,0)==58:
                    assert u32(new,4)==3*(i+1)//2 and u32(new,8)==2
                    assert old[:4]+old[12:]==new[:4]+new[12:]
                else:assert old==new
        # Keep all global effects and the complete top-level spell metadata.
        old_global=before[u32(before,0x6a)+48*u16(before,0x6e):u32(before,0x6a)+48*(u16(before,0x6e)+u16(before,0x70))]
        new_global=after[u32(after,0x6a)+48*u16(after,0x6e):u32(after,0x6a)+48*(u16(after,0x6e)+u16(after,0x70))]
        assert old_global==new_global
        assert before[:0x64]==after[:0x64] and before[0x6e:0x72]==after[0x6e:0x72]
        (game/'second.tp2').write_text('BACKUP ~second-backup~\nAUTHOR ~native regression~\nBEGIN ~idempotence~\nINCLUDE ~repair.tpa~\n')
        run(a.weidu.resolve(),game,'second.tp2');assert after==(game/'override/SPCL231.SPL').read_bytes()
        print('PASS: 255 caster levels, 1.5x dispel, original spell/effects preserved, byte-identical second pass')
if __name__=='__main__':main()
