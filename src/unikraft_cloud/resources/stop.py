# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Why an instance stopped, decoded from the two integers the API reports for
# it: a reason bitmask that says who initiated the stop, and a code the
# platform or the kernel left behind. The shape follows the Go SDK's
# platform/stop package, so the two SDKs describe a stop the same way.

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import ClassVar

__all__ = [
    "KernelStopCode",
    "KernelStopReason",
    "PlatformStopCode",
    "Stop",
    "StopReason",
    "errno_name",
]


class StopReason(IntFlag):
    """Who initiated a stop, as the bits of the API's ``stop_reason``.

    Each bit names an origin, and the named combinations are the scenarios
    the API documents. A forced stop gives the instance no chance to shut down,
    so it never carries the ``APPLICATION`` or ``KERNEL`` bits.

    .. code-block:: python

        reason = StopReason(instance.stop_reason)
        if reason & StopReason.KERNEL:
            print(instance.stop_code)
    """

    #: The kernel exited; ``stop_code`` says how.
    KERNEL = 1
    #: The application exited; ``exit_code`` says how.
    APPLICATION = 2
    #: The platform initiated the stop, e.g. an autoscale policy.
    PLATFORM = 4
    #: The user initiated the stop, e.g. through the API.
    USER = 8
    #: The stop was forced.
    FORCED = 16

    #: The API does not know why the instance stopped.
    UNKNOWN = 0
    #: The kernel exited on its own: a crash.
    KERNEL_CRASH = KERNEL
    #: The application exited and took the kernel with it.
    APP_EXIT = APPLICATION | KERNEL
    #: The platform stopped the instance cleanly, e.g. scale-to-zero.
    PLATFORM_SHUTDOWN = PLATFORM | APPLICATION | KERNEL
    #: The user stopped the instance, but the kernel had to kill the application.
    USER_SHUTDOWN_INCOMPLETE = USER | PLATFORM | KERNEL
    #: The user stopped the instance and it shut down cleanly.
    USER_SHUTDOWN_COMPLETE = USER | PLATFORM | APPLICATION | KERNEL
    #: The user force-stopped the instance.
    FORCED_USER_SHUTDOWN = FORCED | USER | PLATFORM

    def __format__(self, spec: str) -> str:
        # A number format keeps the bits; any other reads as the scenario's name.
        if spec and spec[-1] in "bcdoxXn":
            return format(int(self), spec)
        return format(str(self), spec)

    @property
    def forced(self) -> bool:
        """Whether the stop was forced."""
        return bool(self & StopReason.FORCED)

    @property
    def origin(self) -> str:
        """Who initiated the stop: ``platform``, ``user``, ``app``, ``kernel`` or ``unknown``."""
        if self & StopReason.PLATFORM and not self & StopReason.USER:
            return "platform"
        if self & StopReason.USER:
            return "user"
        if self & StopReason.APPLICATION:
            return "app"
        if self & StopReason.KERNEL:
            return "kernel"
        return "unknown"

    @property
    def flags(self) -> str:
        """The five-letter form the API documentation uses, e.g. ``-UPAK`` or ``FUP--``."""
        bits = (
            (StopReason.FORCED, "F"),
            (StopReason.USER, "U"),
            (StopReason.PLATFORM, "P"),
            (StopReason.APPLICATION, "A"),
            (StopReason.KERNEL, "K"),
        )
        return "".join(letter if self & bit else "-" for bit, letter in bits)

    def __str__(self) -> str:
        named = _REASONS.get(int(self))
        if named is not None:
            return named
        origin = self.origin
        if origin == "unknown":
            return "unknown stop"
        return f"forced {origin} stop" if self.forced else f"{origin} stop"


#: How the documented scenarios read.
_REASONS = {
    int(StopReason.UNKNOWN): "unknown stop",
    int(StopReason.KERNEL_CRASH): "kernel crash",
    int(StopReason.APP_EXIT): "app exit",
    int(StopReason.PLATFORM_SHUTDOWN): "platform shutdown",
    int(StopReason.USER_SHUTDOWN_INCOMPLETE): "user shutdown incomplete",
    int(StopReason.USER_SHUTDOWN_COMPLETE): "user shutdown complete",
    int(StopReason.FORCED_USER_SHUTDOWN): "forced user shutdown",
}


class PlatformStopCode(int):
    """The code of a stop the platform alone initiated: why a node gave up on the instance.

    An ``int``, so a code this SDK does not know yet still comes through and
    compares to the constants here.
    """

    #: The platform did not say.
    UNKNOWN: ClassVar[int] = 0
    #: The node could not pull the image.
    IMAGE_PULL_FAILED: ClassVar[int] = 1

    def __str__(self) -> str:
        return _PLATFORM_CODES.get(int(self), f"code({int(self)})")

    def __repr__(self) -> str:
        return f"{type(self).__name__}({int(self)})"


