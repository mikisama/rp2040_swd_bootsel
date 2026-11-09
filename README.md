# Enter/Exit RP2040 BOOTSEL Mode via SWD

Toggle an RP2040 between USB BOOTSEL and normal application mode over SWD, without unplugging or holding the BOOTSEL button.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- [pyOCD](https://pyocd.io/) installed
- An SWD debug probe connected to the RP2040 (e.g. Raspberry Pi Debug Probe, CMSIS-DAP, picoprobe)
- `rp2040.py` — pyOCD script defining the `reset_to_usb_boot` and `reset_to_app` commands

## Quick Start

Two ways to drive it: a small uv-run script wrapper, or raw `pyocd` commands.

### Option A — uv scripts

```sh
uv sync

# Enter BOOTSEL (USB boot mode)
uv run reset_to_usb_boot.py

# Return to the application
uv run reset_to_app.py
```

### Option B — pyOCD directly

```sh
# Enter BOOTSEL
pyocd cmd -t rp2040 --script rp2040.py -c reset_to_usb_boot

# Return to application
pyocd cmd -t rp2040 --script rp2040.py -c reset_to_app
```

## Commands

| Command | Effect |
| --- | --- |
| `reset_to_usb_boot` | Resets the RP2040 into the ROM USB bootloader (BOOTSEL / RPI-RP2 drive) |
| `reset_to_app` | Resets the RP2040 back into the flashed application |

## Notes

- The target must be reachable over SWD; if pyOCD can't find the probe, check the wiring and `pyocd list`.
- `reset_to_usb_boot` reboots into the ROM bootloader, so the SWD session ends — re-flash or use `reset_to_app` afterwards to resume the application.
- Both commands assume a default RP2040 target; adjust `-t` if you're using a different chip variant.
