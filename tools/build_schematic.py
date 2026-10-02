"""Build the project-local, I2C-only VL53L9CX schematic. Run from project root."""
from pathlib import Path
import re, uuid, json, shutil, math

ROOT = Path(__file__).resolve().parents[1]
LIB = Path('C:/Program Files/KiCad/10.0/share/kicad/symbols')
ROOT_UUID = '7f5e5dbe-2432-41a3-a9e4-3e719c5bb90d'
def uid(key): return str(uuid.uuid5(uuid.UUID(ROOT_UUID), key))
def q(s): return json.dumps(str(s))
def n(v): return f'{v:.4f}'.rstrip('0').rstrip('.') if isinstance(v, float) else str(v)
def extract(text, start):
    depth=0; quoted=False; escaped=False
    for i in range(start,len(text)):
        c=text[i]
        if escaped: escaped=False; continue
        if c=='\\' and quoted: escaped=True; continue
        if c=='"': quoted=not quoted
        if not quoted:
            if c=='(': depth+=1
            if c==')':
                depth-=1
                if depth==0: return text[start:i+1]
    raise ValueError('Unbalanced expression')
def children(text, tag):
    out=[]; i=1
    while i<len(text)-1:
        if text[i]=='(':
            child=extract(text,i)
            if re.match(r'\('+re.escape(tag)+r'(?:\s|\))',child): out.append(child)
            i+=len(child)
        else: i+=1
    return out
def installed(lib,name):
    txt=(LIB/f'{lib}.kicad_sym').read_text(encoding='utf-8')
    return extract(txt,txt.index(f'(symbol "{name}"'))
def prop(key,value,x=0,y=0,hide=False,size=1.27,justify=''):
    return f'(property {q(key)} {q(value)} (at {n(x)} {n(y)} 0) (effects (font (size {size} {size})){" (justify "+justify+")" if justify else ""}{" hide" if hide else ""}))'
def pin(num,name,x,y,angle,typ='passive',length=2.54):
    return f'(pin {typ} line (at {n(x)} {n(y)} {angle}) (length {length}) (name {q(name)} (effects (font (size 1.016 1.016)))) (number {q(num)} (effects (font (size 1.016 1.016)))))'
def custom(name,pins,w=10.16,h=10.16,fp='',datasheet=''):
    return f'''(symbol "{name}" (pin_names (offset 0.508)) (in_bom yes) (on_board yes)
    {prop('Reference','U',0,h+5.08)} {prop('Value',name,0,h+2.54)} {prop('Footprint',fp,hide=True)} {prop('Datasheet',datasheet,hide=True)}
    (symbol "{name}_0_1" (rectangle (start {-w} {h}) (end {w} {-h}) (stroke (width 0.254) (type default)) (fill (type background))))
    (symbol "{name}_1_1" {''.join(pins)}))'''

symbols={}
for lib,name in [('Device','R'),('Device','C'),('power','PWR_FLAG'),('Connector_Generic','Conn_01x06'),('Oscillator','ECS-2520MV-xxx-xx')]:
    symbols[f'{lib}:{name}']=installed(lib,name)

# Preserve every supplied pad number and pin position, but add electrical types for ERC.
supplier=(ROOT/'LIB_VL53L9CX/VL53L9CX/KiCad/VL53L9CX.kicad_sym').read_text()
raw=children(supplier,'symbol')[0]
sensorpins=[]
for p in children(raw,'pin'):
    name=re.search(r'\(name "([^"]+)"',p)[1]
    typ='power_in' if name.startswith(('VSS','VBAT','AVDD')) or name in ('DVDD','IOVDD') else 'bidirectional'
    if name in ('SCL','XSHUT','AP_CLK'): typ='input'
    if name in ('DATA_P','DATA_N','CLK_P','CLK_N'): typ='output'
    if name.startswith('RSVD'): typ='no_connect'
    sensorpins.append(p.replace('(pin passive ',f'(pin {typ} ',1))
sensor=f'''(symbol "VL53L9CX" (in_bom yes) (on_board yes)
 {prop('Reference','U',21.59,10.16)} {prop('Value','VL53L9CX',21.59,7.62)}
 {prop('Footprint','VL53L9_Local:VL53L9CX',hide=True)}
 {prop('Datasheet','https://www.st.com/resource/en/datasheet/vl53l9cx.pdf',hide=True)}
 (symbol "VL53L9CX_0_1" {''.join(children(raw,'rectangle'))})
 (symbol "VL53L9CX_1_1" {''.join(sensorpins)}))'''
