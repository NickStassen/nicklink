/* NickLink v1.3 target for dapboot (USB DFU bootloader in the first 8 KiB of flash).
 * Based on dapboot's bluepill config: 8 MHz HSE, LED on PC13, D+ pull-up hard-wired (R2/R11 from VBUS),
 * so the bootloader re-enumerates by driving PA12 low.
 *
 * Ways in:
 *   - double-tap RESET (second press within ~0.4 s; the green LED is on during the window)
 *   - the app writes 0x4F42 to BKP_DR1 and resets (test firmware: `dfu` command)
 *   - J1.9 (PB2, BOOT1, 10k pull-down) held at 3V3 during reset
 *   - no valid app at 0x08002000
 * In DFU mode the green LED is solid on. USB ID 1209:db42 (dapboot). */
#ifndef CONFIG_H_INCLUDED
#define CONFIG_H_INCLUDED

#define APP_BASE_ADDRESS (0x08000000 + BOOTLOADER_OFFSET)
/* No FLASH_SIZE_OVERRIDE: only the flash the chip reports (64 KiB on NickLink's F103C8) is writable. */
#define FLASH_PAGE_SIZE  1024
#define DFU_UPLOAD_AVAILABLE 1
#define DFU_DOWNLOAD_AVAILABLE 1
#define DFU_WILL_DETACH 0           /* manifestation tolerant: report success, then restart on dfu-util -R */

#define HAVE_LED 1
#define LED_OPEN_DRAIN 1             /* D3 from 3V3 into PC13 through R6: low = on */
#define LED_GPIO_PORT GPIOC
#define LED_GPIO_PIN GPIO13

#define HAVE_BUTTON 1                /* J1.9 / PB2 (BOOT1) to 3V3 at reset */
#define BUTTON_ACTIVE_HIGH 1
#define BUTTON_GPIO_PORT GPIOB
#define BUTTON_GPIO_PIN GPIO2
#define BUTTON_USES_PULL 0           /* R8 10k pull-down on the board */
#define BUTTON_SAMPLE_DELAY_CYCLES 1440000

#define HAVE_USB_PULLUP_CONTROL 0
#define USES_GPIOA 1
#define USES_GPIOB 1
#define USES_GPIOC 1

/* NickLink additions (target_nicklink.c, hooked in by nicklink.patch) */
#define HAVE_DOUBLE_TAP 1
#define DOUBLE_TAP_REG BKP2          /* BKP_DR2 at 0x40006C08; dapboot's own command word is BKP_DR1 */
#define DOUBLE_TAP_MAGIC 0x4454      /* "DT" */
#define DOUBLE_TAP_WINDOW_LOOPS 7200000u  /* ~0.4 s at 72 MHz (4-cycle loop) */
#define TARGET_CUSTOM_CLOCK 1        /* HSE with timeout, else HSI 48 MHz, so a dead crystal still boots the app */
#define HSE_TIMEOUT_LOOPS 1000000u   /* HSE normally starts in ~2 ms; this is ~0.1 s at 8 MHz */
#define TARGET_CUSTOM_SERIAL 1       /* USB serial = the test firmware's UID string */

#define USB_VENDOR_STRING "NickLink"
#define USB_PRODUCT_STRING "NickLink DFU bootloader"
#define USB_INTERFACE_STRING "NickLink application (0x08002000)"

#endif
