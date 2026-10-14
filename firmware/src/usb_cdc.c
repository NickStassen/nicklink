/* USB full-speed CDC ACM console for the STM32F103 USB peripheral (RM0008 ch. 23), bare metal.
 * One function, two interfaces: EP0 control, EP1 bulk OUT/IN (64 B), EP2 interrupt IN (notifications,
 * never sent). bInterfaceProtocol 0 (no AT commands) so ModemManager leaves the port alone.
 * Everything runs in the USB_LP interrupt except usb_cdc_write/usb_cdc_poll, which mask it briefly. */
#include <stdint.h>
#include "regs.h"
#include "usb_cdc.h"

int console_rx_push(uint8_t c);        /* main.c: input ring shared with USART1 */
unsigned console_rx_free(void);
uint32_t millis(void);

#define EP_CTR_RX  0x8000u
#define EP_DTOG_RX 0x4000u
#define EP_STAT_RX 0x3000u
#define EP_SETUP   0x0800u
#define EP_KEEP    0x070Fu             /* EP_TYPE | EP_KIND | EA: plain read/write bits */
#define EP_CTR_TX  0x0080u
#define EP_DTOG_TX 0x0040u
#define EP_STAT_TX 0x0030u
#define T_BULK      0x0000u
#define T_CONTROL   0x0200u
#define T_INTERRUPT 0x0600u
#define RX_VALID 0x3000u
#define TX_STALL 0x0010u
#define TX_NAK   0x0020u
#define TX_VALID 0x0030u
#define ISTR_CTR   (1u << 15)
#define ISTR_RESET (1u << 10)

/* Packet memory: 512 B; the CPU sees each 16-bit word at a 32-bit stride. Buffer table at 0. */
#define PMA16(off)     (*(volatile uint32_t *)(USB_PMA + 2u * (off)))
#define BT_ADDR_TX(n)  PMA16(8u * (n) + 0)
#define BT_COUNT_TX(n) PMA16(8u * (n) + 2)
#define BT_ADDR_RX(n)  PMA16(8u * (n) + 4)
#define BT_COUNT_RX(n) PMA16(8u * (n) + 6)
enum { EP0_TX = 0x40, EP0_RX = 0x80, EP1_RX = 0xC0, EP1_TX = 0x100, EP2_TX = 0x140 };
#define RX_64 0x8400u                   /* BL_SIZE = 32 B blocks, NUM_BLOCK = 1: 64-byte receive buffer */

static const uint8_t dev_desc[18] = {
    18, 1, 0x00, 0x02,                 /* USB 2.0 */
    0x02, 0x00, 0x00, 64,              /* class CDC, EP0 64 B */
    USB_CDC_VID & 0xFF, USB_CDC_VID >> 8, USB_CDC_PID & 0xFF, USB_CDC_PID >> 8,
    0x00, 0x01, 1, 2, 3, 1,            /* bcdDevice 1.00, strings, 1 configuration */
};
static const uint8_t cfg_desc[67] = {
    9, 2, 67, 0, 2, 1, 0, 0x80, 50,    /* 2 interfaces, bus powered, 100 mA */
    9, 4, 0, 0, 1, 0x02, 0x02, 0x00, 0,  /* communication interface: ACM, no AT protocol */
    5, 0x24, 0x00, 0x10, 0x01,         /* header: CDC 1.10 */
    5, 0x24, 0x01, 0x00, 1,            /* call management: none, data on interface 1 */
    4, 0x24, 0x02, 0x02,               /* ACM: Set/Get_Line_Coding, Set_Control_Line_State */
    5, 0x24, 0x06, 0, 1,               /* union: 0 controls 1 */
    7, 5, 0x82, 0x03, 16, 0, 255,      /* EP2 IN interrupt */
    9, 4, 1, 0, 2, 0x0A, 0x00, 0x00, 0,  /* data interface */
    7, 5, 0x01, 0x02, 64, 0, 0,        /* EP1 OUT bulk */
    7, 5, 0x81, 0x02, 64, 0, 0,        /* EP1 IN bulk */
};
static const char *product_str = "NickLink test console";
static uint8_t str_buf[2 + 2 * 40];
static uint8_t line_coding[7] = {0x00, 0xC2, 0x01, 0x00, 0, 0, 8};  /* 115200 8N1; the baud rate is ignored */

static volatile uint8_t configured, dtr, open_event, rx_paused;
static const uint8_t *ctl_ptr;
static uint32_t ctl_rem;
static uint8_t ctl_zlp, ctl_in, pending_addr, expect_line_coding, cfg_value, ep0_small[2];