symbols['VL53L9_Local:VL53L9CX']=sensor
regpins=[pin('1','IN',-10.16,2.54,0,'power_in'),pin('3','EN',-10.16,-2.54,0,'input'),pin('5','OUT',10.16,2.54,180,'power_out'),pin('4','BYP',10.16,-2.54,180),pin('2','GND',0,-10.16,90,'power_in')]
for v in ('12','18','28'):
    name=f'LDK130M{v}R'
    symbols['VL53L9_Local:'+name]=custom(name,regpins,7.62,7.62,'Package_TO_SOT_SMD:SOT-23-5','https://www.st.com/resource/en/datasheet/ldk130.pdf')
transpins=[pin('1','VCCA',-5.08,15.24,270,'power_in'),pin('14','VCCB',5.08,15.24,270,'power_in'),pin('7','GND',0,-15.24,90,'power_in'),pin('8','EN',-15.24,-7.62,0,'input'),pin('6','NC',15.24,-7.62,180,'no_connect'),pin('9','NC',15.24,-10.16,180,'no_connect')]
for k,y in enumerate([7.62,3.81,0,-3.81]):
    transpins += [pin(str(2+k),f'A{k+1}',-15.24,y,0,'bidirectional'),pin(str(13-k),f'B{k+1}',15.24,y,180,'bidirectional')]
symbols['VL53L9_Local:PI4ULS3V204LEX']=custom('PI4ULS3V204LEX',transpins,12.7,12.7,'Package_SO:TSSOP-14_4.4x5mm_P0.65mm','https://www.diodes.com/datasheet/download/PI4ULS3V204.pdf')

items=[]; parts=[]; placed={}; seq=0
def wire(a,b):
    global seq
    seq+=1
    items.append(f'(wire (pts (xy {n(a[0])} {n(a[1])}) (xy {n(b[0])} {n(b[1])})) (stroke (width 0) (type default)) (uuid {uid("wire"+str(seq))}))')
def label(net,x,y,angle=0):
    global seq
    seq+=1
    items.append(f'(label {q(net)} (at {n(x)} {n(y)} 0) (effects (font (size 1.016 1.016)) (justify {"right" if angle==180 else "left"} bottom)) (uuid {uid("label"+str(seq))}))')
def text(txt,x,y,size=1.27):
    global seq
    seq+=1
    items.append(f'(text {q(txt)} (at {n(x)} {n(y)} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {uid("text"+str(seq))}))')
def place(lib,ref,value,x,y,fp=None,mpn='',role='',dnp=False):
    s=symbols[lib]; pins=[]
    for sub in children(s,'symbol'): pins+=children(sub,'pin')
    pd={}
    for p in pins:
        num=re.search(r'\(number "([^"]+)"',p)[1]
        a=re.search(r'\(at ([^ ]+) ([^ ]+) ([^)]+)\)',p)
        pd[num]=(round(x+float(a[1]),4),round(y-float(a[2]),4),int(a[3]))
    if fp is None:
        m=re.search(r'\(property "Footprint" "([^"]*)"',s); fp=m[1] if m else ''
    m=re.search(r'\(property "Datasheet" "([^"]*)"',s); ds=m[1] if m else ''
    ispower=ref.startswith('#')
    if lib=='Device:R' or lib=='Device:C':
        props=prop('Reference',ref,x+2.54,y-1.27,justify='left')+prop('Value',value,x+2.54,y+1.27,justify='left')
    elif 'VL53L9CX' in lib:
        props=prop('Reference',ref,x+21.59,y-10.16)+prop('Value',value,x+21.59,y-7.62)
    elif 'LDK130' in lib:
        props=prop('Reference',ref,x,y-12.7)+prop('Value',value,x,y-10.16)
    elif 'PI4ULS' in lib:
        props=prop('Reference',ref,x+22.86,y-22.86,justify='left')+prop('Value',value,x+22.86,y-20.32,justify='left')
    elif ref=='Y1':
        props=prop('Reference',ref,x+15.24,y-15.24,justify='left')+prop('Value',value,x+15.24,y-12.7,justify='left')
    else:
        tops=[p[1] for p in pd.values()]; yy=min(tops)-5.08
        props=prop('Reference',ref,x,yy,ispower)+prop('Value',value,x,yy+2.54,ispower)
    props+=prop('Footprint',fp,x,y,True)+prop('Datasheet',ds,x,y,True)
    props+=prop('MPN',mpn,x,y,True)+prop('Function',role,x,y,True)
    items.append(f'''(symbol (lib_id {q(lib)}) (at {n(x)} {n(y)} 0) (unit 1) (in_bom {"no" if ispower else "yes"}) (on_board {"no" if ispower else "yes"}) (dnp {"yes" if dnp else "no"}) (uuid {uid(ref)})
      {props} {''.join(f'(pin {q(k)} (uuid {uid(ref+"pin"+k)}))' for k in pd)}
      (instances (project "VL53L9" (path "/{ROOT_UUID}" (reference {q(ref)}) (unit 1)))))''')
    placed[ref]=pd
    if not ispower: parts.append(dict(reference=ref,value=value,mpn=mpn,footprint=fp,function=role,dnp=dnp))
    return pd
