"""Complete local power routes, fills and model paths after importing the SES file."""
from pathlib import Path
import pcbnew as p
import json, shutil
ROOT=Path(__file__).resolve().parents[1]
M=p.FromMM
def xy(x,y): return p.VECTOR2I(M(x),M(y))
def point(o): return (p.ToMM(o.GetPosition().x),p.ToMM(o.GetPosition().y))
# Load the routed snapshot through the real project path so its project rules apply.
propath=ROOT/'VL53L9.kicad_pro'; pro=json.loads(propath.read_text())
default=dict(pro['net_settings']['classes'][0]); default.update(name='Default',clearance=.15,track_width=.2,via_diameter=.5,via_drill=.25)
pro['net_settings']['classes']=[default,dict(default,name='Power',track_width=.4,priority=0)]
pro['net_settings']['netclass_patterns']=[{'netclass':'Power','pattern':'/+*'}]
pro['board']['design_settings']['rules'].update(min_clearance=.15,min_track_width=.15,min_via_diameter=.45,min_through_hole_diameter=.2,min_via_annular_width=.1,min_hole_to_hole=.25,min_copper_edge_clearance=.3,min_silk_clearance=.1,min_text_height=.7,min_text_thickness=.12)
propath.write_text(json.dumps(pro,indent=2)+'\n')
shutil.copyfile(ROOT/'tmp/routing/autorouted.kicad_pcb',ROOT/'VL53L9.kicad_pcb')
b=p.LoadBoard(str(ROOT/'VL53L9.kicad_pcb'))
parts={f.GetReference():f for f in b.GetFootprints()}
def pad(ref,num): return next(a for a in parts[ref].Pads() if a.GetNumber()==str(num))
def track(points,net,width=.3,layer=p.F_Cu):
    for a,c in zip(points,points[1:]):
        t=p.PCB_TRACK(b); t.SetStart(xy(*a)); t.SetEnd(xy(*c)); t.SetLayer(layer); t.SetWidth(M(width)); t.SetNet(b.FindNet(net)); b.Add(t)
def via(pos,net,width=.5,drill=.25):
    v=p.PCB_VIA(b); v.SetPosition(xy(*pos)); v.SetWidth(M(width)); v.SetDrill(M(drill)); v.SetViaType(p.VIATYPE_THROUGH); v.SetLayerPair(p.F_Cu,p.B_Cu); v.SetNet(b.FindNet(net)); b.Add(v)
def drop(ref,num,pos,width=.4):
    a=pad(ref,num); net=a.GetNetname(); track([point(a),pos],net,width); via(pos,net,.6,.3)
for ref in ['U2','U3','U4']:
    x,y=point(pad(ref,'1')); drop(ref,'1',(x-.9,y))
drop('R1','1',(129.0,127.5))
drop('R2','1',(105.9,119.6))
track([point(pad('R3','1')),(105.95,115.46),(105.95,115.4)],'/+3V3',.4)
via((105.95,115.4),'/+3V3',.6,.3)

# Join the three disconnected 1.8 V branches on the back, preserving inner planes.
main=(114.5773,115.2494); resistors=(113.7,112.5234); sensor=(115.575,103.5); osc=(108.2,102.475)
for loc in [main,resistors,sensor,osc]: via(loc,'/+1V8')
track([point(pad('Y1','4')),osc],'/+1V8')
track([main,(114.5773,113.4007),resistors],'/+1V8',layer=p.B_Cu)
track([resistors,(113.7,110.9),(114.6,110.0),(114.6,104.475),sensor],'/+1V8',layer=p.B_Cu)
track([sensor,(114.4,102.325),(108.35,102.325),osc],'/+1V8',layer=p.B_Cu)

# The twelve thermal vias sit beside the paste apertures, with 0.20 mm drills.
thermal_x=[113.98,115.188,116.396,117.604,118.812,120.02]
for t in b.GetTracks():
    if isinstance(t,p.PCB_VIA) and t.GetNetname()=='/GND':
        x,y=point(t)
        if any(abs(x-v)<.001 for v in thermal_x) and any(abs(y-v)<.001 for v in [105.46,108.54]):
            t.SetWidth(M(.45)); t.SetDrill(M(.2))

# A ground fence improves plane stitching and spreads heat into copper.
for x in [101,111,121,132.8]:
    for y in [101,129]:
        # Top-left and top-right regions are clear; avoid the clock/decoupling cluster.
        if y==101 and x==111: continue
        via((x,129.4 if (x==121 and y==129) else y),'/GND')
for y in [106,111,116,121,126]:
    for x in [100.8,133.2]:
        if x==133.2 and y==116: continue
        via((x,y),'/GND')
for x,y in [(122,112.5),(122,119.5),(122,126),(109,126),(130,103.5)]: via((x,y),'/GND')

for z in b.Zones(): z.SetPadConnection(p.ZONE_CONNECTION_THT_THERMAL)
for layer in [p.F_Cu,p.B_Cu]:
    z=p.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet('/GND')); z.SetLocalClearance(M(.15)); z.SetMinThickness(M(.15))
    z.SetPadConnection(p.ZONE_CONNECTION_THT_THERMAL); z.SetThermalReliefGap(M(.2)); z.SetThermalReliefSpokeWidth(M(.3)); z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
    outline=z.Outline(); outline.NewOutline()
    for x,y in [(100.3,100.3),(133.7,100.3),(133.7,129.7),(100.3,129.7)]: outline.Append(M(x),M(y))
    b.Add(z)

for ref,path in [('U1','${KIPRJMOD}/libraries/3d/VL53L9CX.stp'),('Y1','${KICAD10_3DMODEL_DIR}/Oscillator.3dshapes/Oscillator_SMD_SeikoEpson_SG210-4Pin_2.5x2.0mm.step')]:
    models=parts[ref].Models(); model=models[0]; model.m_Filename=path; models[0]=model

# Turn off provisional routing locks, retaining footprint placement locks.
for t in b.GetTracks(): t.SetLocked(False)
p.SaveBoard(str(ROOT/'VL53L9.kicad_pcb'),b)
propath.write_text(json.dumps(pro,indent=2)+'\n')

# Explicit nominal four-layer stack, subject to the fabricator's available laminates.
boardfile=ROOT/'VL53L9.kicad_pcb'; txt=boardfile.read_text()
stack='''
        (stackup
            (layer "F.SilkS" (type "Top Silk Screen"))
            (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
            (layer "F.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 1" (type "prepreg") (thickness 0.18) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
            (layer "In1.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 2" (type "core") (thickness 1.10) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
            (layer "In2.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 3" (type "prepreg") (thickness 0.18) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
            (layer "B.Cu" (type "copper") (thickness 0.035))
            (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
            (layer "B.SilkS" (type "Bottom Silk Screen"))
            (copper_finish "ENIG")
            (dielectric_constraints no)
        )'''
txt=txt.replace('(setup','(setup'+stack,1)
boardfile.write_text(txt)
print('Completed power links, ground fills, stitching, stackup and 3D model paths.')
