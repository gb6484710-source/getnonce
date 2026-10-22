# getnonce

Get an apnonce/generator pair from any\* iDevice (including A12+) without jailbreak

<sup>\* May not work on really old devices, but you only really need this on A12+ anyway.</sup>

## Dependencies

- Python 3.8 or newer, below Python 4, with `rich ~= 12.5` (see `pyproject.toml`).
- libimobiledevice tools: `idevice_id`, `idevicediagnostics`, `ideviceinfo`, and `ideviceenterrecovery`.
- libirecovery tool: `irecovery`.

All five executables must be available in your `PATH` or the current working directory.
The script checks for them before prompting or communicating with a device, and exits
with an error if any are missing.

## Device waits and timeouts

Normal-mode waits (including after a reboot) and recovery-mode waits each have a
120-second timeout. Each device probe is limited to five seconds or the remaining
wait time, whichever is shorter. Failed probes are retried after a delay of up to
one second, also bounded by the remaining wait time.

If a device does not become available before the timeout, the script prints an
error identifying the mode and exits with status 1. In normal mode, make sure the
device is connected, unlocked, and trusted by the computer.

The timeout can be changed by passing `timeout` in seconds to `wait_for_device`
in the Python source; there is no command-line timeout option. These limits apply
to device polling, not every external command or the final "Press Enter to exit"
prompt.

The script reboots the device and enters recovery mode during verification.
A timeout does not automatically return the device to normal mode.
