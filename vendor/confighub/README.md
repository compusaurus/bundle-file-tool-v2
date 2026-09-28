# ConfigHub PyThermX runtime snapshot

`pythermx-0.5.2-py3-none-any.whl` in this directory is built from the current
local `therm_project/therm/src/pythermx` source for ConfigHub's schema 1.3 profile.
Its SHA256 is `1ba20e616f78cb2fcf5407f775fdbdb2587d53e0e048283f624af8b95f5b1673`.
The source retains version 0.5.2 while its older dist wheel supports only
schemas 1.0/1.1. This exact snapshot is delivered and checksum-verified for the
PyProjectMgr environment, not substituted for BFT's progress runtime.

BFT continues using the separate `vendor/pythermx-0.5.3-py3-none-any.whl` to
retain its qualified Tk layout behavior. The snapshot includes the upstream
MIT license. No PyThermX source files or user profile were changed by this task.
