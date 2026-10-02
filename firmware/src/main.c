/* NickLink v1.3 board-test firmware (STM32F103C8, bare metal).
 * USART1 console on PA9/PA10 at 115200 8N1. Type `help`. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "regs.h"
#include "pins.h"

/* Tap/wake tuning knobs (LSM6DSV units, same as LSM6DSV16X: tap 1 LSB = FS/32 = 62.5 mg at +-2 g, wake 1 LSB = 7.8 mg) */
#define TAP_THS  8      /* 0.5 g */
#define WAKE_THS 32     /* 0.25 g */
#define TAP_DUR  0x7A   /* DUR=7 (double-tap window), QUIET=2, SHOCK=2 */

#define IMU_ADDR 0x6A
enum { IN_ANALOG = 0x0, IN_FLOAT = 0x4, IN_PULL = 0x8, OUT_PP = 0x2, OUT_OD = 0x6, AF_PP = 0xB, AF_OD = 0xF };

static volatile uint32_t ticks;          /* ms since boot */
static volatile int led_auto = 1;
static volatile uint8_t rxbuf[64];
static volatile uint8_t rx_head, rx_tail;
static volatile int int1_pending;
static volatile uint32_t sysclk = 8000000;
static const char *volatile clock_msg = "HSI 8 MHz";
static uint32_t reset_csr;
static int imu_ok;
static int standby_wake;

/* ---- basics ----------------------------------------------------------- */
void SysTick_Handler(void) {
    ticks++;
    if (led_auto && ticks % 500 == 0) GPIO_ODR(PC) ^= 1u << 13;
}

static void delay_ms(uint32_t ms) { uint32_t t0 = ticks; while (ticks - t0 < ms) {} }

static void pin_mode(int port, int pin, int mode) {
    volatile uint32_t *cr = pin < 8 ? &GPIO_CRL(port) : &GPIO_CRH(port);
    int sh = (pin & 7) * 4;
    *cr = (*cr & ~(0xFu << sh)) | ((uint32_t)mode << sh);
}
static void pin_set(int port, int pin, int v) { if (v) GPIO_BSRR(port) = 1u << pin; else GPIO_BRR(port) = 1u << pin; }
static int pin_get(int port, int pin) { return (GPIO_IDR(port) >> pin) & 1; }

/* bounded wait: true if cond came true within ~100 ms of HSI-speed loops */
#define WAIT(cond) ({ uint32_t n_ = 200000; while (!(cond) && --n_) {} n_ != 0; })
#define CR_HSION (1u << 0)
#define CR_HSIRDY (1u << 1)
#define CR_HSEON (1u << 16)
#define CR_HSERDY (1u << 17)
#define CR_CSSON (1u << 19)
#define CR_PLLON (1u << 24)
#define CR_PLLRDY (1u << 25)
#define SWS() ((RCC_CFGR >> 2) & 3)

/* Clock security system: if the crystal dies, hardware switches SYSCLK to HSI and raises NMI.
 * Keep running on HSI 8 MHz and record it; `info` reports it. */
void NMI_Handler(void) {
    if (!(RCC_CIR & (1u << 7))) return;                         /* CSSF */
    RCC_CIR |= 1u << 23;                                        /* CSSC: clear it, or NMI fires forever */
    sysclk = 8000000;
    SYST_RVR = sysclk / 1000 - 1; SYST_CVR = 0;
    USART1_BRR = (sysclk + 57600) / 115200;
    clock_msg = "HSE FAILED at runtime (CSS) -> running on HSI 8 MHz";
}

