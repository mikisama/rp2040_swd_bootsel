from pyocd.core.helpers import ConnectHelper


WATCHDOG_BASE = 0x40058000
WATCHDOG_CTRL_OFFSET = 0x00000000
WATCHDOG_CTRL_TRIGGER_BITS = 0x80000000

WATCHDOG_SCRATCH0_OFFSET = 0x0000000C

PSM_BASE = 0x40010000
PSM_WDSEL_OFFSET = 0x00000008
PSM_WDSEL_BITS = 0x0001FFFF
PSM_WDSEL_ROSC_BITS = 0x00000001
PSM_WDSEL_XOSC_BITS = 0x00000002

# Connect to the target.
with ConnectHelper.session_with_chosen_probe(
    target_override="rp2040",
) as session:
    target = session.target
    target.reset_and_halt()

    # disable the watchdog timer and disable pause watchdog
    target.write32(WATCHDOG_BASE + WATCHDOG_CTRL_OFFSET, 0)
    # set SCRATCH0
    target.write32(WATCHDOG_BASE + WATCHDOG_SCRATCH0_OFFSET, 0)

    # Reset everything apart from ROSC and XOSC
    target.write32(
        PSM_BASE + PSM_WDSEL_OFFSET,
        PSM_WDSEL_BITS & ~(PSM_WDSEL_ROSC_BITS | PSM_WDSEL_XOSC_BITS),
    )

    # Trigger a watchdog reset
    ctrl_val = target.read32(WATCHDOG_BASE + WATCHDOG_CTRL_OFFSET)
    ctrl_val |= WATCHDOG_CTRL_TRIGGER_BITS
    target.write32(WATCHDOG_BASE + WATCHDOG_CTRL_OFFSET, ctrl_val)

    target.resume()
