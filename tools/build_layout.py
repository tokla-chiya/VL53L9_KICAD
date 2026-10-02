"""Create the 34 x 30 mm four-layer breakout placement and critical routing.
Run using KiCad's bundled Python from the project directory.
"""
from pathlib import Path
import pcbnew as p
import xml.etree.ElementTree as ET
import json, shutil, uuid, re

ROOT=Path(__file__).resolve().parents[1]
FPBASE=Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')
M=p.FromMM
def xy(x,y): return p.VECTOR2I(M(x),M(y))
def mm(v): return p.ToMM(v)
ROOTID='7f5e5dbe-2432-41a3-a9e4-3e719c5bb90d'
def uid(ref): return str(uuid.uuid5(uuid.UUID(ROOTID),ref))

backup=ROOT/'backups/VL53L9.blank.kicad_pcb'
if not backup.exists(): shutil.copyfile(ROOT/'VL53L9.kicad_pcb',backup)
propath=ROOT/'VL53L9.kicad_pro'
if not (ROOT/'backups/VL53L9.pre-layout.kicad_pro').exists(): shutil.copyfile(propath,ROOT/'backups/VL53L9.pre-layout.kicad_pro')
pro=json.loads(propath.read_text())
default=dict(pro['net_settings']['classes'][0])
default.update(clearance=0.15,track_width=0.2,via_diameter=0.5,via_drill=0.25)
power=dict(default,name='Power',track_width=0.4,priority=0)
pro['net_settings']['classes']=[default,power]
pro['net_settings']['netclass_patterns']=[{'netclass':'Power','pattern':'/+*'}]
boardsettings=pro.setdefault('board',{}).setdefault('design_settings',{})
boardsettings['rules']={'min_clearance':0.15,'min_track_width':0.15,'min_via_diameter':0.45,'min_through_hole_diameter':0.2,'min_via_annular_width':0.1,'min_hole_to_hole':0.25,'min_copper_edge_clearance':0.3,'min_silk_clearance':0.1,'min_text_height':0.7,'min_text_thickness':0.12}
boardsettings['defaults']={'board_outline_line_width':0.05,'copper_line_width':0.2,'copper_text_size_h':1.0,'copper_text_size_v':1.0,'copper_text_thickness':0.15,'courtyard_line_width':0.05,'fab_line_width':0.1,'fab_text_size_h':1.0,'fab_text_size_v':1.0,'fab_text_thickness':0.15,'silk_line_width':0.12,'silk_text_size_h':0.7,'silk_text_size_v':0.7,'silk_text_thickness':0.12}
propath.write_text(json.dumps(pro,indent=2)+'\n')
b=p.BOARD(); b.SetCopperLayerCount(4)
ds=b.GetDesignSettings(); ds.SetBoardThickness(M(1.6))
ds.m_MinClearance=M(.15); ds.m_TrackMinWidth=M(.15); ds.m_ViasMinSize=M(.45)
ds.m_MinThroughDrill=M(.2); ds.m_ViasMinAnnularWidth=M(.1)
ds.m_CopperEdgeClearance=M(.3); ds.m_HoleToHoleMin=M(.25)
ds.m_SolderMaskExpansion=M(.04) if hasattr(ds,'m_SolderMaskExpansion') else 0
ds.m_SolderMaskMinWidth=M(.06)
title=p.TITLE_BLOCK(); title.SetTitle('VL53L9CX I2C breakout'); title.SetRevision('A'); title.SetDate('2026-10-01'); b.SetTitleBlock(title)

doc=ET.parse(ROOT/'output/VL53L9.net.xml').getroot()
nets={}; pin_net={}
for n in doc.findall('nets/net'):
    net=p.NETINFO_ITEM(b,n.attrib['name']); b.Add(net); nets[n.attrib['name']]=net
    for node in n.findall('node'): pin_net[(node.attrib['ref'],node.attrib['pin'])]=net
