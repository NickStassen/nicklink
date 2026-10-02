# NickLink v1.3 board-test firmware.
# Uses a host arm-none-eabi-gcc if there is one, else (or with DOCKER=1) the compiler in docker (./Dockerfile).
TARGET := build/nicklink-test

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

all: $(TARGET).bin

build/.image: Dockerfile
	@mkdir -p build
	docker build -q -t nicklink-fw-build . >/dev/null && touch $@

build/pins.h: gen_pins.py ../tools/spec.py
	@mkdir -p build
	python3 gen_pins.py > $@.tmp && mv $@.tmp $@

$(TARGET).elf: $(SRCS) src/regs.h build/pins.h stm32f103c8.ld | $(IMAGE)
	$(RUN) arm-none-eabi-gcc $(CFLAGS) $(SRCS) $(LDFLAGS) -o $@
	$(RUN) arm-none-eabi-size $@

$(TARGET).bin: $(TARGET).elf
	$(RUN) arm-none-eabi-objcopy -O binary $< $@

# SWD via ST-Link on J3 (3V3, GND, SWDIO, SWCLK, RST). Needs stlink-tools on the host.
flash: $(TARGET).bin
	st-flash --reset write $< 0x08000000

# USART1 ROM bootloader: hold BOOT, tap RESET, release BOOT. 3.3 V USB-serial on J3.3 (TX) / J3.4 (RX).
PORT ?= /dev/ttyUSB0
flash-uart: $(TARGET).bin
	stm32flash -w $< -v -g 0x08000000 $(PORT)

clean:
	rm -rf build

.PHONY: all flash flash-uart clean