static void clock_init(void) {
    /* don't assume a fresh reset (bootloader GO, soft reset): HSI as SYSCLK, PLL/CSS/HSE off */
    RCC_CR |= CR_HSION;
    WAIT(RCC_CR & CR_HSIRDY);
    RCC_CFGR &= ~3u;
    WAIT(SWS() == 0);
    RCC_CR &= ~(CR_CSSON | CR_PLLON);
    RCC_CIR |= 1u << 23;
    WAIT(!(RCC_CR & CR_PLLRDY));
    RCC_CR &= ~CR_HSEON;
    RCC_CR |= CR_HSEON;
    int hse = WAIT(RCC_CR & CR_HSERDY);                         /* ~100 ms on HSI */
    FLASH_ACR = 0x12;                                           /* prefetch, 2 wait states */
    /* APB1 /2, ADC /6 (12 MHz, max 14), USBPRE=0 (/1.5) */
    if (hse) { RCC_CR |= CR_CSSON; RCC_CFGR = (7u << 18) | (1u << 16) | (4u << 8) | (2u << 14); }  /* PLL = HSE x9 = 72 MHz */
    else { RCC_CR &= ~CR_HSEON; RCC_CFGR = (14u << 18) | (4u << 8) | (2u << 14); }  /* PLL = HSI/2 x16 = 64 MHz */
    RCC_CR |= CR_PLLON;
    if (!WAIT(RCC_CR & CR_PLLRDY)) { clock_msg = "PLL did not lock, staying on HSI 8 MHz"; return; }
    RCC_CFGR |= 2;                                              /* SW = PLL */
    if (!WAIT(SWS() == 2)) { clock_msg = "switch to PLL failed (SWS), staying on HSI 8 MHz"; return; }
    sysclk = hse ? 72000000 : 64000000;
    clock_msg = hse ? "HSE 8 MHz -> PLL x9 = 72 MHz (APB1 36 MHz, ADC 12 MHz, USB 48 MHz), CSS on"
                    : "HSE FAILED to start -> HSI/2 x16 = 64 MHz (USB unusable)";
}

/* ---- console ---------------------------------------------------------- */
void USART1_IRQHandler(void) {
    if (USART1_SR & (1u << 5)) {                                /* RXNE */
        uint8_t c = USART1_DR, n = (rx_head + 1) % sizeof rxbuf;
        if (n != rx_tail) { rxbuf[rx_head] = c; rx_head = n; }
    }
}
static int getch(void) {
    if (rx_head == rx_tail) return -1;
    int c = rxbuf[rx_tail]; rx_tail = (rx_tail + 1) % sizeof rxbuf; return c;
}
static void putch(char c) { while (!(USART1_SR & (1u << 7))) {} USART1_DR = c; }
int _write(int fd, const char *p, int n) {
    (void)fd;
    for (int i = 0; i < n; i++) { if (p[i] == '\n') putch('\r'); putch(p[i]); }
    return n;
}
static void uart_init(void) {
    pin_mode(PA, 9, AF_PP);
    pin_mode(PA, 10, IN_PULL); pin_set(PA, 10, 1);             /* pull-up: idle-high if nothing is connected */
    USART1_BRR = (sysclk + 57600) / 115200;
    USART1_CR1 = (1u << 13) | (1u << 5) | (1u << 3) | (1u << 2); /* UE RXNEIE TE RE */
    NVIC_ISER1 = 1u << (37 - 32);
}

/* ---- I2C1 (polled) ---------------------------------------------------- */
#define SR1_SB 0x1
#define SR1_ADDR 0x2
#define SR1_BTF 0x4
#define SR1_RXNE 0x40
#define SR1_TXE 0x80
#define SR1_AF 0x400
#define CR1_START 0x100
#define CR1_STOP 0x200
#define CR1_ACK 0x400

static int i2c_wait(uint32_t flag) {
    uint32_t t0 = ticks;
    while (!(I2C1_SR1 & flag)) {
        if (I2C1_SR1 & SR1_AF) { I2C1_SR1 = ~SR1_AF; return -1; }  /* NACK */
        if (ticks - t0 > 10) return -2;
    }
    return 0;
}
static int i2c_start(uint8_t addr8) {
    I2C1_CR1 |= CR1_START;
    if (i2c_wait(SR1_SB)) return -2;
    I2C1_DR = addr8;
    return i2c_wait(SR1_ADDR);
}
static int i2c_fail(int e) { I2C1_CR1 |= CR1_STOP; return e; }

