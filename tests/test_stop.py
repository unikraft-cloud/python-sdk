# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Unikraft GmbH. All rights reserved.
#
# Decoding why an instance stopped: the reason bitmask, the platform's and the
# kernel's codes, and how the three read together.

from __future__ import annotations

import pytest

from unikraft_cloud import (
    Instance,
    KernelStopCode,
    KernelStopReason,
    PlatformStopCode,
    Stop,
    StopReason,
)
from unikraft_cloud.resources.stop import errno_name

from .conftest import instance

ENOMEM, EFAULT = 12, 14


def kernel_code(
    reason: int, *, errno: int = 0, init_level: int = 0, termtable: bool = False
) -> int:
    """Pack a kernel stop code the way the kernel does."""
    return (errno << 16) | (int(termtable) << 15) | (init_level << 8) | reason


class TestStopReason:
    @pytest.mark.parametrize(
        ("value", "text", "flags", "origin"),
        [
            (0, "unknown stop", "-----", "unknown"),
            (1, "kernel crash", "----K", "kernel"),
            (3, "app exit", "---AK", "app"),
            (7, "platform shutdown", "--PAK", "platform"),
            (13, "user shutdown incomplete", "-UP-K", "user"),
            (15, "user shutdown complete", "-UPAK", "user"),
            (28, "forced user shutdown", "FUP--", "user"),
        ],
    )
    def test_names_the_documented_scenarios(
        self, value: int, text: str, flags: str, origin: str
    ) -> None:
        reason = StopReason(value)
        assert (str(reason), reason.flags, reason.origin) == (text, flags, origin)

    def test_describes_an_undocumented_combination_by_its_origin(self) -> None:
        assert str(StopReason(4)) == "platform stop"
        assert str(StopReason.FORCED | StopReason.PLATFORM) == "forced platform stop"
        assert str(StopReason.FORCED) == "unknown stop"

    def test_keeps_bits_it_does_not_know(self) -> None:
        reason = StopReason(32 | 1)
        assert reason & StopReason.KERNEL
        assert reason.origin == "kernel"

    def test_formats_by_name_unless_a_number_format_is_asked_for(self) -> None:
        reason = StopReason.PLATFORM_SHUTDOWN
        assert f"{reason}" == "platform shutdown"
        assert f"{reason:>20}" == "   platform shutdown"
        assert f"{reason:d}" == "7"
        assert f"{reason:#x}" == "0x7"

    def test_forced_is_the_top_bit(self) -> None:
        assert StopReason.FORCED_USER_SHUTDOWN.forced
        assert not StopReason.USER_SHUTDOWN_COMPLETE.forced


class TestPlatformStopCode:
    def test_names_a_failed_image_pull(self) -> None:
        code = PlatformStopCode(1)
        assert code == PlatformStopCode.IMAGE_PULL_FAILED
        assert str(code) == "image pull failed"
        assert str(PlatformStopCode(0)) == "unknown"

    def test_carries_a_code_it_does_not_know(self) -> None:
        assert str(PlatformStopCode(9)) == "code(9)"
        assert repr(PlatformStopCode(9)) == "PlatformStopCode(9)"


class TestKernelStopCode:
    def test_unpacks_every_field(self) -> None:
        code = KernelStopCode(kernel_code(4, errno=ENOMEM, init_level=5, termtable=True))
        assert (code.reason, code.errno, code.init_level, code.shutdown_table) == (4, ENOMEM, 5, 1)
        assert code.reason == KernelStopReason.PGFAULT
        assert (code.reason_name, code.errno_name) == ("PGFAULT", "ENOMEM")

    def test_reads_the_spec_example(self) -> None:
        # A clean shutdown from the termtable at init level 1, no errno.
        code = KernelStopCode(33024)
        assert (code.reason, code.init_level, code.shutdown_table, code.errno) == (0, 1, 1, 0)
        assert str(code) == ""

    @pytest.mark.parametrize(
        ("packed", "text"),
        [
            (kernel_code(4, errno=ENOMEM), "out of memory (ENOMEM)"),
            (kernel_code(4, errno=EFAULT), "illegal memory access (EFAULT)"),
            (kernel_code(4), "page fault"),
            (kernel_code(1), "assertion error"),
            (kernel_code(2), "arithmetic error"),
            (kernel_code(3), "instruction error"),
            (kernel_code(5), "segmentation fault"),
            (kernel_code(6), "hardware error"),
            (kernel_code(7), "security violation"),
            (kernel_code(9, errno=200), "unexpected error (errno(200))"),
        ],
    )
    def test_describes_the_reason_and_the_errno(self, packed: int, text: str) -> None:
        assert str(KernelStopCode(packed)) == text

    def test_names_an_unknown_reason_by_number(self) -> None:
        assert KernelStopCode(kernel_code(9)).reason_name == "reason(9)"

    def test_errno_names_are_linux_values(self) -> None:
        assert (errno_name(0), errno_name(16), errno_name(133)) == ("", "EBUSY", "EHWPOISON")
        assert errno_name(250) == "errno(250)"


class TestStop:
    def test_a_platform_stop_carries_the_platforms_code(self) -> None:
        stop = Stop(StopReason.PLATFORM, 1)
        assert stop.platform_code == PlatformStopCode.IMAGE_PULL_FAILED
        assert stop.kernel_code is None
        assert str(stop) == "platform stop: image pull failed"

    def test_a_kernel_stop_carries_the_kernels_code(self) -> None:
        stop = Stop(StopReason.KERNEL_CRASH, kernel_code(4, errno=ENOMEM))
        assert stop.platform_code is None
        assert stop.kernel_code is not None and stop.kernel_code.errno == ENOMEM
        assert str(stop) == "kernel crash: out of memory (ENOMEM)"

    def test_a_clean_exit_reads_as_the_reason_alone(self) -> None:
        assert str(Stop(StopReason.APP_EXIT, 0)) == "app exit"
        assert str(Stop(StopReason.FORCED_USER_SHUTDOWN)) == "forced user shutdown"

    def test_a_code_with_no_owner_is_shown_raw(self) -> None:
        assert str(Stop(StopReason.USER | StopReason.PLATFORM, 3)) == "user stop: code(3)"


class TestInstanceStop:
    def test_an_instance_decodes_its_own_stop(self) -> None:
        stopped = Instance.model_validate(
            {**instance(state="stopped", stop_reason=4, stop_code=1), "metro": "fra"}
        )
        assert stopped.stop == Stop(StopReason.PLATFORM, 1)
        assert stopped.describe_stop() == "platform stop: image pull failed"

    def test_a_running_instance_has_no_stop(self) -> None:
        running = Instance.model_validate({**instance(), "metro": "fra"})
        assert running.stop is None
        assert running.describe_stop() == ""
