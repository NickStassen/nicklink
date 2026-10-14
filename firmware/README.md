# NickLink v1.3 board-test firmware

Bare-metal bring-up firmware for the STM32F103C8 on NickLink, a USB DFU bootloader that loads it over USB-C, and a Renode model of the board that runs both headlessly. The firmware uses no vendor libraries: `src/regs.h` defines the registers it uses, and newlib-nano supplies `printf`. It builds to about 22 KB of flash, and its console runs on USB-C (a USB serial port) and on USART1.

**Flash layout:** the bootloader occupies the first 8 KiB (0x08000000–0x08001FFF), and the test firmware is linked to 0x08002000 (56 KiB available). The ST-Link is needed once per board, to put both on (`make flash-full`). After that, `make dfu` updates the firmware over USB-C, and the ST-Link is only for recovery.

`build/pins.h` is generated from `../tools/spec.py` by `gen_pins.py` on every build, so the `pins` table and the GPIO walk always match the hardware. `gen_pins.py` also checks every GPIO net in spec.py against the STM32F103 LQFP-48 datasheet pinout, so the build fails if spec.py has a wrong pin.

## Build

```sh
make            # uses a host arm-none-eabi-gcc if there is one, otherwise docker
make DOCKER=1   # always build in docker (image nicklink-fw-build from ./Dockerfile: Ubuntu 24.04 gcc-arm-none-eabi 13.2)
```

| Output | What it is |
|---|---|
| `build/nicklink-test.elf` / `.bin` / `.map` | The test firmware, linked at 0x08002000 |
| `build/nicklink-test.dfu` | The same `.bin` with a DFU suffix, for `dfu-util` |
| `build/nicklink-full.bin` / `.hex` | Bootloader padded to 8 KiB, then the firmware: flash at 0x08000000 |

The first docker build needs network access for apt. After that, builds work offline. The full image uses `build/nicklink-bootloader.bin` if you built the bootloader, otherwise the committed `prebuilt/nicklink-bootloader.bin`.

`prebuilt/` holds the three files you need without a toolchain: `nicklink-full.hex` (ST-Link, once), `nicklink-test.dfu` (USB updates) and `nicklink-bootloader.bin`. Refresh them with `make prebuilt` after changing the source.

## Flash

[`docs/BRINGUP.md`](../docs/BRINGUP.md) has the STLINK-V3MINIE wiring and the step-by-step board test.

**Once per board, with the ST-Link** (J3.1 3V3 sense, J3.2 GND, J3.7 SWDIO, J3.8 SWCLK, J3.10 NRST):

```sh
make flash-full      # st-flash --reset write build/nicklink-full.bin 0x08000000
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "program prebuilt/nicklink-full.hex verify reset exit"
```

Many "STM32F103C8" parts report a 128 KB flash or are clones with a different IDCODE. If OpenOCD refuses the chip, add `-c "set CPUTAPID 0"` before the target `-f`.

**From then on, over USB-C (no ST-Link):**

```sh
make dfu             # asks the running test firmware to reboot into the bootloader, then flashes build/nicklink-test.dfu
dfu-util -w -R -d 1209:db42 -a 0 -D prebuilt/nicklink-test.dfu   # the same without make; -w waits for the bootloader, -R restarts the board
```

`make dfu` finds the board's console under `/dev/serial/by-id/usb-NickLink*` and sends it `dfu`. If no NickLink console is there (a firmware without USB, a crash), enter the bootloader by hand first: **double-tap RESET**. The green LED stays solid on in the bootloader. After the download dfu-util prints `Done!` and restarts the board into the new firmware. dfu-util 0.11 then exits with code 251, because the board disappears during that reset; `make dfu` treats that as success.

**Several boards connected:** `make dfu` won't guess. It lists the consoles it found, and you pick one with `make dfu CONSOLE=/dev/serial/by-id/usb-NickLink_..._<UID>-if00`. The bootloader reports the same USB serial as the console (the chip UID the banner prints), so `make dfu` passes it to `dfu-util -S` and flashes only that board. For a board that is already in the bootloader, use `dfu-util -l` to list the boards and `dfu-util -S <UID> ...` to pick one.

**Linux permissions:** install the udev rule once so your user can use the bootloader and the console without sudo:

```sh
sudo cp udev/70-nicklink.rules /etc/udev/rules.d/ && sudo udevadm control --reload && sudo udevadm trigger
```

**Recovery** (bootloader erased or broken, firmware that won't start):
- ST-Link: `make flash-full` writes the bootloader and firmware again. `make flash` writes only the firmware at 0x08002000.
- USART1 ROM bootloader, no ST-Link: a 3.3 V USB-serial adapter, its RX on J3.3 (PA9) and TX on J3.4 (PA10). Hold **BOOT**, tap **RESET**, release BOOT, then `make flash-uart PORT=/dev/ttyUSB0` (writes the full image with `stm32flash`).

## Bootloader

`bootloader/` builds [dapboot](https://github.com/devanlai/dapboot) (ISC licence), a USB DFU 1.1 bootloader on libopencm3, for NickLink. `make bootloader` fetches dapboot at a pinned commit (needs git, network once, a host `arm-none-eabi-gcc` and python3), applies `bootloader/nicklink.patch`, adds the `bootloader/nicklink/` target and builds `build/nicklink-bootloader.bin` (about 7.6 KB of its 8 KiB slot).

It enters DFU mode (USB `1209:db42` "NickLink DFU bootloader", green LED solid on) when any of these holds:

| Way in | How |
|---|---|
| `dfu` command | The test firmware writes `0x4F42` to BKP_DR1 and resets |
| Double-tap RESET | After every reset the green LED lights for about 0.4 s. A second press inside that window enters DFU. The flag lives in BKP_DR2, which survives a reset (VBAT is tied to 3V3) but not a power cycle. |
| J1.9 at reset | Jumper J1.9 (PB2/BOOT1, 10k pull-down) to 3V3 while pressing RESET. This needs no working firmware at all. |
| No valid firmware | Nothing usable at 0x08002000 (its first word isn't a RAM address) |

Otherwise it starts the firmware at 0x08002000. NickLink changes to stock dapboot:
- **A dead crystal doesn't hang it.** Stock dapboot waits for the 8 MHz crystal forever. This one gives it about 0.1 s and falls back to HSI 48 MHz, so the test firmware still starts and reports `HSE FAILED`. USB is outside its spec on HSI, so use the ST-Link or the ROM bootloader on a board like that.
- **Double-tap RESET entry** and the LED states.
- **Only the flash the chip reports** (64 KiB) is writable.
- **The same USB serial as the test firmware**, so `dfu-util -S <UID>` finds a board in either mode.
- **It finishes downloads quietly** (`DFU_WILL_DETACH 0`). After a download it reports success and waits; `dfu-util -R` then restarts it into the new firmware. Without `-R`, press RESET.

The bootloader can't replace itself over USB: dfu-util writes from 0x08002000 up. To install a new bootloader, run `make bootloader flash-full` with the ST-Link.

Because the D+ pull-up is hard-wired (R2/R11 from VBUS), both the bootloader and the firmware pull D+ (PA12) low for ≥10 ms at startup, so the PC sees a fresh device after every reset.

## Console

The same console runs on two ports:
- **USB-C:** a USB serial port (CDC ACM, `1209:0001` "NickLink v1.3 test console"), `/dev/serial/by-id/usb-NickLink_NickLink_v1.3_test_console_<UID>-if00` on Linux (a `ttyACM` device), a COM port on Windows, `/dev/cu.usbmodem*` on macOS. The baud rate setting doesn't matter. Opening the port prints the banner again, so you never miss it. Output is dropped while no terminal has the port open.
- **USART1:** 115200 8N1 on J3.3/J3.4, for example through the ST-Link's virtual COM port.

At boot the firmware prints a banner: clock source, reset cause, boot mode, bootloader, USB and IMU status. Then it gives a `>` prompt.

| Command | What it does |
|---|---|
| `info` | Prints the banner again: SYSCLK, clock source (HSE+PLL 72 MHz, or HSI fallback 64 MHz if the crystal doesn't start), reset cause from RCC_CSR, boot mode, PB2/BOOT1 level, flash-size register and UID. |
| `pins` | Lists all 48 MCU pins: function, net, header position, alias and on-board loads. Generated from spec.py. |
| `walk [ms] [all]` | Walks the header GPIOs one at a time. Each pin is driven high, then low, for `ms` per level (default 500), while the other header pins are pulled down. Probe each one with a meter or LED as it goes. It also checks that the pin reads back and that no other header pin follows it (solder bridge), and prints `FAIL ...` lines and a fault count. PA9/PA10 (console) are always skipped. PA13/PA14 (SWD) are skipped unless you add `all`, which turns SWD off until the next reset. Any key aborts. |
| `mon` | Loopback/monitor. All header GPIOs become pulled-down inputs, and every level change is printed. Jumper a pin to 3V3, or to another pin you drive, to test it. PB6/PB7 read 1 because of their 4.7k pull-ups. Any key exits. |
| `imu` | Reads accel (mg), gyro (dps) and temperature once. |
| `stream [hz]` | Raw IMU samples at a fixed rate (default 200 Hz, up to 500) until any key: `S <ms> ax ay az gx gy gz`, accel 0.061 mg/LSB and gyro 70 mdps/LSB. While a terminal has the USB port open they go to USB only, so USART1's baud rate doesn't limit them. `imu_viewer.py` uses it. |
| `i2cscan` | Scans I2C1. Expect `0x6A`. |
| `mco [hse\|pll\|hsi\|off]` | Clock output on PA8 (J3.5). Default HSE (expect 8.000 MHz). `pll` = PLL/2 = 36 MHz. Use it to check the crystal frequency without loading the crystal with a probe (README bring-up step 3). |
| `clock` | Same as `info`. |
| `adc` | ADC1 single conversions (ADC clock 12 MHz, 239.5-cycle sample, calibrated first): PA0-PA7 (ch0-7), PB0/PB1 (ch8/9) in raw counts and mV, plus VREFINT (ch17) to estimate VDDA (VREFINT 1.20 V typ, so +-3 % at best). The pins are analog only while the command runs and are restored afterwards. |
| `standby` | Enters Standby (PWR_CR PDDS, SLEEPDEEP, WFI) with PA0/WKUP armed. It first reads the IMU's ALL_INT_SRC so INT1 is low, and PA0 is a floating input (A0 already has 10k to INT1). A rising edge on PA0 (a tap/wake event from the IMU, or a jumper to 3V3) wakes the MCU, which resets; the banner then says `woke from Standby` (PWR_CSR.SBF, cleared with CSBF). RESET also wakes it. |
| `reset` | Software reset (SYSRESETREQ). |
| `dfu` | Reboots into the USB DFU bootloader (writes dapboot's `0x4F42` to BKP_DR1, then resets). `make dfu` sends this for you. |

The firmware also does these at boot:

- **Vector table:** `Reset_Handler` first points SCB->VTOR at the firmware's own table (0x08002000, the linker symbol `__vectors_start`). It doesn't rely on whatever the DFU bootloader, the ROM bootloader (`stm32flash -g`) or a debugger left there; without this, the first interrupt can land in the wrong table.
- **Clocks:** `clock_init` does not assume a fresh reset: it switches SYSCLK to HSI, turns the PLL (and CSS) off, then sets HSE 8 MHz → PLL ×9 = 72 MHz, APB1 36 MHz, ADC /6 = 12 MHz (limit 14), USB prescaler /1.5 = 48 MHz, 2 flash wait states. The banner prints RCC_CFGR (expect `0x001D840A` on the HSE path).
- **Clock Security System:** CSSON is set once HSE is ready. If the crystal fails later, hardware drops SYSCLK to HSI and raises NMI; `NMI_Handler` clears CSSF, retunes SysTick and the UART baud for 8 MHz, and records the failure (`info`/`clock` then says `HSE FAILED at runtime`). The MCU keeps running on HSI.
- **PVD:** enabled at 2.9 V (PWR_CR PLS=111). It is polled, not interrupt driven: the banner shows `VDD ok` or `VDD BELOW threshold` (PWR_CSR.PVDO) as of boot, and `info` re-reads it. If HSERDY doesn't come up within about 100 ms, it falls back to HSI/2 ×16 = 64 MHz and says so. USB cannot run on HSI. Every wait has a timeout, so a dead crystal never hangs the board.
- **Reset cause:** the RCC_CSR flags are read and then cleared with RMVF. Power-on shows as `power-on`. Pressing **RESET** shows as `NRST pin (RESET button)`, which is how you check that the button works.
- **BOOT0** is not a GPIO on the F103, and it is only sampled at reset. The firmware infers it instead. If the word at 0x0 equals the flash vector table, flash was aliased, so BOOT0 was low. If you see `0x0 is NOT flash`, the chip started from the bootloader (for example via `stm32flash -g`). PB2/BOOT1 is a normal GPIO, so its 10k pull-down is read directly and should read 0.
- **User LED:** PC13, push-pull, low = on. It blinks at 1 Hz from SysTick. If the board hard-faults, the LED stays solid on.
- **JTAG:** AFIO SWJ_CFG is set to "SWD only". This frees PA15, PB3 and PB4, which are JTDI, JTDO and NJTRST at reset and can't be used as GPIO until this is done.
- **USB:** `src/usb_cdc.c` is a bare-metal full-speed CDC ACM device: EP0 control, EP1 bulk 64 B each way, EP2 interrupt IN (never used), a 2 KiB output ring and the shared 256-byte input ring. PA12 (D+) is held low from reset until the IMU is set up, then handed to the USB peripheral, so the host always sees a fresh attach against the fixed D+ pull-up (R2 2k2 from VBUS with R11 4k7 to GND). USB starts only when SYSCLK is 72 MHz from the crystal (USB clock = PLL / 1.5 = 48 MHz). `bInterfaceProtocol` is 0 (no AT commands), so ModemManager doesn't probe it. VID:PID 1209:0001 is the pid.codes test ID: fine for your own boards, not for a product.
- **IMU (LSM6DSV @ 0x6A):** the firmware runs I2C bus recovery (9 SCL clocks if SDA is stuck low, then a STOP), sets I2C1 to 100 kHz, and checks that WHO_AM_I = 0x70. It then does SW_RESET and configures the IMU:
  - INT1 push-pull, active high (IF_CFG PP_OD = 0, H_LACTIVE = 0).
  - Accel 480 Hz ±2 g; gyro 120 Hz ±2000 dps.
  - Tap on X/Y/Z, latched; single and double tap enabled.
  - Wake-up threshold 0.25 g.
  - FUNCTIONS_ENABLE.INTERRUPTS_ENABLE set; MD1_CFG = single tap | double tap | wake-up → INT1.
  - MD1_CFG is read back to confirm the write.
  - PA0 is a pulled-down input on EXTI0 (rising edge). Each event prints `tap`, `double-tap` or `wake`. The firmware reads WAKE_UP_SRC/TAP_SRC, then ALL_INT_SRC to release the latch.
  - The thresholds (`TAP_THS`, `WAKE_THS`, `TAP_DUR`) are `#define`s at the top of `main.c` and need tuning on real hardware.

Not included: SFLP game-rotation-vector FIFO output, which needs embedded-function-bank access and half-float decoding. Add it when a project needs it; `usb_cdc.c` is reusable for streaming the result to a PC.

## 3D IMU viewer

`imu_viewer.py` shows a 3D model of the board that follows the real one, from the IMU. It starts `stream` on the USB console, removes the gyro's offset, and fuses gyro and gravity with a Madgwick filter. The model uses the board's real dimensions and part positions from `nicklink.kicad_pcb`.

```sh
python3 imu_viewer.py            # finds /dev/serial/by-id/usb-NickLink*; or give the port
python3 imu_viewer.py --selftest # checks the filter maths, no board needed
```

It needs PyQt6 and numpy (`pip install PyQt6 numpy`), and runs on Linux or macOS. Lay the board still for a moment after it connects, so the gyro offset can be measured. The mouse orbits and zooms the view. **R** zeroes the heading, **C** measures the gyro offset again (hold still), and **Space** freezes the view. Tilt is absolute, because gravity corrects it. Heading slowly drifts, because the board has no magnetometer.

## Emulation (Renode)

```sh
./test.sh       # make, then renode-test in the antmicro/renode docker image; prints PASS/FAIL per test
```

The emulated board runs the full image, bootloader then firmware, from the same `build/nicklink-full.bin` you flash. The first run downloads the STM32F103 SVD that Renode's platform file references. It is cached in `build/home`. The test results go to `build/robot/` (`log.html`, `console.txt`, and snapshots and logs of failed tests). For interactive use, run `cd renode && renode nicklink.resc`, then `start`.

`renode/nicklink.repl` is Renode's `platforms/cpus/stm32f103.repl` plus:

- `rcc` (`NickLinkRCC.cs`): the stock platform has no RCC, only an SVD tag. In this minimal model, the RDY bits follow their ON bits and SWS follows SW. RCC_CSR reset flags start as POR+PIN at power-on, become PIN after each machine reset, and are cleared by RMVF. Setting `HseBroken true` makes the crystal fail.
- `imu` (`LSM6DSV16X.cs`): Renode has no LSM6DSV-family model, so this is a minimal one. It was written from the LSM6DSV16X datasheet; every register it models has the same address and bits on the board's LSM6DSV:
  - WHO_AM_I = 0x70, a register file, SW_RESET (IF_CFG survives it), IF_INC.
  - The output registers come from settable `AccX/Y/Z`, `GyroX/Y/Z` and `Temp`.
  - `Tap`, `DoubleTap` and `WakeUp` drive INT1 → PA0 **only if the firmware routed the event**, i.e. INTERRUPTS_ENABLE and the matching MD1_CFG bit are set. They honour H_LACTIVE and LIR, and the ALL_INT_SRC read releases the latch.
- `led`: a Renode LED on PC13, inverted (active low).

Tests in `renode/test.robot`:

| Test | Checks |
|---|---|
| Banner Reports 72 MHz From HSE And Power-On Reset | The bootloader starts the firmware; SYSCLK 72 MHz, RCC_CFGR readback 0x001D840A (PLL x9 from HSE, APB1 /2, ADC /6), HSE→PLL message, `power-on` reset cause, BOOT0-low detection, PB2 = 0, the bootloader detected at 0x08000000, USB console line |
| HSE Failure Falls Back To HSI | With `HseBroken`, the bootloader falls back to HSI and still starts the firmware, which reports the HSE failure and runs at 64 MHz without hanging |
| User LED Blinks At 1 Hz | LED model state toggles at 0.5 s on / 0.5 s off |
| IMU WHO_AM_I And Sample | WHO_AM_I = 0x70, config readback OK, `imu` scales the values the model was set to (−1 g, 1 g, 70 dps, 25.0 C), `i2cscan` finds only 0x6A |
| Stream Prints Raw IMU Samples | `stream 50` reports its rate and prints `S` lines with the raw values the model was set to; a key stops it |
| Tap Double-Tap And Wake On INT1 | Each event arrives through INT1 → PA0 → EXTI0 and prints `tap` / `double-tap` / `wake`; PA0 is low again afterwards (latch released) |
| Pins Command Lists Generated Map | `pins` output matches spec.py rows |
| GPIO Walk Drives Each Header Pin Alone | For every walked header pin (list parsed from the generated `pins.h`): the pin is high in the GPIO model, it is the **only** pin set on ports A/B/C, then it goes low; `0 faults` |
| Monitor Mode Sees Header Inputs | Driving PB12 and PC15 inputs from the test prints their level changes |
| NRST Reset Reports Pin Reset | After `machine Reset`, the reset cause is `NRST pin (RESET button)` |
| Software Reset Command Reboots | `reset` reboots the firmware to the prompt |

**What the emulation does not verify:**

- **Real clock behaviour:** the RCC is my own model, which makes PLL/HSE ready instantly. FLASH_ACR is not modelled, and SysTick runs at a fixed 72 MHz in Renode even in HSI fallback. Check the clocks on hardware with `mco`.
- **I2C electrical/timing and the exact F1 receive sequence:** Renode 1.16's `STM32F4_I2C` (reused for the F1) ignores ACK/NACK and fetches one byte per address phase, so the IMU model returns 16-byte bursts. The firmware's N-byte read follows the usual "NACK+STOP after byte N−2" pattern, but the RM0008 errata-safe sequences can only be proven on hardware. Pull-ups are not modelled: SDA reads 0 in recovery, so the 9-clock recovery always runs (harmless).
- **AFIO:** SWJ_CFG and EXTICR are not modelled, because Renode wires every port's pin 0 to EXTI0 directly. So JTAG release of PA15/PB3/PB4 and the "PA0 not PB0" EXTI selection are untested.
- **Pull resistors:** pull-up/pull-down and the ODR-before-mode-switch latching on inputs are not modelled. Renode ignores ODR writes to input pins. The short/bridge detection in `walk` therefore only ran fault-free; in emulation a real short can't be injected.
- **Reset types:** software reset reports `NRST pin` in Renode. Real F1 silicon reports `software` (SFTRSTF, with PINRSTF also set).
- **ADC, PWR, Standby, CSS/PVD:** Renode's ADC does not convert (the `adc` command prints `timeout` per channel and returns, so it is untested), PWR is unmapped (PVD reads ok, SBF reads 0, `standby` is not testable), and the RCC model never raises CSSF/NMI. The new clock sequence needed no RCC model change: ready bits already follow HSION/HSEON/PLLON, so HSI switch and PLL off work as is, and a written CSSON bit simply reads back.
- **Not modelled at all:** USB (so the USB console, DFU download and the bootloader's DFU mode are tested on hardware only), the backup registers (so the `dfu` command and double-tap entry are hardware-only too), MCO, real tap detection from accelerometer data, the IMU FIFO/SFLP.
- **Peripherals only used as GPIO:** USART2/3, SPI1/2 and I2C2 are not exercised as peripherals; the `walk` only drives their pins as plain GPIO.

## Hardware notes found while writing this

1. **Open-drain INT1 doesn't make A0 high-Z by itself.** The main README suggests setting INT1 to open-drain (`PP_OD`) for a high-impedance A0. With the default active-high polarity, the idle (inactive) level is logic 0, which an open-drain output still drives low, so A0 keeps its 10k pull-down. To release A0 when idle you also need `H_LACTIVE = 1` (active low). The interrupt then becomes a falling edge that needs the PA0 internal pull-up, and it can no longer wake the MCU from Standby, because the WKUP pin is rising-edge only. The datasheet (DS13510 Table 30) doesn't spell out the OD + active-high combination, so this needs checking on hardware.
2. **PA0 is never a free input once the IMU is configured.** Push-pull INT1 drives A0 through 10k both ways (low idle, high on events). An external driver on A0 fights it with about 0.33 mA, which is harmless but corrupts ADC readings and lets taps glitch an external signal. The firmware disables EXTI0 during `walk`/`mon` for this reason.
3. **PA15, PB3 and PB4 are JTAG pins at reset:** JTDI (pull-up), JTDO/SWO and NJTRST (pull-up). Firmware must set AFIO SWJ_CFG = 010 before using them, and until then they are not GPIO. The header table lists them as plain GPIO, so a note there would help.
4. **PB2/BOOT1 has a 10k pull-down,** so as an input it reads 0 unless driven, and driving it high costs 0.33 mA. If something external pulls PB2 high while BOOT is held, the chip boots from SRAM instead of the bootloader.
5. **The D+ pull-up is hard-wired:** R2 2k2 from VBUS with R11 4k7 to GND means a host sees a device attach whenever the board is powered, including in the ROM bootloader or under a firmware without USB. The host then logs enumeration errors. Firmware without USB should hold PA12 low; firmware with USB should drive it low for ≥10 ms at startup before enabling the USB peripheral, which forces re-enumeration. The DFU bootloader and this firmware both do.
6. **PB6/PB7 are shared between header and IMU:** driving them as GPIO (`walk`) can generate START/STOP conditions on the IMU's bus. Firmware that reuses them must re-run bus recovery before using I2C again; this firmware does.
7. **The green user LED is modest** (R6 is 330 ohm, about 1.3 mA, brighter than the original 1.5k, but still modest). It is visible next to the red power LED.
8. **MCO on PA8 (J3.5)** is the right way to check the 8 MHz crystal (bring-up step 3), but it is limited to 50 MHz. Use HSE or PLL/2, never SYSCLK at 72 MHz.

There are no pin conflicts: `gen_pins.py` confirms spec.py matches the LQFP-48 pinout, and all 33 header GPIOs are distinct.