_PLATFORM_CODES = {
    PlatformStopCode.UNKNOWN: "unknown",
    PlatformStopCode.IMAGE_PULL_FAILED: "image pull failed",
}


class KernelStopReason(IntEnum):
    """The reason byte of a kernel stop code: what made the kernel stop."""

    #: The kernel shut down as asked.
    OK = 0
    #: An assertion failed.
    EXP = 1
    #: An arithmetic error, such as a division by zero.
    MATH = 2
    #: An invalid instruction.
    INVLOP = 3
    #: A page fault; the errno says which kind.
    PGFAULT = 4
    #: A segmentation fault.
    SEGFAULT = 5
    #: A hardware error.
    HWERR = 6
    #: A security violation.
    SECERR = 7


#: How each kernel stop reason reads.
_KERNEL_REASONS = {
    KernelStopReason.OK: "",
    KernelStopReason.EXP: "assertion error",
    KernelStopReason.MATH: "arithmetic error",
    KernelStopReason.INVLOP: "instruction error",
    KernelStopReason.PGFAULT: "page fault",
    KernelStopReason.SEGFAULT: "segmentation fault",
    KernelStopReason.HWERR: "hardware error",
    KernelStopReason.SECERR: "security violation",
}

#: The Linux errno values a page fault refines.
_ENOMEM = 12
_EFAULT = 14
_EPERM = 1


class KernelStopCode(int):
    """A kernel stop code: the errno, the init level and the reason it packs.

    The kernel packs several details into the API's ``stop_code``: the reason
    in the low byte, the init level and the shutdown table above it, and the
    application's errno above those, using Linux's ``errno.h`` values.
    """

    @property
    def reason(self) -> int:
        """The reason byte; :class:`KernelStopReason` names the known values."""
        return int(self) & 0xFF

    @property
    def reason_name(self) -> str:
        """The reason's name, e.g. ``PGFAULT``, or ``reason(N)`` for one not known here."""
        try:
            return KernelStopReason(self.reason).name
        except ValueError:
            return f"reason({self.reason})"

    @property
    def init_level(self) -> int:
        """The init level the kernel was at when it stopped."""
        return (int(self) >> 8) & 0x7F

    @property
    def shutdown_table(self) -> int:
        """Where the shutdown came from: ``0`` for the inittable, ``1`` for the termtable."""
        return (int(self) >> 15) & 0x1

    @property
    def errno(self) -> int:
        """The application's errno, or ``0`` for none."""
        return (int(self) >> 16) & 0xFF

    @property
    def errno_name(self) -> str:
        """The errno's name, e.g. ``ENOMEM``, or an empty string for none."""
        return errno_name(self.errno)

    @property
    def description(self) -> str:
        """What made the kernel stop, in words; empty for a clean shutdown."""
        reason = self.reason
        if reason == KernelStopReason.PGFAULT:
            if self.errno == _ENOMEM:
                return "out of memory"
            if self.errno in (_EFAULT, _EPERM):
                return "illegal memory access"
        try:
            return _KERNEL_REASONS[KernelStopReason(reason)]
        except ValueError:
            return "unexpected error"

    def __str__(self) -> str:
        text = self.description
        name = self.errno_name
        return f"{text} ({name})" if name else text

    def __repr__(self) -> str:
        return f"{type(self).__name__}({int(self)})"


@dataclass(frozen=True)
class Stop:
    """Why an instance stopped: the API's ``stop_reason`` and ``stop_code``, decoded.

    ``str()`` reads the way the CLI reports a stop, e.g. ``platform stop: image
    pull failed`` or ``kernel crash: out of memory (ENOMEM)``.
    """

    #: Who initiated the stop.
    reason: StopReason
    #: The code left behind, when there is one; its meaning depends on the reason.
    code: int | None = None

    @property
    def platform_code(self) -> PlatformStopCode | None:
        """The platform's code, for a stop the platform alone initiated."""
        if self.code is None or self.reason != StopReason.PLATFORM:
            return None
        return PlatformStopCode(self.code)

    @property
    def kernel_code(self) -> KernelStopCode | None:
        """The kernel's code, for a stop the kernel took part in."""
        if self.code is None or not self.reason & StopReason.KERNEL:
            return None
        return KernelStopCode(self.code)

    def __str__(self) -> str:
        detail = ""
        if self.code is not None:
            platform, kernel = self.platform_code, self.kernel_code
            if platform is not None:
                detail = str(platform)
            elif kernel is not None:
                detail = str(kernel)
            else:
                detail = f"code({self.code})"
        text = str(self.reason)
        return f"{text}: {detail}" if detail else text