#define TXN 2048u                       /* output ring, power of two */
static volatile uint8_t txr[TXN];       /* volatile: the byte must be stored before tx_head moves past it,
                                           or the USB interrupt can send the slot's old contents */
static volatile uint32_t tx_head, tx_tail;
static volatile uint8_t tx_busy, tx_last_full;

static void irq_off(void) { NVIC_ICER0 = 1u << 20; __asm volatile("dsb\n\tisb"); }
static void irq_on(void) { NVIC_ISER0 = 1u << 20; }

static void pma_write(uint32_t off, const uint8_t *p, uint32_t n) {
    for (uint32_t i = 0; i < n; i += 2) PMA16(off + i) = p[i] | (i + 1 < n ? (uint32_t)p[i + 1] << 8 : 0);
}
static void pma_read(uint32_t off, uint8_t *p, uint32_t n) {
    for (uint32_t i = 0; i < n; i += 2) {
        uint32_t w = PMA16(off + i);
        p[i] = w;
        if (i + 1 < n) p[i + 1] = w >> 8;
    }
}

/* EPnR: STAT/DTOG bits toggle on writing 1, CTR bits clear on writing 0. */
static void ep_stat_rx(int n, uint32_t s) {
    uint32_t v = USB_EPR(n);
    USB_EPR(n) = (v & EP_KEEP) | EP_CTR_RX | EP_CTR_TX | ((v ^ s) & EP_STAT_RX);
}
static void ep_stat_tx(int n, uint32_t s) {
    uint32_t v = USB_EPR(n);
    USB_EPR(n) = (v & EP_KEEP) | EP_CTR_RX | EP_CTR_TX | ((v ^ s) & EP_STAT_TX);
}
static void ep_clr_rx(int n) { USB_EPR(n) = (USB_EPR(n) & EP_KEEP) | EP_CTR_TX; }
static void ep_clr_tx(int n) { USB_EPR(n) = (USB_EPR(n) & EP_KEEP) | EP_CTR_RX; }
static void ep_init(int n, uint32_t type, uint32_t rx, uint32_t tx) {  /* also resets both data toggles */
    uint32_t v = USB_EPR(n);
    USB_EPR(n) = type | (uint32_t)n | EP_CTR_RX | EP_CTR_TX | (v & (EP_DTOG_RX | EP_DTOG_TX)) |
                 ((v ^ rx) & EP_STAT_RX) | ((v ^ tx) & EP_STAT_TX);
}

static uint32_t str_desc(uint8_t idx) {
    char hex[25];
    const char *s;
    uint32_t n;
    if (idx == 0) {                    /* language: English (US) */
        str_buf[0] = 4; str_buf[1] = 3; str_buf[2] = 0x09; str_buf[3] = 0x04;
        return 4;
    }
    if (idx == 3) {  /* serial = chip UID, as the banner prints it */
        for (int w = 0; w < 3; w++)
            for (int i = 0; i < 8; i++) hex[w * 8 + i] = "0123456789ABCDEF"[(UID(2 - w) >> (28 - 4 * i)) & 0xF];
        hex[24] = 0;
        s = hex;
    } else s = idx == 1 ? "NickLink" : product_str;
    for (n = 0; s[n] && n < 40; n++) { str_buf[2 + 2 * n] = s[n]; str_buf[3 + 2 * n] = 0; }
    str_buf[0] = 2 + 2 * n;
    str_buf[1] = 3;
    return str_buf[0];
}

/* ---- EP0 control transfers ---------------------------------------------- */
static void ep0_next(void) {
    uint32_t n = ctl_rem > 64 ? 64 : ctl_rem;
    if (!n) ctl_zlp = 0;
    pma_write(EP0_TX, ctl_ptr, n);
    BT_COUNT_TX(0) = n;
    ctl_ptr += n;
    ctl_rem -= n;
    ctl_in = ctl_rem || ctl_zlp;
    ep_stat_tx(0, TX_VALID);
}
static void ep0_send(const void *p, uint32_t len, uint32_t wlen) {  /* data stage IN, or ZLP status */
    if (len > wlen) len = wlen;
    ctl_ptr = p;
    ctl_rem = len;
    ctl_zlp = len && len < wlen && len % 64 == 0;  /* host asked for more: end with a short packet */
    ep0_next();
}
static void ep0_ack(void) { ep0_send(0, 0, 0); }
static void ep0_stall(void) { ep_stat_tx(0, TX_STALL); }  /* the next SETUP is accepted regardless */

