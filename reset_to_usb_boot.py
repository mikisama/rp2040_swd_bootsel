from pyocd.core.helpers import ConnectHelper

XOSC_BASE = 0x40024000
XOSC_CTRL_OFFSET = 0x00000000
XOSC_CTRL_VAL = 0xFAB << 12 | 0xAA0

# Connect to the target.
with ConnectHelper.session_with_chosen_probe(
    target_override="rp2040",
) as session:
    target = session.target

    target.reset_and_halt()

    # enable XOSC
    target.write32(XOSC_BASE + XOSC_CTRL_OFFSET, XOSC_CTRL_VAL)

    ptr = target.read16(0x14)
    usb_boot_addr = 0
    while True:
        code = target.read16(ptr)
        addr = target.read16(ptr + 2)
        ptr += 4

        asc = code.to_bytes(2, "little").decode()
        print(f"code = 0x{code:04X} [{asc}] addr = 0x{addr:04X}")

        if code == 0x4255:  # 'UB'
            usb_boot_addr = addr
            break
        if code == 0x0000:
            break

    print(f"{usb_boot_addr:x}")
    if usb_boot_addr == 0:
        print("Error: could not find function address")
        exit(1)

    target.write_core_register("r0", 0)  # gpio_activity_pin_mask = 0
    target.write_core_register("r1", 0)  # disable_interface_mask = 0
    target.write_core_register("pc", usb_boot_addr)

    target.resume()