def connect(ref,pnum,net,length=5.08):
    x,y,a=placed[ref][str(pnum)]
    if net is None:
        items.append(f'(no_connect (at {n(x)} {n(y)}) (uuid {uid(ref+"nc"+str(pnum))}))'); return
    dx,dy={0:(-length,0),180:(length,0),90:(0,length),270:(0,-length)}[a]
    end=(round(x+dx,4),round(y+dy,4)); wire((x,y),end)
    label(net,*end,180 if a==0 else 0)
def connects(ref,mapping):
    for p,net in mapping.items(): connect(ref,p,net)
capcount=0; rcount=0
def cap(value,x,y,net,role,mpn=''):
    global capcount
    capcount+=1; ref=f'C{capcount}'
    place('Device:C',ref,value,x,y,'Capacitor_SMD:C_0402_1005Metric',mpn,role)
    connects(ref,{'1':net,'2':'GND'}); return ref
def res(value,x,y,top,bottom,role,mpn='',dnp=False):
    global rcount
    rcount+=1; ref=f'R{rcount}'
    place('Device:R',ref,value,x,y,'Resistor_SMD:R_0402_1005Metric',mpn,role,dnp)
    connects(ref,{'1':top,'2':bottom}); return ref

text('VL53L9CX | I2C-only sensor breakout',15.24,15.24,2.54)
text('3.3 V input and host logic / local 1.8 V I/O / onboard 12 MHz clock',15.24,21.59,1.524)
text('01  POWER SUPPLIES',15.24,34.29,1.778)
for i,(v,rail,x) in enumerate([('28','+2V8',50.8),('18','+1V8',127.0),('12','+1V2',203.2)],start=2):
    ref=f'U{i}'; name=f'LDK130M{v}R'
    place('VL53L9_Local:'+name,ref,name,x,58.42,mpn=name,role=rail+' regulator')
    connects(ref,{'1':'+3V3','2':'GND','3':'PWR_EN','4':f'{ref}_BYP','5':rail})
    cap('1uF',x-20.32,88.9,'+3V3',ref+' input','GRM155R6YA105KE11D')
    cap('10nF',x,88.9,f'{ref}_BYP',ref+' bypass','04023D103KAT2A')
    cap('10uF',x+20.32,88.9,rail,ref+' output','GRJ155R60J106ME11D')
res('47k',251.46,58.42,'+3V3','PWR_EN','Enable all regulators','ERJ2RKF4702X')
text('LDOs: 300 mA rated. Confirm dissipation and effective ceramic capacitance in layout.',15.24,100.33)

