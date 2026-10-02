/* Minimal Cortex-M3 startup for STM32F103: vector table, .data/.bss init. */
#include <stdint.h>
#include "regs.h"
extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;
int main(void);
void NMI_Handler(void), SysTick_Handler(void), USART1_IRQHandler(void), EXTI0_IRQHandler(void);

void Reset_Handler(void) {
    SCB_VTOR = 0x08000000;  /* a bootloader GO (stm32flash -g) leaves VTOR at the ROM; fix before any interrupt */
    for (uint32_t *s = &_sidata, *d = &_sdata; d < &_edata;) *d++ = *s++;
    for (uint32_t *d = &_sbss; d < &_ebss;) *d++ = 0;
    main();
    for (;;) {}
}

void Fault_Handler(void) {  /* HardFault/MemManage/BusFault/UsageFault: LED solid on, spin */
    *(volatile uint32_t *)0x40011014 = 1u << 13;  /* GPIOC_BRR: PC13 low = LED on */
    for (;;) {}
}

__attribute__((section(".vectors"), used))
static void (*const vectors[16 + 38])(void) = {
    [0] = (void (*)(void))&_estack, [1] = Reset_Handler,
    [2] = NMI_Handler,                       /* clock security system */
    [3 ... 6] = Fault_Handler,               /* HardFault, MemManage, BusFault, UsageFault */
    [15] = SysTick_Handler,
    [16 + 6] = EXTI0_IRQHandler,
    [16 + 37] = USART1_IRQHandler,
};

/* newlib syscall stubs (console output is _write in main.c) */
extern char end;
void *_sbrk(int n) { static char *brk = &end; char *p = brk; brk += n; return p; }
int _close(int f) { (void)f; return -1; }
int _fstat(int f, void *st) { (void)f; (void)st; return -1; }
int _isatty(int f) { (void)f; return 1; }
int _lseek(int f, int o, int w) { (void)f; (void)o; (void)w; return -1; }
int _read(int f, char *p, int n) { (void)f; (void)p; (void)n; return 0; }
int _kill(int p, int s) { (void)p; (void)s; return -1; }
int _getpid(void) { return 1; }
void _exit(int s) { (void)s; for (;;) {} }
