# NickLink v1.3 board-test firmware

Bare-metal bring-up firmware for the STM32F103C8 on NickLink, plus a Renode model of the board that runs it headlessly. There are no vendor libraries: `src/regs.h` defines the registers it uses, and newlib-nano supplies `printf`. It builds to about 14 KB of flash.

`build/pins.h` is generated from `../tools/spec.py` by `gen_pins.py` on every build, so the `pins` table and the GPIO walk always match the hardware. `gen_pins.py` also checks every GPIO net in spec.py against the STM32F103 LQFP-48 datasheet pinout, so the build fails if spec.py has a wrong pin.

## Build

```sh
make            # uses a host arm-none-eabi-gcc if there is one, otherwise docker
make DOCKER=1   # always build in docker (image nicklink-fw-build from ./Dockerfile: Ubuntu 24.04 gcc-arm-none-eabi 13.2)
```

The outputs are `build/nicklink-test.elf`, `.bin` and `.map`. The first docker build needs network access for apt. After that, builds work offline.

## Flash

**SWD (ST-Link):** connect J3.1 3V3 (target sense), J3.2 GND, J3.7 SWDIO, J3.8 SWCLK and J3.10 NRST.

```sh
make flash                                   # st-flash --reset write build/nicklink-test.bin 0x08000000
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg -c "program build/nicklink-test.elf verify reset exit"
```

Many "STM32F103C8" parts report a 128 KB flash or are clones with a different IDCODE. If OpenOCD refuses the chip, add `-c "set CPUTAPID 0"` before the target `-f`.

**USART1 ROM bootloader:** use a 3.3 V USB-serial adapter. Connect its RX to J3.3 (PA9, TX) and its TX to J3.4 (PA10, RX). Hold **BOOT**, tap **RESET**, then release BOOT.

```sh
make flash-uart PORT=/dev/ttyUSB0            # stm32flash -w build/nicklink-test.bin -v -g 0x08000000 /dev/ttyUSB0
```

The F103 has no USB DFU bootloader. USB is not used by this firmware (see below).

## Console

USART1 at 115200 8N1 on J3.3/J3.4, the same adapter as the bootloader. At boot the firmware prints a banner: clock source, reset cause, boot mode and IMU status. Then it gives a `>` prompt.