text('02  HOST / 3.3 V TO 1.8 V TRANSLATION',15.24,113.03,1.778)
place('Connector_Generic:Conn_01x06','J1','HOST_3V3',45.72,147.32,'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical',role='Power and 3.3 V host interface')
connects('J1',{'1':'+3V3','2':'GND','3':'HOST_SCL','4':'HOST_SDA','5':'HOST_XSHUT','6':'HOST_INTR'})
place('VL53L9_Local:PI4ULS3V204LEX','U5','PI4ULS3V204LEX',134.62,157.48,mpn='PI4ULS3V204LEX',role='I2C, XSHUT and INTR translation')
connects('U5',{'1':'+3V3','14':'+1V8','7':'GND','8':'LS_EN','6':None,'9':None,'2':'HOST_SDA','3':'HOST_SCL','4':'HOST_XSHUT','5':'HOST_INTR','13':'SDA_1V8','12':'SCL_1V8','11':'XSHUT_1V8','10':'INTR_1V8'})
res('2.2k',73.66,139.7,'+3V3','HOST_SDA','Host SDA pull-up','RC0402FR-072K2L')
res('2.2k',93.98,139.7,'+3V3','HOST_SCL','Host SCL pull-up','RC0402FR-072K2L')
res('47k',76.2,175.26,'+3V3','LS_EN','Translator enable','ERJ2RKF4702X')
cap('100nF',185.42,139.7,'+3V3','U5 VCCA bypass','GRT155R71H104KE01D')
cap('100nF',213.36,139.7,'+1V8','U5 VCCB bypass','GRT155R71H104KE01D')
res('2.2k',187.96,175.26,'+1V8','SDA_1V8','Optional sensor SDA pull-up; DNP as in ST reference','RC0402FR-072K2L',True)
res('2.2k',215.9,175.26,'+1V8','SCL_1V8','Optional sensor SCL pull-up; DNP as in ST reference','RC0402FR-072K2L',True)
text('U5 includes 10k pull-ups on both sides. R5/R6 are DNP.',162.56,190.5)
text('Use short I2C wiring. Validate rise time at the selected bus speed.',15.24,201.93)
text('J1: 1=3V3, 2=GND, 3=SCL, 4=SDA, 5=XSHUT, 6=INTR',15.24,207.01)
text('Drive XSHUT low during startup; release after supplies and clock are stable.',15.24,212.09)

text('03  SENSOR / SUPPLIED FOOTPRINT',271.78,34.29,1.778)
place('VL53L9_Local:VL53L9CX','U1','VL53L9CX',312.42,57.15,mpn='VL53L9CXV0VE/1',role='Time-of-flight sensor')
mapping={}
for p in sensorpins:
    num=re.search(r'\(number "([^"]+)"',p)[1]; name=re.search(r'\(name "([^"]+)"',p)[1]
    if name.startswith('VSS'): net='GND'
    elif name.startswith('VBAT'): net='+3V3'
    elif name.startswith('AVDD'): net='+2V8'
    elif name=='DVDD': net='+1V2'
    elif name=='IOVDD': net='+1V8'
    elif name in ('SCL','SDA','XSHUT','INTR'): net=name+'_1V8'
    elif name=='AP_CLK': net='AP_CLK_12M'
    elif name=='SYNC_IN': net='SYNC_1V8'
    else: net=None
    mapping[num]=net
connects('U1',mapping)
text('MIPI A5/A6/A8/A9 and reserved E3/E12: no connection.',271.78,118.11)
text('All VSS / VSS_DRIVER / thermal pads connect to GND.',271.78,123.19)
text('04  LOCAL DECOUPLING',271.78,135.89,1.778)
for val,x,rail,role,mpn in [
 ('10uF',279.4,'+3V3','U1 B1 VBAT_LDD','GRJ155R60J106ME11D'),
 ('10uF',304.8,'+3V3','U1 D1 VBAT_RX','GRJ155R60J106ME11D'),
 ('4.7uF',330.2,'+2V8','U1 E6/E7 AVDD','C1005X5R0J475K050BC'),
 ('1uF',355.6,'+1V8','U1 E8 IOVDD','GRM155R6YA105KE11D'),
 ('4.7uF',381.0,'+1V2','U1 C12 DVDD','C1005X5R0J475K050BC')]: cap(val,x,153.67,rail,role,mpn)
text('Place each capacitor at its associated sensor supply pins.',271.78,170.18)

text('05  LOCAL CLOCK / FRAME SYNC',271.78,184.15,1.778)
place('Oscillator:ECS-2520MV-xxx-xx','Y1','12MHz / 50ppm',304.8,212.09,mpn='ECS-2520MVLC-120-CN-TR',role='Always-enabled 1.8 V application clock')
connects('Y1',{'1':'+1V8','2':'GND','3':'OSC_12M','4':'+1V8'})
cap('100nF',276.86,212.09,'+1V8','Y1 bypass','GRT155R71H104KE01D')
res('0R',340.36,212.09,'OSC_12M','AP_CLK_12M','Clock series link','RC0402JR-070RL')
res('47k',381.0,212.09,'+1V8','SYNC_1V8','Hold sync input inactive','ERJ2RKF4702X')
text('Use autonomous or software-triggered ranging.',271.78,233.68)
text('Configure the driver for the fitted 12 MHz clock.',271.78,238.76)