static int i2c_write(uint8_t addr, uint8_t reg, const uint8_t *buf, int n) {
    int e;
    if ((e = i2c_start(addr << 1))) return i2c_fail(e);
    (void)I2C1_SR2;
    I2C1_DR = reg;
    for (int i = 0; i < n; i++) { if ((e = i2c_wait(SR1_TXE))) return i2c_fail(e); I2C1_DR = buf[i]; }
    if ((e = i2c_wait(SR1_BTF))) return i2c_fail(e);
    I2C1_CR1 |= CR1_STOP;
    return 0;
}
/* ponytail: NACK/STOP is set after the second-to-last byte (not RM0008's exact N=2/N=3 dance); fine while
 * no ISR stalls > ~80 us at 100 kHz. Move to DMA or the RM sequence if longer ISRs appear. */
static int i2c_read(uint8_t addr, uint8_t reg, uint8_t *buf, int n) {
    int e;
    if ((e = i2c_start(addr << 1))) return i2c_fail(e);
    (void)I2C1_SR2;
    I2C1_DR = reg;
    if ((e = i2c_wait(SR1_BTF))) return i2c_fail(e);
    if ((e = i2c_start((addr << 1) | 1))) return i2c_fail(e);
    if (n == 1) I2C1_CR1 &= ~CR1_ACK; else I2C1_CR1 |= CR1_ACK;
    (void)I2C1_SR2;
    if (n == 1) I2C1_CR1 |= CR1_STOP;
    for (int i = 0; i < n; i++) {
        if ((e = i2c_wait(SR1_RXNE))) return i2c_fail(e);
        buf[i] = I2C1_DR;
        if (i == n - 2) { I2C1_CR1 &= ~CR1_ACK; I2C1_CR1 |= CR1_STOP; }
    }
    return 0;
}
static int i2c_probe(uint8_t addr) {
    int e = i2c_start(addr << 1);
    (void)I2C1_SR2;
    I2C1_CR1 |= CR1_STOP;
    return e == 0;
}
static void i2c_init(void) {
    RCC_APB1ENR |= 1u << 21;
    /* bus recovery (F103 BUSY lock-up after a reset mid-transfer): clock SCL until the slave lets SDA go */
    pin_set(PB, 6, 1); pin_set(PB, 7, 1);
    pin_mode(PB, 6, OUT_OD); pin_mode(PB, 7, OUT_OD);
    for (int i = 0; i < 9 && !pin_get(PB, 7); i++) {
        pin_set(PB, 6, 0); delay_ms(1); pin_set(PB, 6, 1); delay_ms(1);
    }
    pin_set(PB, 7, 0); delay_ms(1); pin_set(PB, 7, 1);         /* STOP */
    pin_mode(PB, 6, AF_OD); pin_mode(PB, 7, AF_OD);
    I2C1_CR1 = 0x8000; I2C1_CR1 = 0;                            /* SWRST */
    uint32_t pclk1 = sysclk / 2, mhz = pclk1 / 1000000;
    I2C1_CR2 = mhz;
    I2C1_CCR = pclk1 / (2 * 100000);                            /* 100 kHz standard mode */
    I2C1_TRISE = mhz + 1;
    I2C1_CR1 = 1;                                               /* PE */
}

/* ---- IMU -------------------------------------------------------------- */
static int imu_wr(uint8_t reg, uint8_t v) { return i2c_write(IMU_ADDR, reg, &v, 1); }
static int imu_rd(uint8_t reg) { uint8_t v; return i2c_read(IMU_ADDR, reg, &v, 1) ? -1 : v; }

void EXTI0_IRQHandler(void) { EXTI_PR = 1; int1_pending++; }

