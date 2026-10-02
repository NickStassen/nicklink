*** Comments ***
NickLink v1.3 board-test firmware under Renode. Run via ../test.sh (renode-test in the antmicro/renode image).

*** Settings ***
Library           String
Library           OperatingSystem
Test Setup        Create NickLink
Resource          ${RENODEKEYWORDS}

*** Variables ***
${UART}           sysbus.usart1
${PROMPT}         type 'help'

*** Keywords ***
Create NickLink
    Reset Emulation
    Execute Command           path add @${CURDIR}
    Execute Command           $elf=@${CURDIR}/../build/nicklink-test.elf
    Execute Command           $raw=@${CURDIR}/../build/nicklink-test.bin
    Execute Command           include @${CURDIR}/nicklink.resc
    Create Terminal Tester    ${UART}    timeout=5

Boot To Prompt
    Start Emulation
    Wait For Line On Uart     ${PROMPT}

Pin Should Be
    [Arguments]    ${port}    ${pin}    ${state}
    ${gpios}=      Execute Command    sysbus.gpioPort${port} GetGPIOs
    Should Contain    ${gpios}    (${pin}, GPIO: ${state})

Count Set Pins
    ${n}=    Set Variable    ${0}
    FOR    ${port}    IN    A    B    C
        ${gpios}=    Execute Command    sysbus.gpioPort${port} GetGPIOs
        ${c}=        Get Count    ${gpios}    GPIO: set
        ${n}=        Evaluate    ${n} + ${c}
    END
    RETURN    ${n}

*** Test Cases ***
Banner Reports 72 MHz From HSE And Power-On Reset
    Start Emulation
    Wait For Line On Uart     NickLink v1.3 board test, SYSCLK 72000000 Hz
    Wait For Line On Uart     clock: HSE 8 MHz -> PLL x9 = 72 MHz
    # PLLMUL x9 | PLLSRC HSE | PPRE1 /2 | ADCPRE /6 | SW=SWS=PLL
    Wait For Line On Uart     RCC_CFGR 0x001D840A
    Wait For Line On Uart     reset cause: power-on
    Wait For Line On Uart     boot: flash aliased at 0x0 (BOOT0 was low); BOOT1/PB2 reads 0
    Wait For Line On Uart     ${PROMPT}

HSE Failure Falls Back To HSI
    Execute Command           sysbus.rcc HseBroken true
    Start Emulation
    Wait For Line On Uart     SYSCLK 64000000 Hz
    Wait For Line On Uart     clock: HSE FAILED to start -> HSI/2 x16 = 64 MHz
    Wait For Line On Uart     ${PROMPT}

User LED Blinks At 1 Hz
    Create LED Tester         sysbus.gpioPortC.led    defaultTimeout=2
    Boot To Prompt
    Assert LED Is Blinking    testDuration=3    onDuration=0.5    offDuration=0.5    tolerance=0.05

IMU WHO_AM_I And Sample
    Start Emulation
    Wait For Line On Uart     IMU: WHO_AM_I = 0x70 OK (LSM6DSV family)
    Wait For Line On Uart     IMU: 480 Hz
    Wait For Line On Uart     ${PROMPT}
    Execute Command           sysbus.i2c1.imu AccX -16384
    Execute Command           sysbus.i2c1.imu GyroZ 1000
    Write Line To Uart        imu
    Wait For Line On Uart     IMU: acc mg -999 0 999\\s+gyro dps 0 0 70\\s+temp 25.0 C    treatAsRegex=true
    Write Line To Uart        i2cscan
    Wait For Line On Uart     ^I2C1: 0x6A\\s*$    treatAsRegex=true

Tap Double-Tap And Wake On INT1
    Boot To Prompt
    Execute Command           sysbus.i2c1.imu Tap
    Wait For Line On Uart     tap
    Execute Command           sysbus.i2c1.imu DoubleTap
    Wait For Line On Uart     double-tap
    Execute Command           sysbus.i2c1.imu WakeUp
    Wait For Line On Uart     wake
    # latched INT1 must be released by the firmware's ALL_INT_SRC read
    Pin Should Be             A    0    unset

Pins Command Lists Generated Map
    Boot To Prompt
    Write Line To Uart        pins
    Wait For Line On Uart     10\\s+PA0\\s+PA0\\s+J1.19\\s+WKUP / IMU INT1 via 10k; R10 10k to IMU_INT1    treatAsRegex=true
    Wait For Line On Uart     33\\s+PA12\\s+USB_D\\+\\s+J2 USB, R11 4k7 to GND, R2 2k2 to VBUS    treatAsRegex=true
    Wait For Line On Uart     48\\s+VDD\\s+\\+3.3V    treatAsRegex=true

GPIO Walk Drives Each Header Pin Alone
    ${hdr}=                   Get File    ${CURDIR}/../build/pins.h
    @{pins}=                  Evaluate    [p for p in re.findall(r'\\{"(P[ABC]\\d+)", "(J\\d\\.\\d+)", (\\d), (\\d+)\\}', $hdr) if p[0] not in ("PA9", "PA10", "PA13", "PA14")]    re
    Boot To Prompt
    Write Line To Uart        walk 20
    FOR    ${p}    IN    @{pins}
        ${port}=    Evaluate    "ABC"[int(${p}[2])]
        Wait For Line On Uart     WALK ${p}[1] ${p}[0] high    pauseEmulation=true
        Pin Should Be             ${port}    ${p}[3]    set
        ${n}=                     Count Set Pins
        Should Be Equal As Integers    ${n}    1    more than one pin high while walking ${p}[0]
        Wait For Line On Uart     WALK ${p}[1] ${p}[0] low    pauseEmulation=true
        Pin Should Be             ${port}    ${p}[3]    unset
    END
    ${count}=                 Get Length    ${pins}
    Wait For Line On Uart     walk done: ${count} pins, 0 faults

Monitor Mode Sees Header Inputs
    Boot To Prompt
    Write Line To Uart        mon
    Wait For Line On Uart     mon: inputs with pull-down
    Execute Command           sysbus.gpioPortB OnGPIO 12 true
    Wait For Line On Uart     mon: J1.6 PB12=1
    Execute Command           sysbus.gpioPortB OnGPIO 12 false
    Wait For Line On Uart     mon: J1.6 PB12=0
    Execute Command           sysbus.gpioPortC OnGPIO 15 true
    Wait For Line On Uart     mon: J3.19 PC15=1
    Write Line To Uart        x    waitForEcho=false
    Wait For Line On Uart     mon done

NRST Reset Reports Pin Reset
    Boot To Prompt
    Execute Command           machine Reset
    Start Emulation
    Wait For Line On Uart     reset cause: NRST pin (RESET button)
    Wait For Line On Uart     ${PROMPT}

Software Reset Command Reboots
    Boot To Prompt
    Write Line To Uart        reset
    Wait For Line On Uart     resetting
    Wait For Line On Uart     NickLink v1.3 board test
    Wait For Line On Uart     ${PROMPT}
