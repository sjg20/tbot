"""
TBot
----
"""
import time
import typing
import traceback
import enforce

from tbot import log  # noqa: F401
from tbot import log_events  # noqa: F401
from tbot import tc  # noqa: F401
import tbot.machine
import tbot.config

from tbot.testcase_collector import testcase  # noqa: F401


class TestcaseFailure(Exception):
    """
    A testcase detected an error condition

    Raise this exception if an error occured, that
    was manually detected (don't raise it in an except block,
    use the original exception there)
    """
    pass


class InvalidUsageException(Exception):
    """
    A testcase/utility was invoked with incorrect arguments

    Raise this exception if your testcase was called with incorrect
    parameters (=programmer error). Preferably ensure correct calling
    by using type annotations.
    """
    pass


# pylint: disable=too-many-instance-attributes
class TBot:
    """
    Main class of TBot, you usually do not need to instanciate this yourself

    :param tbot.config.Config config: A configuration to be used
    :param dict testcases: Testcases available to this instance
    :param bool new: Whether this is a new instance that should create a noenv machine.
        Always ``True`` unless you know what you are doing.
    :ivar config: :class:`tbot.config.Config()`
    :ivar testcases: All available testcases
    :ivar machines: All available machines :class:`tbot.machine.machine.MachineManager()`
    """

    def __init__(
        self,
        config: tbot.config.Config,
        testcases: dict,
        new: bool = True,
        interactive: bool = False,
    ) -> None:
        self.config = config
        self.testcases = testcases
        self.layer = 0
        self.interactive = interactive
        self._old_inst: typing.Optional[TBot] = None

        self.destruct_machines: typing.List[tbot.machine.Machine] = list()

        if new:
            self.machines = tbot.machine.MachineManager(self)

            labhost = tbot.machine.MachineLabNoEnv()
            labhost._setup(self)  # pylint: disable=protected-access
            self.machines[labhost.common_machine_name] = labhost
            self.machines[labhost.unique_machine_name] = labhost
            self.destruct_machines.append(labhost)

    @property
    def shell(self) -> tbot.machine.Machine:
        """ The default host machine """
        return self.machines["host"]

    @property
    def boardshell(self) -> tbot.machine.MachineBoard:
        """ The default board machine """
        boardmachine = self.machines["board"]
        if not isinstance(boardmachine, tbot.machine.MachineBoard):
            raise InvalidUsageException("BoardMachine is not a 'MachineBoard'")
        return boardmachine

    def call_then(
        self, tcs: typing.Union[str, typing.Callable], **kwargs: typing.Any
    ) -> typing.Callable:
        """
        Decorator to call a testcase with a function as a payload ("and_then" argument)

        :param tcs: The testcase to call
        :type tcs: str or typing.Callable
        :param dict kwargs: Additional arguments for the testcase
        :returns: The decorated function
        :rtype: typing.Callable
        """

        def _decorator(f: typing.Callable) -> typing.Any:
            kwargs["and_then"] = f
            self.call(tcs, **kwargs)
            return f

        return _decorator

    def call(
        self,
        tcs: typing.Union[str, typing.Callable],
        *,
        fail_ok: bool = False,
        doc: bool = True,
        **kwargs: typing.Any,
    ) -> typing.Any:
        """
        Call a testcase

        :param tcs: The testcase to be called. Can either be a string or a callable
        :type tcs: str or typing.Callable
        :param bool fail_ok: Whether a failure in this testcase is tolerable
        :param bool doc: Whether documentation should be generated in this testcase
        :param dict kwargs: Additional arguments for the testcase
        :returns: The return value from the testcase
        """
        name = tcs if isinstance(tcs, str) else f"@{tcs.__name__}"
        tbot.log_events.testcase_begin(name)
        self.layer += 1
        tbot.log.set_layer(self.layer)
        previous_doc = tbot.log.LOG_DO_DOC
        tbot.log.LOG_DO_DOC = previous_doc and doc
        start_time = time.monotonic()

        try:
            if isinstance(tcs, str):
                retval = self.testcases[tcs](self, **kwargs)
            else:
                retval = enforce.runtime_validation(tcs)(self, **kwargs)
        except Exception as e:  # pylint: disable=broad-except
            # Cleanup is done by "with" handler __exit__
            # A small hack to ensure, the exception is only added once:
            if "__tbot_exc_catched" not in e.__dict__:
                exc_name = type(e).__module__ + "." + type(e).__qualname__
                tbot.log_events.exception(exc_name, traceback.format_exc())
                e.__dict__["__tbot_exc_catched"] = True
            self.layer -= 1
            run_duration = time.monotonic() - start_time
            tbot.log_events.testcase_end(name, run_duration, False, fail_ok)
            tbot.log.set_layer(self.layer)
            tbot.log.LOG_DO_DOC = previous_doc
            raise

        self.layer -= 1
        run_duration = time.monotonic() - start_time
        tbot.log_events.testcase_end(name, run_duration, True)
        tbot.log.set_layer(self.layer)
        tbot.log.LOG_DO_DOC = previous_doc
        return retval

    def machine(self, mach: tbot.machine.Machine) -> "TBot":
        """
        Create a new TBot instance with a new machine

        :param tbot.machine.machine.Machine mach: The machine to be added in the new instance
        :returns: The new TBot instance, which has to be used inside a with
            statement
        :rtype: TBot
        """
        new_inst = TBot(
            self.config, self.testcases, False, interactive=self.interactive
        )
        new_inst.layer = self.layer
        new_inst.machines = tbot.machine.MachineManager(
            new_inst, self.machines.connection
        )

        for machine_name in self.machines.keys():
            new_inst.machines[machine_name] = self.machines[machine_name]

        old_mach = (
            new_inst.machines[mach.common_machine_name]
            if mach.common_machine_name in new_inst.machines
            else None
        )
        new_mach = mach._setup(new_inst, old_mach)  # pylint: disable=protected-access
        new_inst.machines[mach.common_machine_name] = new_mach
        new_inst.machines[mach.unique_machine_name] = new_mach
        if new_mach is not old_mach:
            new_inst.destruct_machines.append(new_mach)

        new_inst._old_inst = self
        return new_inst

    def with_board_uboot(self) -> "TBot":
        """
        Shortcut to create a new TBot instance with a U-Boot boardmachine

        :returns: The new TBot instance, which has to be used inside a with
            statement
        :rtype: TBot
        """
        return self.machine(tbot.machine.MachineBoardUBoot())

    def with_board_linux(self) -> "TBot":
        """
        Shortcut to create a new TBot instance with a Linux boardmachine

        :returns: The new TBot instance, which has to be used inside a with
            statement
        :rtype: TBot
        """
        return self.machine(tbot.machine.MachineBoardLinux())

    def __enter__(self) -> "TBot":
        return self

    def destruct(self) -> None:
        """
        Destruct this TBot instance and all associated machines. This
        method will be called automatically when exiting a with statement.
        """
        # Make sure logfile is written
        tbot.log.flush_log()
        # Destruct all machines that need to be destructed
        for mach in self.destruct_machines:
            # pylint: disable=protected-access
            mach._destruct(self)
        # Make sure, we don't destruct twice
        self.destruct_machines = []

    def __exit__(
        self, exc_type: typing.Any, exc_value: typing.Any, trceback: typing.Any
    ) -> None:
        self.destruct()
        # Hack to make this TBot behave like it's parent after the end of a with
        # statement
        if self._old_inst is not None:
            self.machines = self._old_inst.machines
            self.destruct_machines = self._old_inst.destruct_machines