static int imu_init(void) {
    int who = imu_rd(0x0F);
    if (who < 0) { printf("IMU: no ACK at 0x%02X on I2C1 (PB6/PB7)\n", IMU_ADDR); return 0; }
    printf("IMU: WHO_AM_I = 0x%02X %s\n", who, who == 0x70 ? "OK (LSM6DSV family)" : "UNEXPECTED (want 0x70)");
    if (who != 0x70) return 0;
    imu_wr(0x12, 0x01);                                         /* CTRL3 SW_RESET */
    for (uint32_t t0 = ticks; (imu_rd(0x12) & 1) && ticks - t0 < 20;) {}
    int ifcfg = imu_rd(0x03);                                   /* IF_CFG isn't reset by SW_RESET */
    static const uint8_t cfg[][2] = {
        {0x12, 0x44},              /* CTRL3: BDU, IF_INC */
        {0x10, 0x08},              /* CTRL1: accel 480 Hz high-performance (tap wants >= 400 Hz) */
        {0x11, 0x06},              /* CTRL2: gyro 120 Hz */
        {0x15, 0x04},              /* CTRL6: +-2000 dps */
        {0x17, 0x00},              /* CTRL8: +-2 g */
        {0x56, 0x0F},              /* TAP_CFG0: tap X/Y/Z, latched (LIR) */
        {0x57, TAP_THS}, {0x58, TAP_THS}, {0x59, TAP_THS},  /* TAP_CFG1/2, TAP_THS_6D: thresholds */
        {0x5A, TAP_DUR},
        {0x5B, 0x80 | WAKE_THS},   /* WAKE_UP_THS: single+double tap, wake threshold */
        {0x5C, 0x00},              /* WAKE_UP_DUR */
        {0x50, 0x80},              /* FUNCTIONS_ENABLE: INTERRUPTS_ENABLE */
        {0x5E, 0x68},              /* MD1_CFG: INT1 <- single tap | wake-up | double tap */
    };
    int err = ifcfg < 0 || imu_wr(0x03, ifcfg & ~0x18);         /* INT1 push-pull (PP_OD=0), active high */
    for (unsigned i = 0; i < sizeof cfg / sizeof cfg[0]; i++) err |= imu_wr(cfg[i][0], cfg[i][1]);
    if (err || imu_rd(0x5E) != 0x68) { printf("IMU: config write/readback FAILED\n"); return 0; }
    (void)imu_rd(0x1D);                                         /* ALL_INT_SRC: clear any latched event */
    pin_mode(PA, 0, IN_PULL); pin_set(PA, 0, 0);                /* PA0 pull-down: defined even without the IMU */
    AFIO_EXTICR1 &= ~0xFu;                                      /* EXTI0 <- PA0 */
    EXTI_RTSR |= 1; EXTI_PR = 1; EXTI_IMR |= 1;
    NVIC_ISER0 = 1u << 6;
    printf("IMU: 480 Hz, +-2 g, +-2000 dps; tap/double-tap/wake-up -> INT1 -> PA0 (EXTI0 rising)\n");
    return 1;
}

static void imu_sample(void) {
    uint8_t b[14];
    if (!imu_ok || i2c_read(IMU_ADDR, 0x20, b, 14)) { printf("IMU: not available\n"); return; }
    int16_t v[7];
    for (int i = 0; i < 7; i++) v[i] = (int16_t)(b[2 * i] | b[2 * i + 1] << 8);
    int t10 = 250 + v[0] * 10 / 256;                            /* 256 LSB/C, 0 = 25 C */
    printf("IMU: acc mg %d %d %d  gyro dps %d %d %d  temp %s%d.%d C  (raw acc %d %d %d)\n",
           v[4] * 61 / 1000, v[5] * 61 / 1000, v[6] * 61 / 1000,
           v[1] * 70 / 1000, v[2] * 70 / 1000, v[3] * 70 / 1000,
           t10 < 0 ? "-" : "", abs(t10) / 10, abs(t10) % 10, v[4], v[5], v[6]);
}