components={c.attrib['ref']:c for c in doc.findall('components/comp')}
parts={}
# Coordinates are board coordinates, top view. All components on front.
placement={
 'U1':(117,107,0), 'J1':(102.3,114,0),
 'U2':(129.4,114,0), 'U3':(127.2,122.0,0), 'U4':(117.0,124,0),
 'U5':(110.5,117.1,0), 'Y1':(106.8,103.4,0),
 'C1':(131.8,111.1,90), 'C2':(128.9,117.0,0), 'C3':(132,116.1,90),
 'C4':(129.8,120.3,90), 'C5':(126.7,125.0,0), 'C6':(130,124.1,90),
 'C7':(119.6,122.3,90), 'C8':(116.5,127.0,0), 'C9':(119.8,126.1,90),
 'C10':(105.3,113.7,180), 'C11':(115.5,117.1,0),
 'C12':(125.65,108.125,0), 'C13':(125.65,105.875,0),
 'C14':(117.0,101.9,90), 'C15':(115.1,101.9,90), 'C16':(108.3,107,180),
 'C17':(106.8,101.1,0),
 'R1':(130.5,127.5,0), 'R2':(104.9,118,90), 'R3':(104.9,116,90),
 'R4':(107,122.0,90), 'R5':(115.8,111.8,0), 'R6':(113.2,111.8,0),
 'R7':(110.2,102.2,0), 'R8':(108.5,109.3,90),
}
modeldir=ROOT/'libraries/3d'; modeldir.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'LIB_VL53L9CX/VL53L9CX/3D/VL53L9CX.stp',modeldir/'VL53L9CX.stp')
for ref,(x,y,angle) in placement.items():
    c=components[ref]; lib,name=c.findtext('footprint').split(':')
    libpath=ROOT/'libraries/VL53L9_Local.pretty' if lib=='VL53L9_Local' else FPBASE/(lib+'.pretty')
    fp=p.FootprintLoad(str(libpath),name)
    assert fp is not None,ref
    fp.SetReference(ref); fp.SetValue(c.findtext('value'))
    fp.SetFPID(p.LIB_ID(lib,name)); fp.SetPath(p.KIID_PATH('/'+ROOTID+'/'+uid(ref)))
    fp.SetSheetname(''); fp.SetSheetfile('VL53L9.kicad_sch')
    fp.SetField('Datasheet',c.findtext('datasheet',''))
    for field in c.findall('fields/field'):
        if field.attrib['name'] not in ('Reference','Value','Footprint','Datasheet'):
            fp.SetField(field.attrib['name'],field.text or '')
    fp.SetDNP(ref in ('R5','R6'))
    b.Add(fp); fp.SetPosition(xy(x,y)); fp.SetOrientationDegrees(angle)
    fp.SetLocked(True)
    for pad in fp.Pads():
        if (ref,pad.GetNumber()) in pin_net: pad.SetNet(pin_net[(ref,pad.GetNumber())])
    fp.Value().SetVisible(False)
    for field in fp.GetFields():
        if field.GetName()!='Reference': field.SetVisible(False)
    fp.Reference().SetTextSize(xy(.7,.7)); fp.Reference().SetTextThickness(M(.12)); fp.Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
    fp.Reference().SetPosition(xy(x,y-1.6))
    if ref.startswith(('R','C','Y')):
        fp.Reference().SetLayer(p.F_Fab)
        fp.Reference().SetPosition(xy(x,y))
    if ref in ('U2','U3','U4','U5'):
        fp.Reference().SetPosition(xy(x,{'U2':111.2,'U3':119.1,'U4':121.1,'U5':113.5}[ref]))
    if ref=='U1':
        fp.Reference().SetPosition(xy(123.5,102.1))
        for model in fp.Models(): model.m_Filename='${KIPRJMOD}/libraries/3d/VL53L9CX.stp'
    if ref=='J1': fp.Reference().SetPosition(xy(102.3,111.7))
    parts[ref]=fp

# Closed rectangular board outline, with ample room for sensor optical face.
for a,c in [((100,100),(134,100)),((134,100),(134,130)),((134,130),(100,130)),((100,130),(100,100))]:
    s=p.PCB_SHAPE(); s.SetShape(p.SHAPE_T_SEGMENT); s.SetStart(xy(*a)); s.SetEnd(xy(*c)); s.SetLayer(p.Edge_Cuts); s.SetWidth(M(.05)); b.Add(s)

def pad(ref,num): return next(pa for pa in parts[ref].Pads() if pa.GetNumber()==str(num))
def pt(pa): return (mm(pa.GetPosition().x),mm(pa.GetPosition().y))
def track(points,net,layer=p.F_Cu,width=.25,locked=True):
    net=nets[net] if isinstance(net,str) else net
    for a,c in zip(points,points[1:]):
        if a==c: continue
        tr=p.PCB_TRACK(b); tr.SetStart(xy(*a)); tr.SetEnd(xy(*c)); tr.SetLayer(layer); tr.SetWidth(M(width)); tr.SetNet(net); tr.SetLocked(locked); b.Add(tr)
def via(pos,net,size=.5,drill=.25):
    net=nets[net] if isinstance(net,str) else net
    v=p.PCB_VIA(b); v.SetPosition(xy(*pos)); v.SetWidth(M(size)); v.SetDrill(M(drill)); v.SetViaType(p.VIATYPE_THROUGH); v.SetLayerPair(p.F_Cu,p.B_Cu); v.SetNet(net); v.SetLocked(True); b.Add(v); return v
def padvia(ref,num,pos,width=.3,size=.5,drill=.25):
    pa=pad(ref,num); track([pt(pa),pos],pa.GetNet(),width=width); via(pos,pa.GetNet(),size,drill)
def link(ref1,p1,ref2,p2,bends=(),width=.3):
    pa=pad(ref1,p1); pb=pad(ref2,p2); assert pa.GetNetCode()==pb.GetNetCode()
    track([pt(pa),*bends,pt(pb)],pa.GetNet(),width=width)

