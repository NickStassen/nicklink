"""NickLink design spec: the single source of truth for parts and nets.

gen_sch.py builds the schematic from this; the PCB is built from the netlist
KiCad exports from that schematic.
"""

REV = "1.3"

# ref: (lib_symbol, value, footprint, {pin: net}, extra fields)
# Pins not listed are no-connect.
PARTS = {
    # --- MCU ---------------------------------------------------------------
    "U1": ("MCU_ST_STM32F1:STM32F103C8Tx", "STM32F103C8T6", "Package_QFP:LQFP-48_7x7mm_P0.5mm", {
        "1": "+3.3V",  # VBAT, no backup battery
        "2": "PC13", "3": "PC14", "4": "PC15",
        "5": "HSE_IN", "6": "HSE_OUT", "7": "NRST",
        "8": "GND", "9": "+3.3VA",
        "10": "PA0", "11": "PA1", "12": "PA2", "13": "PA3", "14": "PA4",
        "15": "PA5", "16": "PA6", "17": "PA7", "18": "PB0", "19": "PB1",
        "20": "PB2", "21": "PB10", "22": "PB11", "23": "GND", "24": "+3.3V",
        "25": "PB12", "26": "PB13", "27": "PB14", "28": "PB15",
        "29": "PA8", "30": "PA9", "31": "PA10", "32": "USB_D-", "33": "USB_D+",
        "34": "PA13", "35": "GND", "36": "+3.3V",
        "37": "PA14", "38": "PA15", "39": "PB3", "40": "PB4", "41": "PB5",
        "42": "PB6", "43": "PB7", "44": "BOOT0", "45": "PB8", "46": "PB9",
        "47": "GND", "48": "+3.3V",
    }, {}),
    "C1": ("Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3V", "2": "GND"}, {"Note": "VDD pin 1/VBAT decoupling"}),
    "C2": ("Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3V", "2": "GND"}, {"Note": "VDD pin 24 decoupling"}),
    "C3": ("Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3V", "2": "GND"}, {"Note": "VDD pin 36 decoupling"}),
    "C4": ("Device:C", "4u7", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3V", "2": "GND"}, {"Note": "VDD3 (pin 48) bulk: DS5319 Fig. 14 requires 4.7 uF on VDD3"}),
    "FB1": ("Device:FerriteBead", "120R@100MHz", "Inductor_SMD:L_0402_1005Metric", {"1": "+3.3VA", "2": "+3.3V"}, {}),
    "C6": ("Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3VA", "2": "GND"}, {"Note": "VDDA"}),
    "C7": ("Device:C", "1u", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3VA", "2": "GND"}, {"Note": "VDDA"}),

    # --- Clock: 8 MHz HSE ---------------------------------------------------
    "Y1": ("Device:Crystal_GND24", "8MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", {"1": "HSE_IN", "2": "GND", "3": "HSE_OUT", "4": "GND"}, {"MPN": "YXC X32258MOB4SI (CL 12 pF)"}),
    "C10": ("Device:C", "15p", "Capacitor_SMD:C_0402_1005Metric", {"1": "HSE_IN", "2": "GND"}, {"Note": "C0G; crystal CL 12 pF"}),
    "C11": ("Device:C", "15p", "Capacitor_SMD:C_0402_1005Metric", {"1": "HSE_OUT", "2": "GND"}, {"Note": "C0G; crystal CL 12 pF"}),

    # --- Reset / boot -------------------------------------------------------
    "SW1": ("Switch:SW_Push", "RESET", "nicklink:SW_SPST_B3U-1000P_NoSilk", {"1": "NRST", "2": "GND"}, {}),
    "C9": ("Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", {"1": "NRST", "2": "GND"}, {}),
    "SW2": ("Switch:SW_Push", "BOOT0", "nicklink:SW_SPST_B3U-1000P_NoSilk", {"1": "+3.3V", "2": "BOOT0"}, {"Note": "Hold while resetting to enter the USART1 system bootloader"}),
    "R1": ("Device:R", "10k", "Resistor_SMD:R_0402_1005Metric", {"1": "BOOT0", "2": "GND"}, {"Note": "BOOT0 pull-down"}),
    "R8": ("Device:R", "10k", "nicklink:R_0402_1005Metric_NoSilk", {"1": "PB2", "2": "GND"}, {"Note": "BOOT1 pull-down"}),

    # --- USB ----------------------------------------------------------------
    "J2": ("Connector:USB_C_Receptacle_USB2.0_16P", "USB_C_Receptacle_USB2.0_16P", "nicklink:USB_C_Receptacle_GCT_USB4085_EdgeSilk", {
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
        "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
        "A5": "USB_CC1", "B5": "USB_CC2",
        "A6": "USB_D+", "B6": "USB_D+", "A7": "USB_D-", "B7": "USB_D-",
    }, {"MPN": "GCT USB4085-GF-A"}),
    "R4": ("Device:R", "5k1", "Resistor_SMD:R_0402_1005Metric", {"1": "GND", "2": "USB_CC1"}, {}),
    "R5": ("Device:R", "5k1", "nicklink:R_0402_1005Metric_NoSilk", {"1": "GND", "2": "USB_CC2"}, {}),
    # D+ pull-up from VBUS, not 3V3: R2/R11 = 1.50 kOhm Thevenin to 3.41 V at VBUS 5.0 V (3.24-3.58 V over 4.75-5.25 V).
    # Nothing pulls D+ up (or back-feeds VBUS through U3) unless VBUS is present; R2+R11 also bleed VBUS to vSafe0V.
    "R2": ("Device:R", "2k2", "Resistor_SMD:R_0402_1005Metric", {"1": "VBUS", "2": "USB_D+"}, {"Note": "USB FS D+ pull-up (with R11: 1.5k to 3.4 V, VBUS-derived)"}),
    "R11": ("Device:R", "4k7", "nicklink:R_0402_1005Metric_NoSilk", {"1": "GND", "2": "USB_D+"}, {"Note": "D+ pull-up divider; VBUS bleed"}),
    # USBLC6-2P6: 1/6 = I/O1, 3/4 = I/O2 (each pair internally connected), 2 = GND, 5 = VBUS
    "U3": ("Power_Protection:USBLC6-2P6", "USBLC6-2P6", "Package_TO_SOT_SMD:SOT-666", {
        # channels are identical; D+ on I/O2 so neither line crosses the other at the MCU (D+ is left of D-)
        "1": "USB_D-", "6": "USB_D-", "3": "USB_D+", "4": "USB_D+", "2": "GND", "5": "VBUS",
    }, {}),
    "C13": ("Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", {"1": "VBUS", "2": "GND"}, {"Note": "USBLC6 VBUS decoupling"}),

    # --- Power --------------------------------------------------------------
    # VBUS -> R12 -> D2 -> VSYS (LDO input).  VSYS -> F1 (PTC) -> 5V_F -> Q1 (P-FET, gate to GND) -> +5V = J1.1.
    # Q1 conducts both ways whenever VSYS or J1.1 is positive (5V out on USB, 5V in from J1.1) and blocks a
    # reversed supply on J1.1; F1 trips on a J1.1 short or on a reversed J1.1 supply while USB is connected.
    # R12 damps the USB cable inductance against the ceramic input caps on hot-plug (sim bench 11:
    # without it the input rings to about 6.1-11.4 V; with 1.0 ohm and C12 4.7 uF the USB peak is 5.38 V).
    # The fitted regulator is the TLV76733 (VIN/EN abs max 18 V). The 6.0 V figure was the TLV755 it replaced.
    "R12": ("Device:R", "1R", "Resistor_SMD:R_0805_2012Metric", {"1": "VBUS", "2": "VBUS_D"}, {"Note": "Hot-plug damping (anti-surge, 500 mW)", "MPN": "YAGEO SR0805FR-471RL"}),
    "D2": ("Device:D_Schottky", "1N5819WS", "Diode_SMD:D_SOD-323", {"1": "VSYS", "2": "VBUS_D"}, {"Note": "Blocks back-feed from VSYS / the 5V pin into USB"}),  # 1=K, 2=A
    "C12": ("Device:C", "4u7 16V", "Capacitor_SMD:C_0402_1005Metric", {"1": "VSYS", "2": "GND"}, {"Note": "LDO input, 16 V X5R (J1.1 hot-plug ring); USB allows <= 10 uF", "MPN": "Samsung CL05A475MO5NUNC"}),
    "F1": ("Device:Polyfuse", "0.5A", "Fuse:Fuse_0805_2012Metric", {"1": "VSYS", "2": "5V_F"}, {"Note": "5V pin short / reverse-supply limit: Ihold 0.5 A, Itrip 1 A, 16 V", "MPN": "LUTE 0805L050/16XR"}),
    # SOT-323 G-S-D = 1-2-3, same as the library's DMG2301L symbol (SOT-23); footprint overridden.
    "Q1": ("Transistor_FET:DMG2301L", "DMP2165UW", "nicklink:SOT-323_SC-70_NoSilk", {"1": "GND", "2": "5V_F", "3": "+5V"}, {"Note": "5V pin reverse-polarity switch (gate to GND)", "MPN": "Diodes DMP2165UW-7"}),
    # TLV76733DRVR (WSON-6 2x2, DRV0006A like the TLV755): 1 OUT, 2 SNS (tie to OUT), 3 GND, 4 EN, 5 GND,
    # 6 IN, 7 exposed pad (GND). VIN/EN rated 18 V abs max: survives J1.1 hot-plug ringing (sim bench 12).
    "U2": ("nicklink:TLV76733DRV", "TLV76733DRVR", "nicklink:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm_ThermalVias03", {
        "1": "+3.3V", "2": "+3.3V", "3": "GND", "4": "VSYS", "5": "GND", "6": "VSYS", "7": "GND",
    }, {"MPN": "TI TLV76733DRVR"}),
    "C8": ("Device:C", "1u", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3V", "2": "GND"}, {"Note": "LDO output"}),

    # --- LEDs ---------------------------------------------------------------
    "D1": ("Device:LED", "RED", "LED_SMD:LED_0402_1005Metric", {"1": "PWR_LED_K", "2": "+3.3V"}, {"Note": "Power", "MPN": "Everlight 16-213/R6C-AQ2R2B/3T"}),  # 1=K, 2=A
    "R3": ("Device:R", "1k5", "Resistor_SMD:R_0402_1005Metric", {"1": "GND", "2": "PWR_LED_K"}, {}),
    "D3": ("Device:LED", "GREEN", "LED_SMD:LED_0402_1005Metric", {"1": "USER_LED_K", "2": "+3.3V"}, {"Note": "User LED, PC13 low = on", "MPN": "Everlight 16-213/GHC-YR1S1/3T"}),
    "R6": ("Device:R", "330", "Resistor_SMD:R_0402_1005Metric", {"1": "PC13", "2": "USER_LED_K"}, {"Note": "~1.2-1.8 mA (PC13 sinks <= 3 mA)"}),

    # --- IMU: LSM6DSV on I2C1 (address 0x6A), INT1 -> PA0 (WKUP) ----------------
    # Project symbol (nicklink.kicad_sym): KiCad has none; same LGA-14 pinout as LSM6DSM.
    # LSM6DSV (DS13476), not the LSM6DSV16X it replaced: JLC lists the LSM6DSV16X (C5267406) as
    # "Standard PCBA only". Same pinout, register map, WHO_AM_I 0x70 and SFLP sensor fusion; it lacks
    # the LSM6DSV16X's MLC, Qvar and analog hub, none of which this board uses (SDx/SCx are tied to GND).
    "U4": ("nicklink:LSM6DSV", "LSM6DSV", "nicklink:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y_NoSilk", {
        "1": "GND",          # SDO/SA0 low -> I2C address 0x6A
        "2": "GND", "3": "GND",  # SDx/SCx aux bus unused
        "4": "IMU_INT1",     # INT1 -> R10 -> PA0 (INT1 drives low by default)
        "5": "+3.3V", "8": "+3.3V",  # VDDIO, VDD
        "6": "GND", "7": "GND",
        "10": "+3.3V", "11": "+3.3V",  # OCS_Aux/SDO_Aux: "connect to Vdd_IO or leave unconnected" (DS13476 Table 2)
        "12": "+3.3V",       # CS high -> I2C mode
        "13": "PB6", "14": "PB7",
    }, {"MPN": "ST LSM6DSV (JLC: LSM6DSVETR)"}),
    "C14": ("Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3V", "2": "GND"}, {"Note": "IMU VDD/VDDIO"}),
    "C15": ("Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", {"1": "+3.3V", "2": "GND"}, {"Note": "IMU VDD/VDDIO"}),
    # INT1 is "output forced to ground" from power-up until firmware configures the IMU;
    # 10k keeps that from fighting whatever a user connects to A0 (it becomes a weak pull-down).
    "R10": ("Device:R", "10k", "Resistor_SMD:R_0402_1005Metric", {"1": "IMU_INT1", "2": "PA0"}, {"Note": "IMU INT1 isolation"}),
    "R7": ("Device:R", "4k7", "Resistor_SMD:R_0402_1005Metric", {"1": "+3.3V", "2": "PB6"}, {"Note": "I2C1 SCL pull-up"}),
    "R9": ("Device:R", "4k7", "Resistor_SMD:R_0402_1005Metric", {"1": "+3.3V", "2": "PB7"}, {"Note": "I2C1 SDA pull-up"}),

    # --- Headers ------------------------------------------------------------
    # Top view, USB up: J3 left, J1 right. Pin 1 upper-left; odd pins = left column. JLC assembles them (THT).
    "J1": ("Connector_Generic:Conn_02x10_Odd_Even", "Conn_02x10_Odd_Even", "nicklink:PinHeader_2x10_P2.54mm_Vertical_NoSilk", {
        "1": "+5V", "2": "GND",
        "3": "PB15", "4": "PB14", "5": "PB13", "6": "PB12",
        "7": "PB11", "8": "PB10", "9": "PB2", "10": "PB1",
        "11": "PB0", "12": "PA7", "13": "PA6", "14": "PA5",
        "15": "PA4", "16": "PA3", "17": "PA2", "18": "PA1",
        "19": "PA0", "20": "+3.3V",
    }, {"MPN": "HanElectricity 2541WV-2x10P (male, 6 mm pins, 3 mm tail)"}),
    "J3": ("Connector_Generic:Conn_02x10_Odd_Even", "Conn_02x10_Odd_Even", "nicklink:PinHeader_2x10_P2.54mm_Vertical_NoSilk", {
        "1": "+3.3V", "2": "GND",
        "3": "PA9", "4": "PA10", "5": "PA8", "6": "PA15",
        "7": "PA13", "8": "PA14", "9": "PB3", "10": "NRST",
        "11": "PB4", "12": "PB5", "13": "PB6", "14": "PB7",
        "15": "PB8", "16": "PB9", "17": "PC13", "18": "PC14",
        "19": "PC15", "20": "GND",
    }, {"MPN": "HanElectricity 2541WV-2x10P (male, 6 mm pins, 3 mm tail)"}),
}

