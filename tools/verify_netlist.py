"""Independent checks of KiCad's exported connectivity and assigned footprints."""
from pathlib import Path
import xml.etree.ElementTree as ET
import re, json

root=Path(__file__).resolve().parents[1]
doc=ET.parse(root/'output/VL53L9.net.xml').getroot()
nets={n.attrib['name'].lstrip('/'): {(p.attrib['ref'],p.attrib['pin']) for p in n.findall('node')} for n in doc.findall('nets/net')}
pins={pin:net for net,members in nets.items() for pin in members}
expected={
 'B1':'+3V3','D1':'+3V3','E6':'+2V8','E7':'+2V8','C12':'+1V2','E8':'+1V8',
 'A11':'SCL_1V8','A12':'SDA_1V8','A10':'INTR_1V8','B12':'XSHUT_1V8','D12':'SYNC_1V8','E11':'AP_CLK_12M',
}
grounds='A1 A2 A3 A4 A7 B4 B5 B6 B7 B8 B9 C1 D4 D5 D6 D7 D8 D9 E1 E2 E4 E5 E9 E10'.split()
expected.update({p:'GND' for p in grounds})
for p,net in expected.items(): assert pins[('U1',p)]==net,(p,net,pins.get(('U1',p)))
for p in 'A5 A6 A8 A9 E3 E12'.split():
    net=pins[('U1',p)]
    assert net.startswith('unconnected-') and nets[net]=={('U1',p)}
for p,net in enumerate(['+3V3','GND','HOST_SCL','HOST_SDA','HOST_XSHUT','HOST_INTR'],1): assert pins[('J1',str(p))]==net
for p,net in {'1':'+3V3','14':'+1V8','7':'GND','2':'HOST_SDA','3':'HOST_SCL','4':'HOST_XSHUT','5':'HOST_INTR','13':'SDA_1V8','12':'SCL_1V8','11':'XSHUT_1V8','10':'INTR_1V8'}.items(): assert pins[('U5',p)]==net
for u,rail in [('U2','+2V8'),('U3','+1V8'),('U4','+1V2')]:
    for p,net in {'1':'+3V3','2':'GND','3':'PWR_EN','4':u+'_BYP','5':rail}.items(): assert pins[(u,p)]==net
for p,net in {'1':'+1V8','2':'GND','3':'OSC_12M','4':'+1V8'}.items(): assert pins[('Y1',p)]==net
assert nets['OSC_12M']=={('Y1','3'),('R7','1')}
assert nets['AP_CLK_12M']=={('R7','2'),('U1','E11')}
for c,net in [('C12','+3V3'),('C13','+3V3'),('C14','+2V8'),('C15','+1V8'),('C16','+1V2')]:
    assert pins[(c,'1')]==net and pins[(c,'2')]=='GND'
fpbase=Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')
footprints={}
for c in doc.findall('components/comp'):
    lib,name=c.findtext('footprint').split(':')
    path=(root/'libraries/VL53L9_Local.pretty' if lib=='VL53L9_Local' else fpbase/(lib+'.pretty'))/(name+'.kicad_mod')
    assert path.exists(),path
    padnums=set(re.findall(r'\(pad\s+"?([^"\s()]+)"?\s',path.read_text()))
    used={p for (ref,p) in pins if ref==c.attrib['ref']}
    assert used<=padnums,(c.attrib['ref'],used-padnums)
    footprints[c.attrib['ref']]=str(path)
assert len([p for p in pins if p[0]=='U1'])==42
supplied=root/'LIB_VL53L9CX/VL53L9CX/KiCad/VL53L9CX.kicad_mod'
assert supplied.read_bytes()==Path(footprints['U1']).read_bytes()
erc=json.loads((root/'output/ERC.json').read_text())
assert not any(s['violations'] for s in erc['sheets'])
result={'status':'passed','components':len(footprints),'sensor_pins_checked':42,'ground_pads_checked':len(grounds),'erc_errors_and_warnings':0,'checks':['Sensor pinout vs DS14879 Rev 8','J1 pinout and voltage domains','Translator mapping','Regulator pinouts and rails','Clock path','Five local sensor decoupling capacitors','MIPI and reserved pins isolated','All component footprints exist and contain connected pads','Supplied sensor footprint preserved byte-for-byte']}
(root/'output/verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
