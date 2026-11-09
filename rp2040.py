# pyOCD user script
# 'reset_to_usb_boot' command will resets the RP2040 and re-start in BOOTSEL mode
# 'reset_to_app' command will resets the RP2040 and re-start in application mode
#
# Howto invoke:
# pyocd cmd -t rp2040 --script rp2040.py -c reset_to_usb_boot
# pyocd cmd -t rp2040 --script rp2040.py -c reset_to_app

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Bootrom API table scanning
BOOTROM_API_TABLE_PTR_ADDR = 0x14  # Address containing pointer to API table
BOOTROM_MAGIC_UB = 0x4255  # 'UB' in little-endian (USB boot function)
BOOTROM_TABLE_END_MARKER = 0x0000  # End of table marker
MAX_TABLE_SCAN_ENTRIES = 32  # Maximum entries to scan for safety

# Boot ROM address space (RP2040 bootrom is mapped to 0x00000000 - 0x00004000)
BOOTROM_MIN_ADDR = 0x00000000
BOOTROM_MAX_ADDR = 0x00004000

# Memory mapped registers
WATCHDOG_BASE = 0x40058000
WATCHDOG_CTRL_OFFSET = 0x00000000
WATCHDOG_CTRL_TRIGGER_BITS = 0x80000000
WATCHDOG_SCRATCH0_OFFSET = 0x0000000C

PSM_BASE = 0x40010000
PSM_WDSEL_OFFSET = 0x00000008
PSM_WDSEL_BITS = 0x0001FFFF
PSM_WDSEL_ROSC_BITS = 0x00000001
PSM_WDSEL_XOSC_BITS = 0x00000002

XOSC_BASE = 0x40024000
XOSC_CTRL_OFFSET = 0x00000000
XOSC_CTRL_VAL = (0xFAB << 12) | 0xAA0  # Enable XOSC with required magic


# -----------------------------------------------------------------------------
# pyOCD options
# -----------------------------------------------------------------------------

options.update(
    {
        "target_override": "rp2040",
    }
)

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def find_bootrom_function(magic):
    """
    Scans the bootrom API table for a function with the given magic identifier.

    Args:
        magic (int): 16-bit magic value (e.g., 0x4255 for 'UB')

    Returns:
        int: Absolute address of the function, or 0 if not found.
    """
    # Read pointer to the bootrom API table (16-bit value at 0x14)
    table_ptr = target.read16(BOOTROM_API_TABLE_PTR_ADDR)

    # Scan the table for the matching entry
    for _ in range(MAX_TABLE_SCAN_ENTRIES):
        code = target.read16(table_ptr)
        addr = target.read16(table_ptr + 2)
        table_ptr += 4

        if code == magic:
            # Found the function, return absolute address
            # (bootrom is mapped at 0x00000000, so addr is already absolute)
            return addr
        elif code == BOOTROM_TABLE_END_MARKER:
            # Reached end of table
            break

    return 0


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------


@command(help="re-start in BOOTSEL mode")
def reset_to_usb_boot():
    """Resets the target, locates the USB boot function in the bootrom API table, and jumps to it."""
    target.reset_and_halt()

    # Enable XOSC (crystal oscillator) - required for USB boot
    # Note: In a real system, you might need to wait for XOSC stability,
    # but the bootrom USB function typically handles this or assumes it's enabled.
    target.write32(XOSC_BASE + XOSC_CTRL_OFFSET, XOSC_CTRL_VAL)

    # Find the _reset_to_usb_boot function in bootrom
    func = find_bootrom_function(BOOTROM_MAGIC_UB)

    if func == 0:
        raise RuntimeError(
            "Error: Could not find _reset_to_usb_boot function in bootrom table."
        )

    # Validate address is within Boot ROM space (sanity check)
    if not (BOOTROM_MIN_ADDR <= func < BOOTROM_MAX_ADDR):
        raise RuntimeError(
            f"Error: _reset_to_usb_boot 0x{func:04X} is outside expected bootrom range."
        )

    print(f"Found _reset_to_usb_boot function at address: 0x{func:04X}")

    # Setup registers and jump to bootloader
    target.write_core_register("r0", 0)  # gpio_activity_pin_mask = 0
    target.write_core_register("r1", 0)  # disable_interface_mask = 0
    target.write_core_register("pc", func)  # Set program counter

    target.resume()


@command(help="re-start in application mode")
def reset_to_app():
    """Uses the watchdog peripheral to reset the chip and clear scratch registers, forcing a boot into the main application."""
    target.reset_and_halt()

    # Disable the watchdog timer and pause function to ensure clean state
    target.write32(WATCHDOG_BASE + WATCHDOG_CTRL_OFFSET, 0)

    # Clear SCRATCH0 to ensure bootrom doesn't re-enter a special mode (e.g., BOOTSEL)
    target.write32(WATCHDOG_BASE + WATCHDOG_SCRATCH0_OFFSET, 0)

    # Select all peripherals for watchdog reset except ROSC and XOSC
    # (these clock sources should not be reset to maintain system stability)
    target.write32(
        PSM_BASE + PSM_WDSEL_OFFSET,
        PSM_WDSEL_BITS & ~(PSM_WDSEL_ROSC_BITS | PSM_WDSEL_XOSC_BITS),
    )

    # Trigger a watchdog reset by setting the trigger bit (preserving other bits)
    ctrl_val = target.read32(WATCHDOG_BASE + WATCHDOG_CTRL_OFFSET)
    ctrl_val |= WATCHDOG_CTRL_TRIGGER_BITS
    target.write32(WATCHDOG_BASE + WATCHDOG_CTRL_OFFSET, ctrl_val)

    # Resume execution - watchdog will reset the chip almost immediately
    target.resume()