text('DESIGN NOTES',15.24,232.41,1.778)
text('I2C address: 0x29 (7-bit). Select data readout over I2C in firmware.',15.24,239.52)
text('Power: regulated 3.3 V input; allow at least 1 A source capacity and verify peaks.',15.24,244.6)
text('Reference rails retained: VBAT=3.3 V, AVDD=2.8 V, DVDD=1.2 V, IOVDD=1.8 V.',15.24,249.68)
text('No MIPI connector or EEPROM. U5 uses TSSOP-14 instead of reference TQFN.',15.24,254.76)
text('Source: supplied STEVAL-VL53L9 schematic/BOM; DS14879 Rev 8 pinout.',15.24,259.84)

for i,(net,x) in enumerate([('+3V3',30.48),('GND',55.88)],1):
    place('power:PWR_FLAG',f'#FLG0{i:02}', 'PWR_FLAG',x,276.86)
    connect(f'#FLG0{i:02}','1',net)

localdir=ROOT/'libraries'; localdir.mkdir(exist_ok=True)
local_symbols=[s for key,s in symbols.items() if key.startswith('VL53L9_Local:')]
(localdir/'VL53L9_Local.kicad_sym').write_text('(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n'+'\n'.join(local_symbols)+'\n)\n')
pretty=localdir/'VL53L9_Local.pretty'; pretty.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'LIB_VL53L9CX/VL53L9CX/KiCad/VL53L9CX.kicad_mod',pretty/'VL53L9CX.kicad_mod')
# Keep the footprint and 3D source files exactly as supplied.
libentries=[f'(lib (name "VL53L9_Local") (type "KiCad") (uri "${{KIPRJMOD}}/libraries/VL53L9_Local.kicad_sym") (options "") (descr "Project sensor and support ICs"))']
for lib in ['Device','power','Connector_Generic','Oscillator']:
    libentries.append(f'(lib (name "{lib}") (type "KiCad") (uri "${{KICAD10_SYMBOL_DIR}}/{lib}.kicad_sym") (options "") (descr ""))')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (version 7)\n'+'\n'.join(libentries)+'\n)\n')
(ROOT/'fp-lib-table').write_text('(fp_lib_table (version 7)\n(lib (name "VL53L9_Local") (type "KiCad") (uri "${KIPRJMOD}/libraries/VL53L9_Local.pretty") (options "") (descr "User supplied VL53L9CX footprint"))\n)\n')
embedded=[]
for key,s in symbols.items(): embedded.append(re.sub(r'^\(symbol "[^"]+"','(symbol '+q(key),s,count=1))
schematic=f'''(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")
 (uuid {ROOT_UUID}) (paper "A3")
 (title_block (title "VL53L9CX - I2C-only breakout") (date "2026-10-01") (rev "A") (comment 1 "3.3 V host / local regulators and oscillator"))
 (lib_symbols {''.join(embedded)})
 {''.join(items)}
 (sheet_instances (path "/" (page "1"))) (embedded_fonts no))\n'''
backup=ROOT/'backups'; backup.mkdir(exist_ok=True)
if not (backup/'VL53L9.blank.kicad_sch').exists(): shutil.copyfile(ROOT/'VL53L9.kicad_sch',backup/'VL53L9.blank.kicad_sch')
(ROOT/'VL53L9.kicad_sch').write_text(schematic,encoding='utf-8')
(ROOT/'output').mkdir(exist_ok=True)
(ROOT/'output/components.json').write_text(json.dumps(parts,indent=2))
rows=['# Schematic bill of materials','', '32 components total; R5 and R6 are not fitted (30 fitted components).', '', '| Reference | Value | Manufacturer part number | Function | Fitted |', '|---|---|---|---|---|']
for p in parts:
    rows.append('| '+ ' | '.join([p['reference'],p['value'],p['mpn'] or 'Generic 1x6, 2.54 mm header',p['function'],'No (DNP)' if p['dnp'] else 'Yes'])+' |')
(ROOT/'output/BOM.md').write_text('\n'.join(rows)+'\n')
print(f'Created schematic: {len(parts)} components; {len(sensorpins)} sensor pins; {len(items)} drawing items')
