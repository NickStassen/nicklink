/* NickLink-specific dapboot hooks: double-tap RESET, LED states, crystal fallback, USB serial. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/gpio.h>

#include "target.h"
#include "config.h"
#include "backup.h"

bool target_double_tap(bool force);

static void spin(uint32_t n) {  /* ~4 cycles per loop; only needs to be roughly right */
    __asm__ volatile("1: subs %0, #1\n\tbne 1b" : "+r"(n));
}

static void led(bool on) {  /* active low */
    if (on) gpio_clear(LED_GPIO_PORT, LED_GPIO_PIN); else gpio_set(LED_GPIO_PORT, LED_GPIO_PIN);
}

/* Called from target_get_force_bootloader() with what dapboot already decided (magic word / PB2). */
bool target_double_tap(bool force) {
    if (force || backup_read(DOUBLE_TAP_REG) == DOUBLE_TAP_MAGIC) {
        backup_write(DOUBLE_TAP_REG, 0);
        return true;
    }
    /* Arm, then give a second RESET press ~0.4 s to land. Backup registers survive NRST (VBAT is tied
     * to 3V3) but not a power cycle, so the first boot after power-up never enters DFU by accident. */
    backup_write(DOUBLE_TAP_REG, DOUBLE_TAP_MAGIC);
    led(true);
    spin(DOUBLE_TAP_WINDOW_LOOPS);
    led(false);
    backup_write(DOUBLE_TAP_REG, 0);
    return false;
}

void target_clock_setup(void) {
    /* Stock dapboot waits forever for the crystal. On a bring-up board a dead crystal must not hide
     * everything else, so give HSE ~0.1 s and fall back to HSI 48 MHz (out of USB spec, but the app
     * still starts and reports the failure). */
    rcc_osc_on(RCC_HSE);
    uint32_t n = HSE_TIMEOUT_LOOPS;
    while (!rcc_is_osc_ready(RCC_HSE) && --n) {}
    if (n) {
        rcc_clock_setup_pll(&rcc_hse_configs[RCC_CLOCK_HSE8_72MHZ]);
    } else {
        rcc_osc_off(RCC_HSE);
        rcc_clock_setup_pll(&rcc_hsi_configs[RCC_CLOCK_HSI_48MHZ]);
    }
}

/* The same serial as the test firmware's console and banner (UID words 2, 1, 0 in hex), so one board
 * has one serial in both modes and `dfu-util -S` can pick it out by its console's name. */
void target_get_serial_number(char* dest, size_t max_chars) {
    const volatile uint32_t *uid = (const volatile uint32_t *)0x1FFFF7E8;
    size_t n = 0;
    for (int w = 2; w >= 0; w--)
        for (int i = 28; i >= 0 && n < max_chars; i -= 4) dest[n++] = "0123456789ABCDEF"[(uid[w] >> i) & 0xF];
    dest[n] = '\0';
}

void target_post_setup(void) {
    led(true);  /* DFU mode: solid on (the test firmware blinks at 1 Hz) */
}

void target_pre_detach(bool manifested) {
    (void)manifested;
    led(false);
}
