from pathlib import Path
import pcbnew as p
root=Path(__file__).resolve().parents[1]
b=p.LoadBoard(str(root/'VL53L9.kicad_pcb'))
dst=root/'tmp/routing/VL53L9.dsn'
assert p.ExportSpecctraDSN(b,str(dst))
txt=dst.read_text()
rules='''
    (autoroute_settings
      (layer_rule F.Cu (active on) (preferred_direction horizontal))
      (layer_rule In1.Cu (active off) (preferred_direction horizontal))
      (layer_rule In2.Cu (active off) (preferred_direction vertical))
      (layer_rule B.Cu (active on) (preferred_direction vertical))
    )'''
txt=txt.replace('    (boundary',rules+'\n    (boundary',1)
for layer in ['In1.Cu','In2.Cu']:
    txt=txt.replace(f'(layer {layer}\n      (type signal)',f'(layer {layer}\n      (type power)')
# KiCad relaxes smd_smd clearance in DSN; keep the real board rule here.
txt=txt.replace('(clearance 37.5 (type smd_smd))','(clearance 150 (type smd_smd))')
dst.write_text(txt)
print('DSN exported. Routing confined to outer layers; inner planes reserved.')