static void imu_event(void) {
    uint8_t src[2];                                             /* WAKE_UP_SRC, TAP_SRC */
    int ok = !i2c_read(IMU_ADDR, 0x45, src, 2);
    (void)imu_rd(0x1D);                                         /* ALL_INT_SRC read releases the latch */
    if (!ok) { printf("int1 (I2C read failed)\n"); return; }
    if (src[1] & 0x20) printf("tap\n");
    if (src[1] & 0x10) printf("double-tap\n");
    if (src[0] & 0x08) printf("wake\n");
    if (!(src[1] & 0x30) && !(src[0] & 0x08)) printf("int1 (no source: WU 0x%02X TAP 0x%02X)\n", src[0], src[1]);
}

/* ---- board info ------------------------------------------------------- */
static void print_info(void) {
    printf("\nNickLink v" BOARD_REV " board test, SYSCLK %lu Hz\n", (unsigned long)sysclk);
    printf("clock: %s\n", clock_msg);
    printf("RCC_CFGR 0x%08lX, PVD 2.9 V: VDD %s, %s\n", (unsigned long)RCC_CFGR,
           PWR_CSR & (1u << 2) ? "BELOW threshold" : "ok", standby_wake ? "woke from Standby" : "not from Standby");
    uint32_t c = reset_csr;
    printf("reset cause:%s%s%s%s%s%s (RCC_CSR 0x%08lX)\n",
           c & (1u << 27) ? " power-on" : "", c & (1u << 28) ? " software" : "",
           c & (1u << 29) ? " IWDG" : "", c & (1u << 30) ? " WWDG" : "", c & (1u << 31) ? " low-power" : "",
           (c & (0x3Fu << 26)) == (1u << 26) ? " NRST pin (RESET button)" : "", (unsigned long)c);
    /* BOOT0 isn't a GPIO; infer it from what is aliased at 0x0 (flash only when BOOT0 was low at reset) */
    int flash_alias = R32(0x00000004) == R32(0x08000004);
    printf("boot: %s; BOOT1/PB2 reads %d (10k pull-down, want 0)\n",
           flash_alias ? "flash aliased at 0x0 (BOOT0 was low)" : "0x0 is NOT flash (BOOT0 high / started by bootloader)",
           pin_get(PB, 2));
    printf("flash size reg %u KB, UID %08lX%08lX%08lX\n", FLASH_SIZE_KB,
           (unsigned long)UID(2), (unsigned long)UID(1), (unsigned long)UID(0));
}

static void print_pins(void) {
    printf("LQFP  func   net      header  function / on-board load\n");
    for (unsigned i = 0; i < N_MCU_PINS; i++) {
        const mcu_pin_t *p = &MCU_PINS[i];
        printf("%4u  %-5s  %-7s  %-6s  %s%s%s\n", p->lqfp, p->fn, p->net, p->hdr, p->alias,
               *p->alias && *p->loads ? "; " : "", p->loads);
    }
}

/* ---- GPIO walk / monitor ---------------------------------------------- */
static int skip_pin(const hdr_pin_t *h, int all) {
    if (h->port == PA && (h->pin == 9 || h->pin == 10)) return 1;           /* console */
    return !all && h->port == PA && (h->pin == 13 || h->pin == 14);         /* SWD */
}
static void pins_release(void) {  /* back to normal use after walk/mon */
    for (unsigned i = 0; i < N_HDR_PINS; i++)
        if (!skip_pin(&HDR_PINS[i], 1)) pin_mode(HDR_PINS[i].port, HDR_PINS[i].pin, IN_FLOAT);
    AFIO_MAPR = (AFIO_MAPR & ~(7u << 24)) | (2u << 24);       /* SWD on, JTAG off (frees PA15/PB3/PB4) */
    pin_mode(PC, 13, OUT_PP); led_auto = 1;
    i2c_init(); imu_ok = imu_init();
}
static void pins_pulldown(int all) {
    led_auto = 0; EXTI_IMR &= ~1u;
    if (all) AFIO_MAPR = (AFIO_MAPR & ~(7u << 24)) | (4u << 24);  /* SWD off too: SWD is lost until reset */
    for (unsigned i = 0; i < N_HDR_PINS; i++) {
        const hdr_pin_t *h = &HDR_PINS[i];
        if (!skip_pin(h, all)) { pin_set(h->port, h->pin, 0); pin_mode(h->port, h->pin, IN_PULL); }
    }
}