static void tx_kick(void);
static void cdc_configure(void) {
    ep_init(1, T_BULK, RX_VALID, TX_NAK);
    ep_init(2, T_INTERRUPT, 0, TX_NAK);
    tx_busy = tx_last_full = rx_paused = 0;
    configured = 1;
    tx_kick();
}

static void on_setup(const uint8_t *s) {
    uint8_t type = s[0], req = s[1];
    uint16_t val = s[2] | s[3] << 8, idx = s[4] | s[5] << 8, len = s[6] | s[7] << 8;
    ctl_in = 0;
    if ((type & 0x60) == 0x00) {         /* standard */
        if (req == 0x06) {               /* GET_DESCRIPTOR */
            if (val >> 8 == 1) ep0_send(dev_desc, sizeof dev_desc, len);
            else if (val >> 8 == 2) ep0_send(cfg_desc, sizeof cfg_desc, len);
            else if (val >> 8 == 3 && (val & 0xFF) <= 3) ep0_send(str_buf, str_desc(val & 0xFF), len);
            else ep0_stall();            /* device qualifier etc.: full-speed only */
        } else if (req == 0x05) {        /* SET_ADDRESS: applied after the status stage */
            pending_addr = val & 0x7F;
            ep0_ack();
        } else if (req == 0x09) {        /* SET_CONFIGURATION */
            cfg_value = val & 0xFF;
            if (cfg_value) cdc_configure(); else configured = 0;
            ep0_ack();
        } else if (req == 0x08) {        /* GET_CONFIGURATION */
            ep0_small[0] = cfg_value;
            ep0_send(ep0_small, 1, len);
        } else if (req == 0x00) {        /* GET_STATUS */
            ep0_small[0] = ep0_small[1] = 0;
            ep0_send(ep0_small, 2, len);
        } else if (req == 0x0A) {        /* GET_INTERFACE */
            ep0_small[0] = 0;
            ep0_send(ep0_small, 1, len);
        } else if (req == 0x01 && (type & 0x1F) == 2 && val == 0 && (idx & 0x7F) == 1) {
            cdc_configure();             /* CLEAR_FEATURE(ENDPOINT_HALT) on EP1: data toggles back to DATA0 */
            ep0_ack();
        } else if (req == 0x01 || req == 0x03 || req == 0x0B) {
            ep0_ack();                   /* other CLEAR/SET_FEATURE, SET_INTERFACE */
        } else ep0_stall();
    } else if ((type & 0x60) == 0x20) {  /* CDC class */
        if (req == 0x20) expect_line_coding = 1;              /* SET_LINE_CODING: 7 bytes follow */
        else if (req == 0x21) ep0_send(line_coding, 7, len);  /* GET_LINE_CODING */
        else if (req == 0x22) {                               /* SET_CONTROL_LINE_STATE */
            if ((val & 1) && !dtr) open_event = 1;
            dtr = val & 1;
            if (!dtr) tx_tail = tx_head;                      /* terminal closed: drop what it won't read */
            ep0_ack();
        } else if (req == 0x23) ep0_ack();                    /* SEND_BREAK */
        else ep0_stall();
    } else ep0_stall();
}

static void ep0_irq(void) {
    uint32_t v = USB_EPR(0);
    if (v & EP_CTR_TX) {
        ep_clr_tx(0);
        if (pending_addr) { USB_DADDR = 0x80u | pending_addr; pending_addr = 0; }
        if (ctl_in) ep0_next();
    }
    if (v & EP_CTR_RX) {
        uint32_t n = BT_COUNT_RX(0) & 0x3FF;
        ep_clr_rx(0);
        if (v & EP_SETUP) {
            uint8_t s[8];
            pma_read(EP0_RX, s, 8);
            expect_line_coding = 0;
            on_setup(s);
        } else if (expect_line_coding) {  /* OUT data stage */
            if (n >= 7) pma_read(EP0_RX, line_coding, 7);
            expect_line_coding = 0;
            ep0_ack();
        }
        ep_stat_rx(0, RX_VALID);
    }
}

