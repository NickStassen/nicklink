/* The few STM32F103 registers this firmware touches (RM0008). */
#pragma once
#include <stdint.h>
#define R32(a) (*(volatile uint32_t *)(a))

#define RCC_CR       R32(0x40021000)
#define RCC_CFGR     R32(0x40021004)
#define RCC_CIR      R32(0x40021008)
#define RCC_APB2ENR  R32(0x40021018)
#define RCC_APB1ENR  R32(0x4002101C)
#define RCC_CSR      R32(0x40021024)
#define PWR_CR       R32(0x40007000)
#define PWR_CSR      R32(0x40007004)
#define FLASH_ACR    R32(0x40022000)

#define GPIO_BASE(p) (0x40010800u + 0x400u * (p))   /* 0=A 1=B 2=C 3=D */
#define GPIO_CRL(p)  R32(GPIO_BASE(p) + 0x00)
#define GPIO_CRH(p)  R32(GPIO_BASE(p) + 0x04)
#define GPIO_IDR(p)  R32(GPIO_BASE(p) + 0x08)
#define GPIO_ODR(p)  R32(GPIO_BASE(p) + 0x0C)
#define GPIO_BSRR(p) R32(GPIO_BASE(p) + 0x10)
#define GPIO_BRR(p)  R32(GPIO_BASE(p) + 0x14)
#define PA 0
#define PB 1
#define PC 2

#define AFIO_MAPR    R32(0x40010004)
#define AFIO_EXTICR1 R32(0x40010008)
#define EXTI_IMR     R32(0x40010400)
#define EXTI_RTSR    R32(0x40010408)
#define EXTI_PR      R32(0x40010414)

#define USART1_SR    R32(0x40013800)
#define USART1_DR    R32(0x40013804)
#define USART1_BRR   R32(0x40013808)
#define USART1_CR1   R32(0x4001380C)

#define ADC1_SR      R32(0x40012400)
#define ADC1_CR2     R32(0x40012408)
#define ADC1_SMPR1   R32(0x4001240C)
#define ADC1_SMPR2   R32(0x40012410)
#define ADC1_SQR1    R32(0x4001242C)
#define ADC1_SQR3    R32(0x40012434)
#define ADC1_DR      R32(0x4001244C)

#define I2C1_CR1     R32(0x40005400)
#define I2C1_CR2     R32(0x40005404)
#define I2C1_DR      R32(0x40005410)
#define I2C1_SR1     R32(0x40005414)
#define I2C1_SR2     R32(0x40005418)
#define I2C1_CCR     R32(0x4000541C)
#define I2C1_TRISE   R32(0x40005420)

#define SYST_CSR     R32(0xE000E010)
#define SYST_RVR     R32(0xE000E014)
#define SYST_CVR     R32(0xE000E018)
#define NVIC_ISER0   R32(0xE000E100)
#define NVIC_ISER1   R32(0xE000E104)
#define SCB_VTOR     R32(0xE000ED08)
#define SCB_SCR      R32(0xE000ED10)
#define SCB_AIRCR    R32(0xE000ED0C)

#define FLASH_SIZE_KB (*(volatile uint16_t *)0x1FFFF7E0)
#define UID(n)        R32(0x1FFFF7E8 + 4 * (n))