| Command | What it does |
|---|---|
| `info` | Prints the banner again: SYSCLK, clock source (HSE+PLL 72 MHz, or HSI fallback 64 MHz if the crystal doesn't start), reset cause from RCC_CSR, boot mode, PB2/BOOT1 level, flash-size register and UID. |
| `pins` | Lists all 48 MCU pins: function, net, header position, alias and on-board loads. Generated from spec.py. |
| `walk [ms] [all]` | Walks the header GPIOs one at a time. Each pin is driven high, then low, for `ms` per level (default 500), while the other header pins are pulled down. Probe each one with a meter or LED as it goes. It also checks that the pin reads back and that no other header pin follows it (solder bridge), and prints `FAIL ...` lines and a fault count. PA9/PA10 (console) are always skipped. PA13/PA14 (SWD) are skipped unless you add `all`, which turns SWD off until the next reset. Any key aborts. |
| `mon` | Loopback/monitor. All header GPIOs become pulled-down inputs, and every level change is printed. Jumper a pin to 3V3, or to another pin you drive, to test it. PB6/PB7 read 1 because of their 4.7k pull-ups. Any key exits. |
| `imu` | Reads accel (mg), gyro (dps) and temperature once. |
| `i2cscan` | Scans I2C1. Expect `0x6A`. |
| `mco [hse\|pll\|hsi\|off]` | Clock output on PA8 (J3.5). Default HSE (expect 8.000 MHz). `pll` = PLL/2 = 36 MHz. Use it to check the crystal frequency without loading the crystal with a probe (README bring-up step 3). |
| `reset` | Software reset (SYSRESETREQ). |

The firmware also does these at boot:

- **Clocks:** HSE 8 MHz → PLL ×9 = 72 MHz, APB1 36 MHz, USB prescaler /1.5 = 48 MHz, 2 flash wait states. If HSERDY doesn't come up within about 100 ms, it falls back to HSI/2 ×16 = 64 MHz and says so. USB cannot run on HSI. Every wait has a timeout, so a dead crystal never hangs the board.
- **Reset cause:** the RCC_CSR flags are read and then cleared with RMVF. Power-on shows as `power-on`. Pressing **RESET** shows as `NRST pin (RESET button)`, which is how you check that the button works.
- **BOOT0** is not a GPIO on the F103, and it is only sampled at reset. The firmware infers it instead. If the word at 0x0 equals the flash vector table, flash was aliased, so BOOT0 was low. If you see `0x0 is NOT flash`, the chip started from the bootloader (for example via `stm32flash -g`). PB2/BOOT1 is a normal GPIO, so its 10k pull-down is read directly and should read 0.
- **User LED:** PC13, push-pull, low = on. It blinks at 1 Hz from SysTick. If the board hard-faults, the LED stays solid on.
- **JTAG:** AFIO SWJ_CFG is set to "SWD only". This frees PA15, PB3 and PB4, which are JTDI, JTDO and NJTRST at reset and can't be used as GPIO until this is done.
- **USB:** no stack. PA12 (D+) is held low, so the host sees nothing attached rather than a device that never answers. A USB build should release PA12 at least 10 ms after boot; that forces re-enumeration against the fixed 1.5k pull-up.
- **IMU (LSM6DSV16X @ 0x6A):** the firmware runs I2C bus recovery (9 SCL clocks if SDA is stuck low, then a STOP), sets I2C1 to 100 kHz, and checks that WHO_AM_I = 0x70. It then does SW_RESET and configures the IMU:
  - INT1 push-pull, active high (IF_CFG PP_OD = 0, H_LACTIVE = 0).
  - Accel 480 Hz ±2 g; gyro 120 Hz ±2000 dps.
  - Tap on X/Y/Z, latched; single and double tap enabled.
  - Wake-up threshold 0.25 g.
  - FUNCTIONS_ENABLE.INTERRUPTS_ENABLE set; MD1_CFG = single tap | double tap | wake-up → INT1.
  - MD1_CFG is read back to confirm the write.
  - PA0 is a pulled-down input on EXTI0 (rising edge). Each event prints `tap`, `double-tap` or `wake`. The firmware reads WAKE_UP_SRC/TAP_SRC, then ALL_INT_SRC to release the latch.
  - The thresholds (`TAP_THS`, `WAKE_THS`, `TAP_DUR`) are `#define`s at the top of `main.c` and need tuning on real hardware.

Not included: USB CDC, which needs a USB device stack of about 1–2 KB plus descriptors, and which Renode can't model on the F1 anyway. SFLP game-rotation-vector FIFO output is also left out; it needs embedded-function-bank access and half-float decoding. Add either when a project needs it.

## Emulation (Renode)

```sh
./test.sh       # make, then renode-test in the antmicro/renode docker image; prints PASS/FAIL per test
```

The first run downloads the STM32F103 SVD that Renode's platform file references. It is cached in `build/home`. The test results go to `build/robot/` (`log.html`, `console.txt`, and snapshots and logs of failed tests). For interactive use, run `cd renode && renode nicklink.resc`, then `start`.

`renode/nicklink.repl` is Renode's `platforms/cpus/stm32f103.repl` plus:

- `rcc` (`NickLinkRCC.cs`): the stock platform has no RCC, only an SVD tag. In this minimal model, the RDY bits follow their ON bits and SWS follows SW. RCC_CSR reset flags start as POR+PIN at power-on, become PIN after each machine reset, and are cleared by RMVF. Setting `HseBroken true` makes the crystal fail.
- `imu` (`LSM6DSV16X.cs`): Renode has no LSM6DSV16X, so this is a minimal model:
  - WHO_AM_I = 0x70, a register file, SW_RESET (IF_CFG survives it), IF_INC.
  - The output registers come from settable `AccX/Y/Z`, `GyroX/Y/Z` and `Temp`.
  - `Tap`, `DoubleTap` and `WakeUp` drive INT1 → PA0 **only if the firmware routed the event**, i.e. INTERRUPTS_ENABLE and the matching MD1_CFG bit are set. They honour H_LACTIVE and LIR, and the ALL_INT_SRC read releases the latch.
- `led`: a Renode LED on PC13, inverted (active low).

Tests in `renode/test.robot`:

| Test | Checks |
|---|---|
| Banner Reports 72 MHz From HSE And Power-On Reset | SYSCLK 72 MHz, HSE→PLL message, `power-on` reset cause, BOOT0-low detection, PB2 = 0 |
| HSE Failure Falls Back To HSI | With `HseBroken`, the firmware reports the HSE failure and runs at 64 MHz without hanging |
| User LED Blinks At 1 Hz | LED model state toggles at 0.5 s on / 0.5 s off |
| IMU WHO_AM_I And Sample | WHO_AM_I = 0x70, config readback OK, `imu` scales the values the model was set to (−1 g, 1 g, 70 dps, 25.0 C), `i2cscan` finds only 0x6A |
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
- **Not modelled at all:** USB, MCO, real tap detection from accelerometer data, the IMU FIFO/SFLP, and ADC.

## Hardware notes found while writing this

1. **Open-drain INT1 doesn't make A0 high-Z by itself.** The main README suggests setting INT1 to open-drain (`PP_OD`) for a high-impedance A0. With the default active-high polarity, the idle (inactive) level is logic 0, which an open-drain output still drives low, so A0 keeps its 10k pull-down. To release A0 when idle you also need `H_LACTIVE = 1` (active low). The interrupt then becomes a falling edge that needs the PA0 internal pull-up, and it can no longer wake the MCU from Standby, because the WKUP pin is rising-edge only. The datasheet (DS13510 Table 30) doesn't spell out the OD + active-high combination, so this needs checking on hardware.
2. **PA0 is never a free input once the IMU is configured.** Push-pull INT1 drives A0 through 10k both ways (low idle, high on events). An external driver on A0 fights it with about 0.33 mA, which is harmless but corrupts ADC readings and lets taps glitch an external signal. The firmware disables EXTI0 during `walk`/`mon` for this reason.
3. **PA15, PB3 and PB4 are JTAG pins at reset:** JTDI (pull-up), JTDO/SWO and NJTRST (pull-up). Firmware must set AFIO SWJ_CFG = 010 before using them, and until then they are not GPIO. The header table lists them as plain GPIO, so a note there would help.
4. **PB2/BOOT1 has a 10k pull-down,** so as an input it reads 0 unless driven, and driving it high costs 0.33 mA. If something external pulls PB2 high while BOOT is held, the chip boots from SRAM instead of the bootloader.
5. **USB with no firmware stack:** the fixed 1.5k D+ pull-up means a host sees a device attach whenever the board is powered, including in the bootloader or under a non-USB firmware. The host then logs enumeration errors. This firmware avoids that by holding PA12 low. A USB application must release PA12 (drive it low for ≥10 ms first) to force re-enumeration.
6. **PB6/PB7 are shared between header and IMU:** driving them as GPIO (`walk`) can generate START/STOP conditions on the IMU's bus. Firmware that reuses them must re-run bus recovery before using I2C again; this firmware does.
7. **The green user LED is dim** (about 0.4 mA through 1.5k, as already noted in docs/REVIEW.md). It is visible but faint next to the red power LED.
8. **MCO on PA8 (J3.5)** is the right way to check the 8 MHz crystal (bring-up step 3), but it is limited to 50 MHz. Use HSE or PLL/2, never SYSCLK at 72 MHz.

There are no pin conflicts: `gen_pins.py` confirms spec.py matches the LQFP-48 pinout, and all 33 header GPIOs are distinct.