/* Drive each header GPIO high then low (one at a time, others pulled down) and check that it reads back,
 * and that no other header pin follows it (solder bridge). Probe each pin with a meter/LED as it walks. */
static void cmd_walk(uint32_t ms, int all) {
    int faults = 0, n = 0;
    pins_pulldown(all);
    printf("walk: %lu ms per level%s; any key aborts\n", (unsigned long)ms, all ? ", SWD pins included" : "");
    for (unsigned i = 0; i < N_HDR_PINS && getch() < 0; i++) {
        const hdr_pin_t *h = &HDR_PINS[i];
        if (skip_pin(h, all)) continue;
        uint32_t idr[2][3];
        pin_mode(h->port, h->pin, OUT_PP);
        for (int lvl = 1; lvl >= 0; lvl--) {
            pin_set(h->port, h->pin, lvl);
            printf("WALK %s %s %s\n", h->hdr, h->name, lvl ? "high" : "low");
            delay_ms(ms);
            for (int p = 0; p < 3; p++) idr[lvl][p] = GPIO_IDR(p);
        }
        pin_mode(h->port, h->pin, IN_PULL);
        n++;
        int hi = idr[1][h->port] >> h->pin & 1, lo = idr[0][h->port] >> h->pin & 1;
        if (!hi) { printf("  FAIL %s reads 0 while driven high (short to GND?)\n", h->name); faults++; }
        if (lo) { printf("  FAIL %s reads 1 while driven low (short to 3V3?)\n", h->name); faults++; }
        for (unsigned j = 0; j < N_HDR_PINS; j++) {
            const hdr_pin_t *o = &HDR_PINS[j];
            if (j == i || skip_pin(o, all)) continue;
            if ((idr[1][o->port] >> o->pin & 1) && !(idr[0][o->port] >> o->pin & 1)) {
                printf("  FAIL %s follows %s (short?)\n", o->name, h->name); faults++;
            }
        }
    }
    printf("walk done: %d pins, %d faults\n", n, faults);
    pins_release();
}

/* Loopback/monitor: all header GPIOs as pulled-down inputs; print every level change. */
static void cmd_mon(void) {
    pins_pulldown(0);
    printf("mon: inputs with pull-down, printing changes; any key exits\n");
    uint32_t last[3] = {0}, cur[3];
    for (int first = 1; getch() < 0; first = 0) {
        for (int p = 0; p < 3; p++) cur[p] = GPIO_IDR(p);
        for (unsigned i = 0; i < N_HDR_PINS; i++) {
            const hdr_pin_t *h = &HDR_PINS[i];
            int v = cur[h->port] >> h->pin & 1;
            if (!skip_pin(h, 0) && (first ? v : v != (int)(last[h->port] >> h->pin & 1)))
                printf("mon: %s %s=%d\n", h->hdr, h->name, v);
        }
        memcpy(last, cur, sizeof last);
        delay_ms(5);
    }
    printf("mon done\n");
    pins_release();
}

/* ---- Standby / ADC ---------------------------------------------------- */
/* Standby, wake on a rising edge at PA0/WKUP (A0). The IMU INT1 (push-pull, idles low) drives A0
 * through 10k, so a tap/wake event wakes the MCU. Wake = reset; the banner reports it. */
static void cmd_standby(void) {
    (void)imu_rd(0x1D);                                         /* ALL_INT_SRC: release latched INT1 so it is low */
    pin_mode(PA, 0, IN_FLOAT);                                  /* A0 already has 10k to INT1; no internal pull */
    if (pin_get(PA, 0)) printf("warning: PA0 is high, a rising edge is needed to wake\n");
    printf("entering Standby; rising edge on PA0 (or RESET) wakes\n");
    while (!(USART1_SR & (1u << 6))) {}                         /* TC: let the text out */
    SYST_CSR = 0; USART1_CR1 &= ~(1u << 5); EXTI_IMR &= ~1u;    /* no pending interrupt may cancel WFI */
    PWR_CR |= (1u << 2) | (1u << 1);                            /* CWUF, PDDS */
    PWR_CSR |= 1u << 8;                                         /* EWUP */
    SCB_SCR |= 1u << 2;                                         /* SLEEPDEEP */
    __asm volatile("wfi");
    SCB_AIRCR = 0x05FA0004;                                     /* WFI fell through (debugger?): reset */
}

