/* USB-C console: CDC ACM virtual serial port on the STM32F103's full-speed USB (PA11/PA12). */
#pragma once
#include <stdint.h>

#define USB_CDC_VID 0x1209  /* pid.codes */
#define USB_CDC_PID 0x0001  /* pid.codes test PID: fine for your own boards, not for products */

void usb_cdc_init(const char *product);    /* SYSCLK must be 72 MHz from HSE (USB = PLL / 1.5 = 48 MHz) */
void usb_cdc_write(const char *p, int n);  /* queued; dropped while no terminal has the port open (DTR low) */
void usb_cdc_poll(void);                   /* main loop: resume USB input once the console has room again */
int usb_cdc_take_open_event(void);         /* 1 once each time a terminal opens the port */
int usb_cdc_connected(void);               /* configured, and a terminal has the port open (DTR) */
int usb_cdc_tx_idle(void);                 /* everything written so far has reached the PC */