# Verified JLC/LCSC part numbers (tools/parts_research.md). "" = choose at order time.
LCSC = {
    "U1": "C8734", "U2": "C2848334", "U3": "C15999", "D2": "C191023", "J2": "C7095263",
    "Y1": "C2682775", "C10": "C1548", "C11": "C1548", "SW1": "C231329", "SW2": "C231329",
    "FB1": "C85812", "C12": "C318563", "C4": "C23733", "R12": "C873764", "F1": "C22435898", "Q1": "C388477",
    "U4": "C41785564", "D1": "C264407", "D3": "C74338", "J1": "C5383109", "J3": "C5383109",
}
for _ref, (_sym, _val, _fp, _pins, _extra) in PARTS.items():
    _lcsc = LCSC.get(_ref) or {"100n": "C1525", "1u": "C52923", "10k": "C25744", "5k1": "C25905", "1k5": "C25867", "4k7": "C25900",
                                "2k2": "C25879", "330": "C25104"}.get(_val, "")
    if _lcsc:
        _extra.setdefault("LCSC", _lcsc)

# Board-only parts (no schematic symbol)
BOARD_ONLY = {
    "H1": "MountingHole:MountingHole_2.2mm_M2",
    "H2": "MountingHole:MountingHole_2.2mm_M2",
    "H3": "MountingHole:MountingHole_2.2mm_M2",
    "H4": "MountingHole:MountingHole_2.2mm_M2",
}