/* ADC1 single conversions: PA0-PA7 = ch0-7, PB0/PB1 = ch8/9, VREFINT = ch17. ADC clock 12 MHz,
 * 239.5-cycle sample (~21 us, covers VREFINT's 17.1 us minimum). Pins are analog only while it runs. */
static int adc_read(int ch) {
    ADC1_SQR3 = (uint32_t)ch;
    ADC1_CR2 |= 1u << 22;                                       /* SWSTART */
    uint32_t t0 = ticks;
    while (!(ADC1_SR & 2)) if (ticks - t0 > 5) return -1;       /* EOC */
    return ADC1_DR & 0xFFF;                                     /* DR read clears EOC */
}
static void cmd_adc(void) {
    uint32_t cra = GPIO_CRL(PA), crb = GPIO_CRL(PB);
    RCC_APB2ENR |= 1u << 9;                                     /* ADC1EN */
    ADC1_SMPR1 = 0x00FFFFFF; ADC1_SMPR2 = 0x3FFFFFFF; ADC1_SQR1 = 0;
    ADC1_CR2 = 1u;                                              /* ADON */
    delay_ms(1);
    ADC1_CR2 = 1u | (7u << 17) | (1u << 20) | (1u << 23);       /* EXTSEL=SWSTART, EXTTRIG, TSVREFE */
    ADC1_CR2 |= 1u << 3; for (uint32_t t0 = ticks; (ADC1_CR2 & (1u << 3)) && ticks - t0 < 5;) {}   /* RSTCAL */
    ADC1_CR2 |= 1u << 2; for (uint32_t t0 = ticks; (ADC1_CR2 & (1u << 2)) && ticks - t0 < 5;) {}   /* CAL */
    delay_ms(1);                                                /* VREFINT start-up */
    GPIO_CRL(PA) = 0;                                           /* PA0-7 analog */
    GPIO_CRL(PB) = (crb & ~0xFFu);                              /* PB0/PB1 analog */
    int vref = adc_read(17);
    uint32_t vdda = vref > 0 ? 1200u * 4095u / (uint32_t)vref : 0;  /* VREFINT 1.20 V typ (1.16-1.24) */
    printf("VREFINT raw %d -> VDDA ~%lu mV\n", vref, (unsigned long)vdda);
    for (int ch = 0; ch < 10; ch++) {
        int v = adc_read(ch);
        if (v < 0) printf("%s%d ch%d: timeout\n", ch < 8 ? "PA" : "PB", ch < 8 ? ch : ch - 8, ch);
        else printf("%s%d ch%d: raw %4d = %4lu mV\n", ch < 8 ? "PA" : "PB", ch < 8 ? ch : ch - 8, ch,
                    v, (unsigned long)v * vdda / 4095);
    }
    GPIO_CRL(PA) = cra; GPIO_CRL(PB) = crb;
    ADC1_CR2 = 0; RCC_APB2ENR &= ~(1u << 9);
}

