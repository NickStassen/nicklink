// Minimal STM32F1 RCC for Renode (the stock stm32f103.repl only has an SVD tag here).
// Ready bits follow their enable bits, SWS follows SW, RCC_CSR keeps reset flags across resets
// (power-on = PORRSTF|PINRSTF, every later machine reset = PINRSTF) and clears them on RMVF.
// HseBroken = true makes the crystal never start, to exercise the firmware's HSI fallback.
using Antmicro.Renode.Core;
using Antmicro.Renode.Peripherals.Bus;

namespace Antmicro.Renode.Peripherals.Miscellaneous
{
    public class NickLinkRCC : IDoubleWordPeripheral, IKnownSize
    {
        public NickLinkRCC()
        {
            csr = PORRSTF | PINRSTF;
            Reset();
        }

        public bool HseBroken { get; set; }
        public long Size => 0x400;

        public void Reset()
        {
            regs = new uint[0x100];
            regs[0] = 0x00000083;      // CR: HSION, HSIRDY, HSITRIM=16
            regs[0x14 / 4] = 0x14;     // AHBENR: SRAM, FLITF
            if(!first) { csr |= PINRSTF; }
            first = false;
        }

        public uint ReadDoubleWord(long offset)
        {
            switch(offset)
            {
            case 0x00:
                {
                    var cr = regs[0] & ~(HSIRDY | HSERDY | PLLRDY);
                    if((cr & HSION) != 0) cr |= HSIRDY;
                    if((cr & HSEON) != 0 && !HseBroken) cr |= HSERDY;
                    if((cr & PLLON) != 0 && PllSourceReady(cr)) cr |= PLLRDY;
                    return cr;
                }
            case 0x04:
                {
                    var cfgr = regs[1] & ~0xCu;
                    var sw = cfgr & 3;
                    var ready = ReadDoubleWord(0) & (sw == 0 ? HSIRDY : sw == 1 ? HSERDY : PLLRDY);
                    return cfgr | ((ready != 0 ? sw : 0) << 2);
                }
            case 0x24:
                return csr | (regs[0x24 / 4] & 1) | ((regs[0x24 / 4] & 1) << 1);   // LSION -> LSIRDY
            default:
                return offset < Size ? regs[offset / 4] : 0;
            }
        }

        public void WriteDoubleWord(long offset, uint value)
        {
            if(offset == 0x24)
            {
                if((value & RMVF) != 0) csr = 0;
                regs[0x24 / 4] = value & 1;
                return;
            }
            if(offset < Size) regs[offset / 4] = value;
        }

        private bool PllSourceReady(uint cr)
        {
            var pllsrcHse = (regs[1] & (1u << 16)) != 0;
            return pllsrcHse ? ((cr & HSEON) != 0 && !HseBroken) : (cr & HSION) != 0;
        }

        private uint[] regs;
        private uint csr;
        private bool first = true;

        private const uint HSION = 1u << 0, HSIRDY = 1u << 1, HSEON = 1u << 16, HSERDY = 1u << 17;
        private const uint PLLON = 1u << 24, PLLRDY = 1u << 25;
        private const uint RMVF = 1u << 24, PINRSTF = 1u << 26, PORRSTF = 1u << 27;
    }
}
