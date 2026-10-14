# NickLink v1.3 board-test firmware, linked to run after the USB DFU bootloader (bootloader/, first 8 KiB).
# Uses a host arm-none-eabi-gcc if there is one, else (or with DOCKER=1) the compiler in docker (./Dockerfile).
#
#   make              app (build/nicklink-test.*) + full image (build/nicklink-full.*: bootloader + app)
#   make flash-full   ST-Link, once per board or for recovery: bootloader + app at 0x08000000
#   make dfu          USB-C only: asks the running test firmware to enter the bootloader, then flashes the app
#   make flash        ST-Link: app only (keeps the bootloader)
#   make bootloader   rebuild the bootloader from dapboot (host toolchain, git, network once)
TARGET := build/nicklink-test
FULL   := build/nicklink-full
BOOT   := $(firstword $(wildcard build/nicklink-bootloader.bin) prebuilt/nicklink-bootloader.bin)

ifneq ($(DOCKER)$(if $(shell command -v arm-none-eabi-gcc),,1),)
RUN   := docker run --rm -u $(shell id -u):$(shell id -g) -v $(abspath ..):/w -w /w/firmware nicklink-fw-build
IMAGE := build/.image
else
RUN   :=
IMAGE :=
endif

CFLAGS  := -mcpu=cortex-m3 -mthumb -Os -g3 -std=gnu11 -Wall -Wextra -ffunction-sections -fdata-sections --param=min-pagesize=0 -Ibuild
LDFLAGS := -T stm32f103c8.ld -nostartfiles --specs=nano.specs -Wl,--gc-sections -Wl,-Map=$(TARGET).map
SRCS    := $(wildcard src/*.c)

all: $(TARGET).bin $(TARGET).dfu $(FULL).bin $(FULL).hex

build/.image: Dockerfile
	@mkdir -p build
	docker build -q -t nicklink-fw-build . >/dev/null && touch $@

build/pins.h: gen_pins.py ../tools/spec.py
	@mkdir -p build
	python3 gen_pins.py > $@.tmp && mv $@.tmp $@

$(TARGET).elf: $(SRCS) $(wildcard src/*.h) build/pins.h stm32f103c8.ld | $(IMAGE)
	$(RUN) arm-none-eabi-gcc $(CFLAGS) $(SRCS) $(LDFLAGS) -o $@
	$(RUN) arm-none-eabi-size $@

$(TARGET).bin: $(TARGET).elf
	$(RUN) arm-none-eabi-objcopy -O binary $< $@

# DFU file: the .bin plus a DFU suffix (USB ID of the bootloader), so dfu-util doesn't warn
$(TARGET).dfu: $(TARGET).bin
	cp $< $@
	dfu-suffix -v 1209 -p db42 -a $@ >/dev/null 2>&1 || true

# bootloader padded to 8 KiB with 0xFF, then the app
$(FULL).bin: $(BOOT) $(TARGET).bin
	python3 -c "import sys; b=open(sys.argv[1],'rb').read(); a=open(sys.argv[2],'rb').read(); assert len(b)<=8192; open(sys.argv[3],'wb').write(b+b'\xff'*(8192-len(b))+a)" $(BOOT) $(TARGET).bin $@

$(FULL).hex: $(FULL).bin
	$(RUN) arm-none-eabi-objcopy -I binary -O ihex --change-addresses 0x08000000 $< $@

bootloader:
	$(MAKE) -C bootloader

flash-full: $(FULL).bin
	st-flash --reset write $< 0x08000000

flash: $(TARGET).bin
	st-flash --reset write $< 0x08002000

# USB-C only. If the test firmware's console is there, it is told to reboot into the bootloader;
# otherwise double-tap RESET first (green LED solid on). dfu-util waits for the bootloader to appear.
# CONSOLE= picks the board when several are connected (or names the port where by-id doesn't exist).
# The bootloader has the same USB serial as the console, so dfu-util -S then flashes only that board.
# dfu-util 0.11 exits 251 (LIBUSB_ERROR_NOT_FOUND) after "Done!" because the board restarts when -R resets
# it; that is the expected ending, so it counts as success. fwupd (Linux desktops) briefly claims every new
# DFU device, so dfu-util can lose the race with "Cannot claim interface - LIBUSB_ERROR_BUSY"; the board
# stays in the bootloader then, so try again.
dfu: $(TARGET).dfu
	@sn=$$(python3 enter_dfu.py $(CONSOLE)) || exit 1; \
	  for try in 1 2 3; do \
	    dfu-util -w -R -d 1209:db42 $${sn:+-S $$sn} -a 0 -D $<; rc=$$?; \
	    if [ $$rc -eq 0 ] || [ $$rc -eq 251 ]; then echo "flashed: the board is restarting into the new firmware"; exit 0; fi; \
	    echo "dfu-util failed ($$rc), trying again"; sleep 1; \
	  done; exit $$rc

# USART1 ROM bootloader (hold BOOT, tap RESET, release BOOT), 3.3 V USB-serial on J3.3 (TX) / J3.4 (RX)
PORT ?= /dev/ttyUSB0
flash-uart: $(FULL).bin
	stm32flash -w $< -v -g 0x08000000 $(PORT)

# refresh prebuilt/ from this build (commit the result)
prebuilt: all
	cp $(BOOT) prebuilt/nicklink-bootloader.bin
	cp $(TARGET).dfu prebuilt/nicklink-test.dfu
	cp $(FULL).hex prebuilt/nicklink-full.hex

clean:
	rm -rf build

.PHONY: all bootloader flash flash-full dfu flash-uart prebuilt clean
