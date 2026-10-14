/* STM32F103C8: 64 KiB flash, 20 KiB SRAM. The first 8 KiB hold the USB DFU bootloader (bootloader/),
 * which starts the app at 0x08002000. */
MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08002000, LENGTH = 56K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 20K
}
ENTRY(Reset_Handler)
_estack = ORIGIN(RAM) + LENGTH(RAM);
SECTIONS
{
  .text : {
    __vectors_start = .;
    KEEP(*(.vectors))
    *(.text*) *(.rodata*)
    . = ALIGN(4);
  } > FLASH
  .ARM.exidx : { *(.ARM.exidx*) } > FLASH
  _sidata = LOADADDR(.data);
  .data : { _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > RAM AT > FLASH
  .bss (NOLOAD) : { _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; } > RAM
  end = .;   /* newlib sbrk heap start */
}