# Friendly function names for docs/silkscreen
ALIASES = {
    "PA13": "SWDIO", "PA14": "SWCLK", "PB3": "SWO", "PA9": "UART1 TX", "PA10": "UART1 RX",
    "PB6": "I2C1 SCL (4.7k pull-up, IMU)", "PB7": "I2C1 SDA (4.7k pull-up, IMU)", "PB8": "CAN RX (remap)", "PB9": "CAN TX (remap)",
    "PA5": "SPI1 SCK", "PA6": "SPI1 MISO", "PA7": "SPI1 MOSI", "PB2": "BOOT1, 10k pull-down",
    "PC13": "user LED (active low)", "PA2": "UART2 TX", "PA3": "UART2 RX", "PA0": "WKUP / IMU INT1 via 10k",
    "PB10": "I2C2 SCL / UART3 TX", "PB11": "I2C2 SDA / UART3 RX",
    "PB13": "SPI2 SCK", "PB14": "SPI2 MISO", "PB15": "SPI2 MOSI",
}

POWER_NETS = {"GND", "+3.3V", "+3.3VA", "+5V", "VBUS"}

if __name__ == "__main__":
    from collections import defaultdict
    nets = defaultdict(list)
    for ref, (_, _, _, pins, _) in PARTS.items():
        for p, n in pins.items():
            nets[n].append(f"{ref}.{p}")
    singles = [n for n, m in nets.items() if len(m) < 2]
    assert not singles, f"single-pin nets: {singles}"
    hdr = [n for r in ("J1", "J3") for n in PARTS[r][3].values() if n not in POWER_NETS]
    assert len(hdr) == len(set(hdr)) == 34, (len(hdr), len(set(hdr)))
    print(f"{len(PARTS)} parts, {len(nets)} nets, 34 header signals OK")