/* ---- EP1 bulk data -------------------------------------------------------- */
static void tx_kick(void) {  /* USB interrupt masked, or from it */
    if (!configured || tx_busy) return;
    uint32_t used = (tx_head - tx_tail) & (TXN - 1);
    if (!used && !tx_last_full) return;
    uint8_t b[64];
    uint32_t n = used > 64 ? 64 : used;
    for (uint32_t i = 0; i < n; i++) b[i] = txr[(tx_tail + i) & (TXN - 1)];
    tx_tail = (tx_tail + n) & (TXN - 1);
    pma_write(EP1_TX, b, n);
    BT_COUNT_TX(1) = n;
    tx_last_full = n == 64;            /* a full packet with nothing after it needs a ZLP to end the transfer */
    tx_busy = 1;
    ep_stat_tx(1, TX_VALID);
}

static void ep1_irq(void) {
    uint32_t v = USB_EPR(1);
    if (v & EP_CTR_RX) {
        ep_clr_rx(1);
        uint8_t b[64];
        uint32_t n = BT_COUNT_RX(1) & 0x3FF;
        if (n > 64) n = 64;
        pma_read(EP1_RX, b, n);
        for (uint32_t i = 0; i < n; i++) console_rx_push(b[i]);
        if (console_rx_free() >= 64) ep_stat_rx(1, RX_VALID); else rx_paused = 1;  /* NAK until there's room */
    }
    if (v & EP_CTR_TX) {
        ep_clr_tx(1);
        tx_busy = 0;
        tx_kick();
    }
}

static void usb_bus_reset(void) {
    USB_BTABLE = 0;
    BT_ADDR_TX(0) = EP0_TX; BT_COUNT_TX(0) = 0; BT_ADDR_RX(0) = EP0_RX; BT_COUNT_RX(0) = RX_64;
    BT_ADDR_TX(1) = EP1_TX; BT_COUNT_TX(1) = 0; BT_ADDR_RX(1) = EP1_RX; BT_COUNT_RX(1) = RX_64;
    BT_ADDR_TX(2) = EP2_TX; BT_COUNT_TX(2) = 0; BT_ADDR_RX(2) = 0;      BT_COUNT_RX(2) = 0;
    ep_init(0, T_CONTROL, RX_VALID, TX_NAK);
    configured = dtr = tx_busy = tx_last_full = rx_paused = 0;
    ctl_in = pending_addr = expect_line_coding = cfg_value = 0;
    USB_DADDR = 0x80;                  /* enable, address 0 */
}

void USB_LP_IRQHandler(void) {
    uint32_t istr = USB_ISTR;
    if (istr & ISTR_RESET) {
        USB_ISTR = 0xFFFFu & ~ISTR_RESET;
        usb_bus_reset();
    }
    while ((istr = USB_ISTR) & ISTR_CTR) {
        int ep = istr & 0xF;
        if (ep == 0) ep0_irq();
        else if (ep == 1) ep1_irq();
        else { ep_clr_rx(ep); ep_clr_tx(ep); }
    }
}

/* ---- API ------------------------------------------------------------------- */
void usb_cdc_init(const char *product) {
    product_str = product;
    RCC_APB1ENR |= 1u << 23;           /* USB clock */
    USB_CNTR = 1;                      /* FRES with PDWN cleared: power up the transceiver */
    for (volatile int i = 0; i < 100; i++) {}  /* tSTARTUP 1 us */
    USB_CNTR = 0;
    USB_ISTR = 0;
    usb_bus_reset();
    USB_CNTR = (1u << 15) | (1u << 10);  /* CTRM, RESETM */
    irq_on();                          /* USB_LP_CAN1_RX0, IRQ 20 */
}

void usb_cdc_write(const char *p, int n) {
    if (!configured || !dtr) return;
    for (int i = 0; i < n; i++) {
        uint32_t next = (tx_head + 1) & (TXN - 1);
        if (next == tx_tail) {         /* full: give the host up to 20 ms to read */
            irq_off(); tx_kick(); irq_on();
            for (uint32_t t0 = millis(); next == tx_tail && millis() - t0 < 20;) {}
            if (next == tx_tail) return;
        }
        txr[tx_head] = p[i];
        tx_head = next;
    }
    irq_off(); tx_kick(); irq_on();
}

void usb_cdc_poll(void) {
    if (rx_paused && console_rx_free() >= 64) {
        irq_off();
        rx_paused = 0;
        if (configured) ep_stat_rx(1, RX_VALID);
        irq_on();
    }
}

int usb_cdc_connected(void) { return configured && dtr; }
int usb_cdc_tx_idle(void) { return tx_head == tx_tail && !tx_busy; }

int usb_cdc_take_open_event(void) {
    if (!open_event) return 0;
    open_event = 0;
    return 1;
}
