# VL53L9CX I2C-only breakout

Open `VL53L9.kicad_pro` in KiCad, then open `VL53L9.kicad_sch`.
The schematic is complete; the PCB is still empty and needs placement/routing.

## Interface

Supply regulated 3.3 V through J1. The design assumes a 3.3 V host and uses
U5 to translate SDA, SCL, XSHUT, and INTR to the sensor's 1.8 V domain.
Provide at least 1 A source capacity as a starting design allowance, then
verify rail droop and transient current with the intended ranging profile.

| J1 pin | Signal | Use |
|---|---|---|
| 1 | 3V3 | Power input |
| 2 | GND | Common ground |
| 3 | HOST_SCL | Host I2C clock |
| 4 | HOST_SDA | Host I2C data |
| 5 | HOST_XSHUT | Active-low shutdown/reset control |
| 6 | HOST_INTR | Interrupt to host |

Keep XSHUT low while power starts, then release it after supplies and the
onboard clock stabilize. Configure firmware for a 12 MHz application clock,
2.8 V AVDD, 1.8 V IOVDD, and I2C data readout. The default 7-bit address is
0x29. I2C readout limits frame rate; select resolution and rate accordingly.
SYNC_IN is pulled high for autonomous or software-triggered operation.

## Implementation

- U1 uses the supplied 42-pad sensor footprint, copied unchanged to the local library.
- U2/U3/U4 provide 2.8 V, 1.8 V, and 1.2 V using the reference LDK130 regulators.
- Y1 is the reference ECS-2520MVLC-120-CN-TR oscillator, powered at 1.8 V.
- U5 is PI4ULS3V204LEX (TSSOP-14). This deliberately substitutes the larger
  package for the reference board's TQFN version; order the LEX variant.
- R2/R3 are fitted host pull-ups. R5/R6 are optional sensor-side pull-ups,
  **DNP**, matching the reference population. U5 has internal pull-ups.
- MIPI and reserved pins have explicit no-connect markers. No MIPI connector,
  EEPROM, external clock input, or host voltage-select jumper is included.
- The sensor symbol's pin positions/numbers come from the supplied library;
  electrical types were added so ERC can check inputs and supply connections.

The older reference schematic labels some thermal pads C4-C9 and E3/E5/E12
as VHV/VPP/ATEST0. The supplied library and current datasheet use D4-D9
for those thermal pads, E5 as ground, and E3/E12 as reserved no-connect pins.
This design follows the current pinout.

Place sensor decoupling capacitors immediately beside the associated supply
pads (see each capacitor's Function field). Connect all ground and thermal
pads to a ground plane with thermal vias. Verify package land dimensions,
orientation, thermal performance, and effective capacitor values during PCB
layout. The supplied footprint was checked for matching pad numbers; its
manufacturing geometry has not been independently qualified.

## Review files

- `output/VL53L9-I2C-schematic.pdf`: plotted schematic.
- `output/BOM.md`: 32 components, including two DNP resistors.
- `output/VL53L9.net.xml`: KiCad-exported netlist.
- `output/ERC.json`: zero reported errors or warnings in KiCad 10.0.6.
- `output/verification.json`: independent connectivity and pad checks.
- `backups/VL53L9.blank.kicad_sch`: original empty schematic.

`tools/build_schematic.py` generated the starting schematic. It overwrites
the schematic and local libraries, so do not rerun it after manual edits
unless those edits have been incorporated into the script. Re-export the
netlist/ERC before running `tools/verify_netlist.py` on subsequent changes.

## References

- Supplied `steval-vl53l9-schematic.pdf`, Rev 1, March 2026.
- Supplied `steval-vl53l9-bom.pdf`, Rev 2, May 2026.
- [ST VL53L9CX datasheet, DS14879 Rev 8](https://www.st.com/resource/en/datasheet/vl53l9cx.pdf), pinout and I2C application circuit.
- [Diodes PI4ULS3V204 datasheet](https://www.diodes.com/datasheet/download/PI4ULS3V204.pdf), translator pinout and package.
- [ECS-2520MVLC](https://ecsxtal.com/products/oscillators/surface-mount-oscillators/ecs-2520mvlc/), oscillator family.

These are schematic-level checks, not a hardware validation or a completed PCB design.