def errno_name(errno: int) -> str:
    """The name of a Linux errno, e.g. ``ENOMEM``; ``errno(N)`` for an unknown one.

    Zero is no error, and reads as an empty string.
    """
    if errno == 0:
        return ""
    return _ERRNO_NAMES.get(errno, f"errno({errno})")


#: Linux errno values by name, since the kernel uses Linux's numbering whatever
#: this SDK runs on.
_ERRNO_NAMES: dict[int, str] = {
    1: "EPERM",
    2: "ENOENT",
    3: "ESRCH",
    4: "EINTR",
    5: "EIO",
    6: "ENXIO",
    7: "E2BIG",
    8: "ENOEXEC",
    9: "EBADF",
    10: "ECHILD",
    11: "EAGAIN",
    12: "ENOMEM",
    13: "EACCES",
    14: "EFAULT",
    15: "ENOTBLK",
    16: "EBUSY",
    17: "EEXIST",
    18: "EXDEV",
    19: "ENODEV",
    20: "ENOTDIR",
    21: "EISDIR",
    22: "EINVAL",
    23: "ENFILE",
    24: "EMFILE",
    25: "ENOTTY",
    26: "ETXTBSY",
    27: "EFBIG",
    28: "ENOSPC",
    29: "ESPIPE",
    30: "EROFS",
    31: "EMLINK",
    32: "EPIPE",
    33: "EDOM",
    34: "ERANGE",
    35: "EDEADLOCK",
    36: "ENAMETOOLONG",
    37: "ENOLCK",
    38: "ENOSYS",
    39: "ENOTEMPTY",
    40: "ELOOP",
    42: "ENOMSG",
    43: "EIDRM",
    44: "ECHRNG",
    45: "EL2NSYNC",
    46: "EL3HLT",
    47: "EL3RST",
    48: "ELNRNG",
    49: "EUNATCH",
    50: "ENOCSI",
    51: "EL2HLT",
    52: "EBADE",
    53: "EBADR",
    54: "EXFULL",
    55: "ENOANO",
    56: "EBADRQC",
    57: "EBADSLT",
    59: "EBFONT",
    60: "ENOSTR",
    61: "ENODATA",
    62: "ETIME",
    63: "ENOSR",
    64: "ENONET",
    65: "ENOPKG",
    66: "EREMOTE",
    67: "ENOLINK",
    68: "EADV",
    69: "ESRMNT",
    70: "ECOMM",
    71: "EPROTO",
    72: "EMULTIHOP",
    73: "EDOTDOT",
    74: "EBADMSG",
    75: "EOVERFLOW",
    76: "ENOTUNIQ",
    77: "EBADFD",
    78: "EREMCHG",
    79: "ELIBACC",
    80: "ELIBBAD",
    81: "ELIBSCN",
    82: "ELIBMAX",
    83: "ELIBEXEC",
    84: "EILSEQ",
    85: "ERESTART",
    86: "ESTRPIPE",
    87: "EUSERS",
    88: "ENOTSOCK",
    89: "EDESTADDRREQ",
    90: "EMSGSIZE",
    91: "EPROTOTYPE",
    92: "ENOPROTOOPT",
    93: "EPROTONOSUPPORT",
    94: "ESOCKTNOSUPPORT",
    95: "ENOTSUP",
    96: "EPFNOSUPPORT",
    97: "EAFNOSUPPORT",
    98: "EADDRINUSE",
    99: "EADDRNOTAVAIL",
    100: "ENETDOWN",
    101: "ENETUNREACH",
    102: "ENETRESET",
    103: "ECONNABORTED",
    104: "ECONNRESET",
    105: "ENOBUFS",
    106: "EISCONN",
    107: "ENOTCONN",
    108: "ESHUTDOWN",
    109: "ETOOMANYREFS",
    110: "ETIMEDOUT",
    111: "ECONNREFUSED",
    112: "EHOSTDOWN",
    113: "EHOSTUNREACH",
    114: "EALREADY",
    115: "EINPROGRESS",
    116: "ESTALE",
    117: "EUCLEAN",
    118: "ENOTNAM",
    119: "ENAVAIL",
    120: "EISNAM",
    121: "EREMOTEIO",
    122: "EDQUOT",
    123: "ENOMEDIUM",
    124: "EMEDIUMTYPE",
    125: "ECANCELED",
    126: "ENOKEY",
    127: "EKEYEXPIRED",
    128: "EKEYREVOKED",
    129: "EKEYREJECTED",
    130: "EOWNERDEAD",
    131: "ENOTRECOVERABLE",
    132: "ERFKILL",
    133: "EHWPOISON",
}
