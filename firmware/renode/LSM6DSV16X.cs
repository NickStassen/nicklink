// Minimal ST LSM6DSV16X I2C model for Renode: register file, WHO_AM_I = 0x70, SW_RESET,
// accel/gyro/temp output registers from settable raw values, and tap/double-tap/wake-up events
// that drive INT1 only if the firmware routed them (FUNCTIONS_ENABLE.INTERRUPTS_ENABLE + MD1_CFG),
// honouring IF_CFG.H_LACTIVE and TAP_CFG0.LIR (latched until ALL_INT_SRC is read).
// Not modelled: FIFO/SFLP, embedded-function bank, real tap detection from samples, INT2, OIS.
using Antmicro.Renode.Core;
using Antmicro.Renode.Logging;
using Antmicro.Renode.Peripherals.I2C;

namespace Antmicro.Renode.Peripherals.Sensors
{
    public class LSM6DSV16X : II2CPeripheral
    {
        public LSM6DSV16X()
        {
            INT1 = new GPIO();
            Reset();
        }

        public GPIO INT1 { get; }
        public int AccX { get; set; }
        public int AccY { get; set; }
        public int AccZ { get; set; } = 16393;   // ~ +1 g at +-2 g (0.061 mg/LSB)
        public int GyroX { get; set; }
        public int GyroY { get; set; }
        public int GyroZ { get; set; }
        public int Temp { get; set; }             // 0 = 25 C, 256 LSB/C

        public void Reset()
        {
            var ifcfg = regs == null ? (byte)0 : regs[IF_CFG];
            regs = new byte[256];
            regs[WHO_AM_I] = 0x70;
            regs[CTRL3] = 0x44;
            regs[IF_CFG] = ifcfg;                  // not reset by SW_RESET
            pointer = 0;
            INT1.Set(false);                       // "output forced to ground"
        }

        public void Write(byte[] data)
        {
            this.Log(LogLevel.Debug, "write {0}", string.Join(" ", System.Array.ConvertAll(data, x => x.ToString("X2"))));
            if(data.Length == 0) return;
            pointer = data[0];                     // the I2C controller hands over one transaction per call
            for(var i = 1; i < data.Length; i++)
            {
                WriteRegister(pointer, data[i]);
                Advance();
            }
        }

        // Renode 1.16's STM32F4_I2C asks for one byte per address phase and serves every following DR read
        // from that buffer, so return a 16-byte burst. Read side effects (ALL_INT_SRC clear) apply to the
        // first byte only; the firmware never bursts across 0x1D.
        public byte[] Read(int count = 1)
        {
            this.Log(LogLevel.Debug, "read {0} @0x{1:X2}", count, pointer);
            var result = new byte[System.Math.Max(count, 16)];
            for(var i = 0; i < result.Length; i++)
            {
                result[i] = ReadRegister(pointer, i == 0);
                Advance();
            }
            return result;
        }

        public void FinishTransmission()
        {
        }

        public void Tap() { Event(TAP_SRC, 0x40 | 0x20 | 0x01, 0x04, 0x40); }        // TAP_IA|SINGLE_TAP|Z, MD1 INT1_SINGLE_TAP
        public void DoubleTap() { Event(TAP_SRC, 0x40 | 0x10 | 0x01, 0x04, 0x08); }  // TAP_IA|DOUBLE_TAP|Z, MD1 INT1_DOUBLE_TAP
        public void WakeUp() { Event(WAKE_UP_SRC, 0x08 | 0x01, 0x02, 0x20); }       // WU_IA|Z_WU, MD1 INT1_WU

        private void Event(byte srcReg, byte srcBits, byte allBits, byte md1Bit)
        {
            regs[srcReg] |= srcBits;
            regs[ALL_INT_SRC] |= allBits;
            var routed = (regs[FUNCTIONS_ENABLE] & 0x80) != 0 && (regs[MD1_CFG] & md1Bit) != 0;
            this.Log(LogLevel.Info, "event src 0x{0:X2}, routed to INT1: {1}", srcReg, routed);
            if(!routed) return;
            DriveInt1(true);
            if((regs[TAP_CFG0] & 0x01) == 0)       // pulsed mode
            {
                DriveInt1(false);
            }
        }

        private void DriveInt1(bool active)
        {
            int1Active = active;
            INT1.Set(active ^ ((regs[IF_CFG] & 0x10) != 0));
        }

        private byte ReadRegister(byte reg, bool sideEffects)
        {
            if(reg >= 0x20 && reg <= 0x2D)
            {
                int[] v = { Temp, GyroX, GyroY, GyroZ, AccX, AccY, AccZ };
                var s = v[(reg - 0x20) / 2];
                return (byte)((reg & 1) == 0 ? s & 0xFF : (s >> 8) & 0xFF);
            }
            var value = regs[reg];
            if(reg == ALL_INT_SRC && sideEffects)  // read releases latched interrupts
            {
                regs[ALL_INT_SRC] = 0;
                regs[TAP_SRC] = 0;
                regs[WAKE_UP_SRC] = 0;
                if(int1Active) DriveInt1(false);
            }
            return value;
        }

        private void WriteRegister(byte reg, byte value)
        {
            if(reg == WHO_AM_I || reg == ALL_INT_SRC || reg == TAP_SRC || reg == WAKE_UP_SRC) return;  // read-only
            if(reg == CTRL3 && (value & 0x01) != 0) { this.Log(LogLevel.Info, "SW_RESET"); Reset(); pointer = CTRL3; return; }
            regs[reg] = value;
            if(reg == IF_CFG) DriveInt1(int1Active);
        }

        private void Advance()
        {
            if((regs[CTRL3] & 0x04) != 0) pointer++;   // IF_INC
        }

        private byte[] regs;
        private byte pointer;
        private bool int1Active;

        private const byte IF_CFG = 0x03, WHO_AM_I = 0x0F, CTRL3 = 0x12, ALL_INT_SRC = 0x1D;
        private const byte WAKE_UP_SRC = 0x45, TAP_SRC = 0x46, FUNCTIONS_ENABLE = 0x50, TAP_CFG0 = 0x56, MD1_CFG = 0x5E;
    }
}
