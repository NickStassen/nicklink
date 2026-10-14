# NickLink USB DFU bootloader: dapboot (https://github.com/devanlai/dapboot, ISC licence) with a NickLink
# target. dapboot and its libopencm3 are fetched at a pinned commit on the first build (needs git, network
# once, arm-none-eabi-gcc and python3 on the host); only the NickLink files live in this repo, and
# ../prebuilt/nicklink-bootloader.bin is the committed result.
DAPBOOT_URL := https://github.com/devanlai/dapboot.git
DAPBOOT_REV := 8a1f099f6e43ce292eee3a326bd810b7e55f198f
SRC := ../build/dapboot
OUT := ../build/nicklink-bootloader

all: $(OUT).bin

$(SRC)/.fetched: nicklink.patch
	rm -rf $(SRC)
	git clone -q $(DAPBOOT_URL) $(SRC)
	git -C $(SRC) checkout -q $(DAPBOOT_REV)
	git -C $(SRC) submodule update -q --init libopencm3
	git -C $(SRC) apply $(CURDIR)/nicklink.patch
	touch $@

$(OUT).bin: $(SRC)/.fetched $(wildcard nicklink/*)
	rm -rf $(SRC)/src/stm32f103/nicklink
	cp -r nicklink $(SRC)/src/stm32f103/
	$(MAKE) -C $(SRC)/src clean >/dev/null
	$(MAKE) -C $(SRC)/src TARGET=NICKLINK
	cp $(SRC)/src/dapboot.elf $(OUT).elf
	cp $(SRC)/src/dapboot.bin $(OUT).bin
	arm-none-eabi-size $(OUT).elf
	@test $$(stat -c %s $(OUT).bin) -le 8192 || { echo "bootloader is over 8 KiB"; exit 1; }

clean:
	rm -rf $(SRC) $(OUT).elf $(OUT).bin

.PHONY: all clean