/* ---- command line ----------------------------------------------------- */
static void run(char *line) {
    char *cmd = strtok(line, " "), *arg = strtok(NULL, " ");
    if (!cmd) return;
    if (!strcmp(cmd, "help"))
        printf("info | pins | walk [ms] [all] | mon | imu | i2cscan | mco [hse|pll|hsi|off] | adc | standby | reset\n"
               "  walk: drive each header GPIO high then low, check readback + shorts (all = include SWD)\n"
               "  mon:  print header input changes (jumper a pin to 3V3 to test it)\n");
    else if (!strcmp(cmd, "info") || !strcmp(cmd, "clock")) print_info();
    else if (!strcmp(cmd, "pins")) print_pins();
    else if (!strcmp(cmd, "walk")) {
        int all = arg && !strcmp(arg, "all");
        char *a2 = all ? NULL : strtok(NULL, " ");
        uint32_t ms = arg && !all ? strtoul(arg, NULL, 0) : 500;
        cmd_walk(ms ? ms : 500, all || (a2 && !strcmp(a2, "all")));
    }
    else if (!strcmp(cmd, "mon")) cmd_mon();
    else if (!strcmp(cmd, "imu")) { if (!imu_ok) imu_ok = imu_init(); imu_sample(); }
    else if (!strcmp(cmd, "i2cscan")) {
        printf("I2C1:");
        for (int a = 0x08; a < 0x78; a++) if (i2c_probe(a)) printf(" 0x%02X", a);
        printf("\n");
    }
    else if (!strcmp(cmd, "mco")) {  /* clock out on PA8 (J3.5): check the crystal with a counter/scope */
        uint32_t src = !arg ? 6 : !strcmp(arg, "pll") ? 7 : !strcmp(arg, "hsi") ? 5 : !strcmp(arg, "off") ? 0 : 6;
        RCC_CFGR = (RCC_CFGR & ~(7u << 24)) | (src << 24);
        pin_mode(PA, 8, src ? AF_PP : IN_FLOAT);
        printf("MCO on PA8 (J3.5): %s\n", src == 6 ? "HSE, expect 8.000 MHz" : src == 7 ? "PLL/2, expect 36.000 MHz" : src == 5 ? "HSI 8 MHz" : "off");
    }
    else if (!strcmp(cmd, "adc")) cmd_adc();
    else if (!strcmp(cmd, "standby")) cmd_standby();
    else if (!strcmp(cmd, "reset")) { printf("resetting\n"); delay_ms(5); SCB_AIRCR = 0x05FA0004; }
    else printf("? %s (try help)\n", cmd);
}

/* No USB stack in this build: hold D+ low so the host sees "nothing attached" instead of a device
 * that never answers. A USB build must release PA12 (>= 10 ms after boot) to force re-enumeration. */
static void usb_detach(void) { pin_set(PA, 12, 0); pin_mode(PA, 12, OUT_OD); }

int main(void) {
    reset_csr = RCC_CSR;
    RCC_APB1ENR |= 1u << 28;                                    /* PWR clock */
    standby_wake = PWR_CSR & (1u << 1);                         /* SBF */
    PWR_CR |= (1u << 3) | (7u << 5) | (1u << 4);                /* CSBF, PLS=111 (2.9 V), PVDE; polled, no EXTI16 */
    RCC_CSR |= 1u << 24;                                        /* RMVF: clear reset flags for next time */
    clock_init();
    RCC_APB2ENR |= (1u << 0) | (1u << 2) | (1u << 3) | (1u << 4) | (1u << 14);  /* AFIO, GPIOA/B/C, USART1 */
    AFIO_MAPR = (AFIO_MAPR & ~(7u << 24)) | (2u << 24);       /* SWD only: frees PA15/PB3/PB4 as GPIO */
    SYST_RVR = sysclk / 1000 - 1; SYST_CVR = 0; SYST_CSR = 7;
    pin_mode(PC, 13, OUT_PP); pin_set(PC, 13, 1);              /* user LED off (active low) */
    usb_detach();
    uart_init();
    setvbuf(stdout, NULL, _IONBF, 0);
    print_info();
    i2c_init();
    imu_ok = imu_init();
    printf("type 'help'\n> ");

    char line[48];
    unsigned len = 0;
    for (;;) {
        if (int1_pending) { int1_pending = 0; imu_event(); }
        int c = getch();
        if (c < 0) continue;
        if (c == '\r' || c == '\n') {
            printf("\n"); line[len] = 0; run(line); len = 0; printf("> ");
        } else if ((c == 8 || c == 127) && len) { len--; printf("\b \b"); }
        else if (c >= ' ' && len < sizeof line - 1) { line[len++] = c; putch(c); }
    }
}
