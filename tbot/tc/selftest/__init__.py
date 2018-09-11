import typing
import tbot
from tbot.machine import linux

from tbot import tc

from .path import *  # noqa: F403
from .machine import *  # noqa: F403


@tbot.testcase
def selftest_uname(lab: typing.Optional[linux.LabHost] = None,) -> None:
    with lab or tbot.acquire_lab() as lh:
        lh.exec0("uname", "-a")


@tbot.testcase
def selftest_user(lab: typing.Optional[linux.LabHost] = None,) -> None:
    with lab or tbot.acquire_lab() as lh:
        lh.exec0("echo", linux.Env("USER"))


@tbot.testcase
def selftest(lab: typing.Optional[linux.LabHost] = None,) -> None:
    with lab or tbot.acquire_lab() as lh:
        tc.testsuite(
            selftest_machine_reentrant,  # noqa: F405
            selftest_machine_labhost_shell,  # noqa: F405
            selftest_path_stat,  # noqa: F405
            selftest_path_integrity,  # noqa: F405
            lab=lh,
        )