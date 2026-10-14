# NickLink v1.3 bring-up and board test

This takes a freshly assembled board from "just arrived" to "every part checked", in about 15 minutes. You need:

- The board, and a USB-C cable to a computer (or a USB charger) for power.
- An **STLINK-V3MINIE** with its STDC14 flat cable. The cable ends in a 1.27 mm socket, so you also need a way onto the board's 2.54 mm header: an STDC14-to-2.54 mm adapter board (Waveshare sells one with the probe), or 1.27-to-2.54 mm jumper wires.
- A serial terminal: PuTTY, the Arduino serial monitor, `screen`, or `python -m serial.tools.miniterm`.
- Optional: a multimeter, a few jumper wires, and an LED with a 1 kΩ resistor for probing pins.

The test program is [`firmware/`](../firmware/): a bare-metal bring-up firmware for this exact pinout. It comes with a USB DFU bootloader. You flash both **once** with the ST-Link; after that the board is updated and tested over its own USB-C port, and the ST-Link is only for recovery. Prebuilt images are in [`firmware/prebuilt/`](../firmware/prebuilt/), so no toolchain is needed. The console runs on USB-C (a USB serial port) and on USART1 (the ST-Link's virtual COM port).

![Bring-up check points](images/bringup-checkpoints.png)

## 1. Before power

Look the board over for solder bridges, especially at the USB-C pins, the IMU (the small square chip right of the MCU) and the MCU's pins.

With a meter on resistance, check that none of these pairs is a dead short (under 10 Ω):

| Between | Expect |
|---|---|
| J3.1 (3V3) and J3.2 (GND) | Not a short. It reads low at first while the capacitors charge, then rises. |
| J1.1 (5V) and J1.2 (GND) | Not a short |

## 2. First power

Plug USB-C into a computer.

- The **red PWR LED** comes on.
- **J3.1 / J1.20 (3V3)** reads 3.23–3.37 V.
- **J1.1 (5V)** reads about 4.6–4.8 V.
- Unplug, flip the USB-C plug over and plug in again. The LED should light in both orientations.

A brand-new STM32 has no program, so it will not enumerate. The D+ pull-up is hard-wired from VBUS (R2 2.2 kΩ and R11 4.7 kΩ), so the computer still sees a USB device as soon as the cable is plugged in. USB data needs firmware that speaks USB. The test firmware in this guide holds D+ low and keeps USB off.

## 3. Wire the ST-Link

![STLINK-V3MINIE to NickLink wiring](images/bringup-stlink-wiring.png)

| Wire | STLINK-V3MINIE (STDC14 / CN4) | NickLink | Signal |
|---|---|---|---|
| Red | pin 3 T_VCC | J3.1 | 3V3 (the probe only *senses* it) |
| Grey | pin 5 GND | J3.2 | GND |
| Orange | pin 4 T_SWDIO | J3.7 | PA13 SWDIO |
| Green | pin 6 T_SWCLK | J3.8 | PA14 SWCLK |
| Blue | pin 12 T_NRST | J3.10 | NRST |
| Cyan | pin 13 T_VCP_RX | J3.4 | PA10, USART1 RX |
| Magenta | pin 14 T_VCP_TX | J3.3 | PA9, USART1 TX |
| Purple, optional | pin 8 T_SWO | J3.9 | PB3 SWO, for SWV trace only |

- **The probe does not power the board.** Keep the board on USB-C (or 5 V on J1.1) the whole time. T_VCC tells the probe the target's voltage; it supplies nothing.
- **TX and RX are not a mistake.** ST names the VCP pins from the target's side. In UM2910, pin 13 T_VCP_RX is a probe *output* that drives the MCU's RX (PA10), and pin 14 T_VCP_TX is a probe *input* that reads the MCU's TX (PA9).
- **STDC14 pin 1** is marked on the probe and on the cable. Odd pins are in one row and even pins in the other.
- J3 pin 1 is the top-left pin, labelled `3V3`, with the USB-C connector at the top. Odd pins are the outer column, along the board edge.

All the SWD, serial and reset signals are on J3, so one header does everything.

## 4. Flash the bootloader and test firmware (once per board)

`firmware/prebuilt/nicklink-full.hex` holds both: the USB DFU bootloader (first 8 KiB) and the test firmware after it. Use any one of these, with the board powered and the ST-Link plugged into your computer.

**STM32CubeProgrammer (GUI, Windows/macOS/Linux):**
1. Select ST-LINK, port SWD, mode **Under reset**, then **Connect**. "Under reset" uses the NRST wire and works even if the chip is running something that disables SWD.
2. Open `firmware/prebuilt/nicklink-full.hex`, click **Download**, then **Disconnect**. The board starts on its own.

**STM32CubeProgrammer CLI:**
```sh
STM32_Programmer_CLI -c port=SWD mode=UR -w firmware/prebuilt/nicklink-full.hex -v -rst
```

**OpenOCD** (0.12 or newer):
```sh
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
  -c "program firmware/prebuilt/nicklink-full.hex verify reset exit"
```

**stlink tools** (1.8 or newer):
```sh
st-flash --reset --format ihex write firmware/prebuilt/nicklink-full.hex
```

**To build it yourself:** `cd firmware && make flash-full` (or `make DOCKER=1` without an ARM toolchain, then flash `firmware/build/nicklink-full.hex`).

If the tool reports an unknown device ID or refuses the chip, the STM32 may be a clone. For OpenOCD, add `-c "set CPUTAPID 0"` before the target `-f`. CubeProgrammer may also ask to update the ST-Link's own firmware first; let it.

From here on you can unplug the ST-Link. The rest of this guide needs only USB-C.

## 5. Open the console

**On Linux, once per computer:** install the udev rule, so your user can open the board's USB port and its bootloader without sudo:
```sh
sudo cp firmware/udev/70-nicklink.rules /etc/udev/rules.d/ && sudo udevadm control --reload && sudo udevadm trigger
```

The board shows up as a USB serial port called **"NickLink v1.3 test console"**:
- **Linux:** `/dev/serial/by-id/usb-NickLink_NickLink_v1.3_test_console_<serial>-if00` (a `/dev/ttyACM*` device)
- **Windows:** a new COM port
- **macOS:** `/dev/cu.usbmodem*`

Open it with any terminal (`screen /dev/serial/by-id/usb-NickLink* 115200`, PuTTY, the Arduino serial monitor). The baud rate doesn't matter on USB. Opening the port prints the banner. You can also use USART1 through the ST-Link's virtual COM port at 115200 8N1, then press **RESET**.

You should see lines like these:

```
NickLink v1.3 board test, SYSCLK 72000000 Hz
clock: HSE 8 MHz -> PLL x9 = 72 MHz (APB1 36 MHz, ADC 12 MHz, USB 48 MHz), CSS on
RCC_CFGR 0x001D840A, PVD 2.9 V: VDD ok, not from Standby
reset cause: power-on (RCC_CSR 0x...)
boot: flash aliased at 0x0 (BOOT0 was low); BOOT1/PB2 reads 0 (10k pull-down, want 0)
flash size reg 64 KB, UID ...        (many chips report 128 KB)
bootloader: USB DFU at 0x08000000, this app at 0x08002000 (`dfu` or double-tap RESET to enter)
USB: console on USB-C (CDC ACM 1209:0001)
IMU: OK (WHO_AM_I 0x70, tap/wake -> A0)
type 'help'
>
```

Type `help` to list the commands. [`firmware/README.md`](../firmware/README.md) documents each one.

## 6. Test checklist

Work down the list; each line tests one part of the board.

| # | Part | Do this | Pass when |
|---|---|---|---|
| 1 | Power, 3V3 regulator | Steps 2 and 5 | PWR LED on, 3V3 in range, `VDD ok` in the banner |
| 2 | MCU + SWD | Step 4 | Flash and verify succeed, and the board shows up on USB (step 5) |
| 3 | 8 MHz crystal | Read the banner `clock:` line | `HSE 8 MHz -> PLL x9 = 72 MHz` and `SYSCLK 72000000`. A dead crystal shows `64 MHz` / HSI instead. |
| 3b | Crystal accuracy (optional) | `mco`, then put a frequency counter or scope on **J3.5** | 8.000 MHz within about ±30 ppm (±240 Hz). `mco off` stops it. |
| 4 | User LED (green, PC13) | Watch it | Blinks once a second |
| 5 | RESET button | Press it | The banner reprints with `reset cause: NRST pin (RESET button)` |
| 6 | BOOT button | Hold **BOOT**, tap **RESET**, release BOOT | The LED stops blinking and the USB console stops answering: the chip's ROM serial bootloader is running. The PC may still list the port, because the D+ pull-up is wired to VBUS and the ROM bootloader never pulls D+ low. To be sure, the ROM bootloader answers `0x79` to a `0x7F` byte at 115200 8E1 on J3.3/J3.4 (the ST-Link's serial port). Tap RESET again and the test firmware comes back. |
| 6b | USB DFU bootloader | Type `dfu` | The console closes, the green LED goes solid, and a USB device "NickLink DFU bootloader" (`1209:db42`) appears (`dfu-util -l`). Tap RESET to leave it, or reflash as in step 7. **Double-tap RESET** (second press while the LED is lit, within about 0.4 s) gets you there too. |
| 7 | IMU on I2C | `i2cscan` | Only `0x6A` is found. The banner showed `WHO_AM_I = 0x70`. |
| 8 | IMU data | Lay the board flat, run `imu` | Accel about `0 0 1000` mg (±60), gyro within a few dps of 0, temperature near room temperature. Flip it upside down: Z reads about −1000. |
| 9 | IMU interrupt, INT1 → A0 | Tap the board near the IMU, double-tap it, give it a shake | Prints `tap`, `double-tap` and `wake`. Thresholds are `#define`s at the top of `firmware/src/main.c` if it is too eager or too deaf. |
| 10 | Every header GPIO (outputs, shorts) | Unplug anything else from the headers, run `walk`. Optionally follow along with an LED + 1 kΩ to GND on each pin as it is named. | Ends with `walk done: N pins, 0 faults`. Any `FAIL` names the pin and whether it looks shorted to GND, 3V3 or another pin. |
| 11 | Every header GPIO (inputs) | `mon`, then touch a jumper from 3V3 (J3.1) to each pin in turn | Each touch prints `mon: J1.x PAy=1`, then `=0` on release. B6/B7 sit at 1 (I2C pull-ups). |
| 12 | ADC | `adc`, then jumper A1 (J1.18) to 3V3 and run `adc` again | VDDA about 3300 mV. A1 reads about 3300 mV with the jumper. A0 reads about 0 (it has 10 kΩ to the IMU's INT1). |
| 13 | Standby + wake on A0 | `standby`, wait a second, then tap the board | The LED goes out and the console stops answering (the port can stay listed, as for BOOT). A tap restarts the board, and the banner says `woke from Standby`. RESET also wakes it. |
| 14 | USB-C data, both orientations | Unplug the USB-C cable, flip the plug over, plug it back in | The console port comes back both ways round (D+/D− and CC are wired for both orientations). |

Two pin groups are never walked:
- **J3.3/J3.4 (USART1):** the second console runs over them. Check them with the ST-Link's virtual COM port, or skip them.
- **J3.7/J3.8 (SWD):** flashing proves them. `walk all` includes them, but disables the debugger until the next reset.

Record anything odd, especially the crystal frequency, any `FAIL` line, and IMU readings that look wrong. Those are the open items in [`REVIEW.md`](REVIEW.md).

## 7. Updating the firmware over USB

Once a board has the bootloader, new firmware goes in over USB-C:

```sh
cd firmware
make dfu        # builds, tells the running test firmware to enter the bootloader, flashes, restarts
```

Without `make`: `dfu-util -w -R -d 1209:db42 -a 0 -D firmware/prebuilt/nicklink-test.dfu`. `-w` waits for the bootloader to appear, and `-R` restarts the board afterwards. dfu-util may then print an error from that restart even after `Done!`; the board reconnecting with the new firmware is what counts.

With several boards plugged in, choose one: `make dfu CONSOLE=/dev/serial/by-id/usb-NickLink_..._<UID>-if00`. The bootloader uses the same USB serial (the UID in the banner), so only that board is flashed.

Ways into the bootloader (green LED solid on):
- `dfu` on the console (`make dfu` does this for you)
- **double-tap RESET**: after any reset the LED lights for about 0.4 s, and a second press in that time enters it
- **jumper J1.9 to 3V3 while pressing RESET**, which needs no working firmware at all
- automatically, if there's no valid firmware at 0x08002000

Your own programs must be linked at **0x08002000** (the first 8 KiB belong to the bootloader). They should also set `SCB->VTOR` to their vector table. See `firmware/stm32f103c8.ld` and `src/startup.c`.

The ST-Link is still needed to put the bootloader back if it is gone (for example after a full-chip erase), or to install a new version of it: USB updates only write the firmware above it. Use step 4, or the chip's ROM serial bootloader (`make flash-uart`, see `firmware/README.md`).

## Troubleshooting

| Symptom | Check |
|---|---|
| Programmer can't connect | Board powered from USB-C? GND wired? T_VCC to J3.1 (the probe reads the target voltage from it; 0 V there blocks the connection)? Try mode **Under reset**, or lower the SWD speed to 1 MHz. |
| Programs fine but the console is silent | Right COM port and 115200 baud? Press RESET. Check that the cyan wire goes to J3.4 and the magenta to J3.3. If they were swapped, swap them (harmless). |
| Banner says HSI / 64 MHz | Crystal Y1 or its 15 pF caps (C10/C11) are not oscillating. Check their soldering. The board still works on the internal oscillator, but USB needs the crystal. |
| `IMU: no ACK at 0x6A` | IMU solder joints (an LGA, inspect under magnification). Check that R7/R9 (I2C pull-ups) are fitted. Also check that nothing on J3.13/J3.14 (B6/B7) is pulling the bus low. |
| `walk` reports `FAIL ... follows ...` | Solder bridge between the two named pins, at the header or at the MCU |
| Green LED solid on, no console | Either the board is in the DFU bootloader (`dfu-util -l` lists `1209:db42`; flash with `make dfu`, or press RESET to leave), or the firmware hard-faulted (re-flash, then press RESET). |
| No NickLink USB port appears | Check the banner's `USB:` line over the ST-Link's COM port. USB needs the crystal (72 MHz). Try another cable, since some are charge-only. On Linux, check `journalctl -k` for `NickLink`. |
| `dfu-util: LIBUSB_ERROR_ACCESS` or `Permission denied` on the port | Install the udev rule (step 5), then unplug and replug the board. |
| `dfu-util` waits forever | The board isn't in the bootloader. Double-tap RESET until the green LED stays on. |
| `Cannot claim interface - LIBUSB_ERROR_BUSY` | fwupd (on most Linux desktops) briefly claims every DFU device as it appears. `make dfu` tries again by itself; with plain `dfu-util`, run the same command again. The board stays in the bootloader until a download succeeds. |
| `More than one DFU capable USB device found` | Several boards are in the bootloader. Unplug the others, or pick one with `dfu-util -S <UID>` (`dfu-util -l` shows each board's serial). |