# Direct local decoupling, prior to general routing.
link('U1','B1','C12','1',width=.5)
link('U1','D1','C13','1',width=.5)
link('U1','C12','C16','1',width=.4)
link('U1','E6','U1','E7',width=.4)
link('U1','E7','C14','1',[(116.525,103.65),(117,103.175)],width=.4)
link('U1','E8','C15','1',[(115.575,103.5),(115.1,103.025)],width=.3)
link('Y1','3','R7','1',[(108.7,104.15),(109.72,103.13)],width=.2)
link('R7','2','U1','E11',[(111.4,102.2),(112.725,103.525)],width=.2)

# Thermal vias are outside paste pads (no untented via-in-pad construction).
for row,y in [('B',108.54),('D',105.46)]:
    for col in range(4,10):
        pa=pad('U1',f'{row}{col}'); padvia('U1',f'{row}{col}',(pt(pa)[0],y),width=.35)
for num in ['A1','A2','A3','A4','A7']:
    pa=pad('U1',num); padvia('U1',num,(pt(pa)[0],110.4),width=.35)
for num in ['E1','E2','E4','E5','E9','E10']:
    pa=pad('U1',num); padvia('U1',num,(pt(pa)[0],103.55),width=.3)
padvia('U1','C1',(124.0,107),width=.35)

# Ground drops beside all other SMD ground pads; horizontal/vertical away from body.
for ref,fp in parts.items():
    if ref in ('U1','J1'): continue
    for pa in fp.Pads():
        if pa.GetNetname()!='/GND': continue
        x,y=pt(pa); cx,cy=pt(fp)
        if ref.startswith('C'):
            dx,dy=x-cx,y-cy; d=(dx*dx+dy*dy)**.5
            dest=(x+.6*dx/d,y+.6*dy/d)
        elif ref=='Y1': dest=(x+.3,y+.65)
        elif ref=='U5': dest=(x-.75,y+.4)
        else: dest=(x-.8,y)
        padvia(ref,pa.GetNumber(),dest,width=.25)

# Plane feeds at sensor boost capacitors, header and regulator input capacitors.
for ref in ['C1','C4','C7','C10','C12','C13']:
    pa=pad(ref,'1'); x,y=pt(pa); cx,cy=pt(parts[ref]); dx,dy=x-cx,y-cy; d=(dx*dx+dy*dy)**.5
    # Boost rail vias branch orthogonally, keeping the direct sensor-to-capacitor path short.
    dest=(x,y+.72 if ref=='C12' else y-.72) if ref in ('C12','C13') else (x+.7*dx/d,y+.7*dy/d)
    padvia(ref,'1',dest,width=.4,size=.6,drill=.3)

def zone(layer,net,thermal=False):
    z=p.ZONE(b); z.SetLayer(layer); z.SetNet(nets[net]); z.SetLocalClearance(M(.15)); z.SetMinThickness(M(.15))
    z.SetPadConnection(p.ZONE_CONNECTION_THERMAL if thermal else p.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(M(.2)); z.SetThermalReliefSpokeWidth(M(.3))
    outline=z.Outline(); outline.NewOutline()
    for x,y in [(100.3,100.3),(133.7,100.3),(133.7,129.7),(100.3,129.7)]: outline.Append(M(x),M(y))
    b.Add(z)
zone(p.In1_Cu,'/GND'); zone(p.In2_Cu,'/+3V3')

def label(txt,x,y,size=.8,layer=p.F_SilkS):
    t=p.PCB_TEXT(b); t.SetText(txt); t.SetPosition(xy(x,y)); t.SetTextSize(xy(size,size)); t.SetTextThickness(M(.12)); t.SetLayer(layer)
    if layer==p.B_SilkS: t.SetMirrored(True)
    b.Add(t)
label('VL53L9 I2C',117,128.9,1.0)
label('REV A / 3V3',128,101.3,.7)
for i,name in enumerate(['3V3','GND','SCL','SDA','XSH','INT']): label(name,104.8,114+2.54*i,.7,p.B_SilkS)
label('VL53L9CX  I2C',117,111,1.1,p.B_SilkS)
label('3.3V INPUT / HOST',117,114,1.0,p.B_SilkS)
label('4 LAYERS / REV A',117,117,1.0,p.B_SilkS)

b.BuildListOfNets(); b.SynchronizeNetsAndNetClasses(False)
p.SaveBoard(str(ROOT/'VL53L9.kicad_pcb'),b)
# SaveBoard on a newly created BOARD writes default project settings; restore our rules.
propath.write_text(json.dumps(pro,indent=2)+'\n')
(ROOT/'output/pcb').mkdir(exist_ok=True)
print(f'Placed {len(parts)} schematic footprints on 34 x 30 mm, 4 layers. Critical tracks: {len(list(b.GetTracks()))}.')
