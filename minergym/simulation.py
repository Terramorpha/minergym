"""It would be nice to be able to use energyplus through some familiar reset &
step API. However, energyplus was not made for this. This module implements all
the code glue needed to make the .step function work.

Note, however, that at this point, the concept of a reward doesn't exist yet.
This module only cares about control.

"""

import pyenergyplus.api
import threading
import collections
from dataclasses import dataclass, field
import typing
import queue
import pathlib
import traceback
import optree
from pathlib import Path
from ctypes import c_void_p

api = pyenergyplus.api.EnergyPlusAPI()


class SimulationCrashed(Exception):
    pass


@dataclass(frozen=True, slots=True)
class _StepResult:
    observation: typing.Any
    finished: bool


@dataclass(frozen=True, slots=True)
class _DoneResult:
    exit_code: int


@dataclass(frozen=True, slots=True)
class _ExceptionResult:
    tb: traceback.TracebackException
    exn: Exception


_Result = typing.Union[_StepResult, _DoneResult, _ExceptionResult]


@dataclass(frozen=True, slots=True)
class VariableHole:
    variable_name: str
    variable_key: str


@dataclass(frozen=True, slots=True)
class VariableHandle:
    handle: int


class InvalidVariable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ActuatorHole:
    component_type: str
    control_type: str
    actuator_key: str


@dataclass(frozen=True, slots=True)
class ActuatorHandle:
    handle: int


class InvalidActuator(Exception):
    pass


@dataclass(frozen=True, slots=True)
class MeterHole:
    meter_name: str


@dataclass(frozen=True, slots=True)
class MeterHandle:
    handle: int


class InvalidMeter(Exception):
    pass


@dataclass(frozen=True, slots=True)
class FunctionHole:
    function: typing.Callable[[c_void_p], typing.Any]


T = typing.TypeVar("T")


class Channel(typing.Generic[T]):
    """Since we are running the Energyplus simulation in a different thread, we
    need a mechanism for the user thread (the one in which the user might
    presumably run their policy and the .step function) to exchange actuator
    values sensor values. Moreover, this communication mechanism must act as a
    rendezvous point: a chan.put() must return only if a chan.get() has been
    executed on the other thread.

    """

    _q: queue.Queue[queue.Queue[T]]
    _closed: bool

    def __init__(self):
        self.q = queue.Queue()
        self.closed = False

    def put(self, v: T) -> None:
        assert not self.closed

        wait_q = self.q.get()
        wait_q.put(v)

    def get(self) -> T:
        assert not self.closed
        wait_q: queue.Queue[T] = queue.Queue()
        self.q.put(wait_q)

        return wait_q.get()

    def close(self) -> None:
        """Close the channel. In python 3.13, we will be able to call
        .shutdown() on a queue, which will remove the possible race condition
        that happens when .close() is run at the same time as .put() or .get().
        """

        assert not self.closed
        self.closed = True


# types for things

_AnyHandle = VariableHandle | MeterHandle | ActuatorHandle | FunctionHole
_AnyHole = VariableHole | MeterHole | ActuatorHole | FunctionHole

@dataclass(slots=True)
class EnergyPlusSimulation:

    """"""

    """The building file used for the simulation."""
    building_path: Path

    """The weather file used for the simulation."""
    weather_path: Path

    """A PyTree containing `Variable` and `Meter` leaves."""
    observation_template: typing.Any

    actuators: typing.Dict[str, ActuatorHole]

    """ A PyTree of the same shape, but containing the associated handles."""
    observation_handles: typing.Any = None

    number_of_warmup_phases_completed: int = 0

    warmup_phases: int = 5

    n_steps: int = field(default=0, init=False)

    """The amount of steps before the simulation exits."""
    max_steps: int = 10_000

    """The directory in which energyplus will write its log files."""
    log_dir: Path = Path("eplus_output")

    """Wether to let energyplus print a bunch of stuff to stdout."""
    verbose: bool = True

    actuator_handles: typing.Dict[str, int] = field(default_factory=dict)

    obs_chan: Channel = field(default_factory=Channel)
    act_chan: Channel = field(default_factory=Channel)

    state: typing.Union[None, c_void_p] = field(default=None, init=False)

    def callback_timestep(self, state: c_void_p) -> None:
        try:

            if not api.exchange.api_data_fully_ready(state):
                return

            if api.exchange.warmup_flag(state):
                return

            # The energyplus simulator has 5 warmup phases. If we start
            # evaluating setpoints and sending observations before all the
            # warmup phases are all done, the policy will see the date jump
            # around, which is bad.
            if self.number_of_warmup_phases_completed < self.warmup_phases:
                return

            if self.observation_handles is None:
                self.construct_handles(state)

            def get_handle_value(han : _AnyHandle) -> float:
                if isinstance(han, VariableHandle):
                    return api.exchange.get_variable_value(state, han.handle)
                elif isinstance(han, MeterHandle):
                    return api.exchange.get_meter_value(state, han.handle)
                elif isinstance(han, ActuatorHandle):
                    return api.exchange.get_actuator_value(state, han.handle)
                elif isinstance(han, FunctionHole):
                    result = han.function(state)
                    return result
                else:
                    raise Exception(f"got a weird thing: {han}")

            obs = optree.tree_map(get_handle_value, self.observation_handles)

            if not (self.n_steps < self.max_steps):
                api.runtime.stop_simulation(state)
                return
            self.obs_chan.put(
                _StepResult(
                    observation=obs,
                    finished=False,
                )
            )

            # TODO: explain why this is here
            # In case of early return, because after receiving a StopStep
            # signal, the caller will not give other actuator values to set.
            act = self.act_chan.get()
            if not isinstance(act, dict):
                return

            # And we send the simulation the actuator values
            for k, v in act.items():
                api.exchange.set_actuator_value(state, self.actuator_handles[k], v)

            self.n_steps += 1

        except Exception as e:
            api.runtime.stop_simulation(state)
            tb_exc = traceback.TracebackException.from_exception(e)
            self.obs_chan.put(_ExceptionResult(tb_exc, e))

    def construct_handles(self, state: c_void_p) -> None:
        if self.verbose:
            print("constructing handles")

        # Most of Variable, Meter, Actuator need to be converted (by a
        # running simulation) into a not-so-human-readable numerical handle.
        # This is what we do here.

        def get_hole_handle(o: _AnyHole) -> _AnyHandle:
            if isinstance(o, VariableHole):
                var = o
                han = api.exchange.get_variable_handle(
                    state,
                    var.variable_name,
                    var.variable_key,
                )
                if han < 0:
                    raise InvalidVariable(var)
                return VariableHandle(han)
            elif isinstance(o, MeterHole):
                met = o
                han = api.exchange.get_meter_handle(state, met.meter_name)
                if han < 0:
                    raise InvalidMeter(met)
                return MeterHandle(han)
            elif isinstance(o, ActuatorHole):
                act = o
                han = api.exchange.get_actuator_handle(
                    state,
                    act.component_type,
                    act.control_type,
                    act.actuator_key,
                )
                if han < 0:
                    raise InvalidActuator(act)
                return ActuatorHandle(han)
            elif isinstance(o, FunctionHole):
                # We don't need to turn it into anything else.
                return o
            else:
                raise Exception(f"got a weird thing: {o}")

        self.observation_handles = optree.tree_map(
            get_hole_handle,
            self.observation_template,
        )

        for k, act in self.actuators.items():
            han = api.exchange.get_actuator_handle(
                state, act.component_type, act.control_type, act.actuator_key
            )
            self.actuator_handles[k] = han

    def start(self) -> typing.Tuple[typing.Any, bool]:
        state = api.state_manager.new_state()
        self.state = state

        def eplus_thread():
            """Thread running the energyplus simulation."""
            exit_code = None
            try:

                args: list[str] = [
                    "-d",
                    str(self.log_dir),
                    "-w",
                    str(self.weather_path),
                    str(self.building_path),
                ]
                exit_code = api.runtime.run_energyplus(
                    state,
                    args,
                )
                self.obs_chan.put(_DoneResult(exit_code))
            except Exception as e:
                tb_exc = traceback.TracebackException.from_exception(e)
                self.obs_chan.put(_ExceptionResult(tb_exc, e))
            finally:
                api.state_manager.delete_state(state)
                del self.state
                self.obs_chan.close()
                self.act_chan.close()

        # We must request access to Variable before the simulation is started.
        def request_var(var):
            if isinstance(var, VariableHole):
                api.exchange.request_variable(
                    state,
                    var.variable_name,
                    var.variable_key,
                )

        # breakpoint()
        optree.tree_map(
            request_var,
            self.observation_template,
            is_leaf=lambda x: isinstance(x, VariableHole),
        )

        api.runtime.callback_begin_system_timestep_before_predictor(
            state, self.callback_timestep
        )

        def warmup_callback(state: int):
            if self.verbose:
                print("warmup phase complete")

            self.number_of_warmup_phases_completed += 1

        api.runtime.set_console_output_status(state, self.verbose)

        api.runtime.callback_after_new_environment_warmup_complete(
            state, warmup_callback
        )

        thread = threading.Thread(target=eplus_thread, daemon=True)
        thread.start()

        return self._get_obs_and_filter()

    def _filter(self, result: _Result) -> typing.Tuple[typing.Any, bool]:
        if isinstance(result, _StepResult):
            return (result.observation, result.finished)
        elif isinstance(result, _DoneResult):
            if result.exit_code != 0:
                raise SimulationCrashed(
                    "energyplus exited with an error. See the eplusout.err file"
                )
            else:
                return ({}, True)
        elif isinstance(result, _ExceptionResult):
            raise result.exn
        else:
            raise Exception(
                "this channel should receive only a `StepResult` or a `DoneResult`."
            )

    def _get_obs_and_filter(self) -> typing.Tuple[typing.Any, bool]:
        return self._filter(self.obs_chan.get())

    def step(self, action: typing.Dict[str, float]) -> typing.Tuple[typing.Any, bool]:
        self.act_chan.put(action)
        return self._get_obs_and_filter()

    def get_api_endpoints(
        self,
    ) -> typing.List[typing.Union[ActuatorHole, VariableHole, MeterHole]]:
        exchange_points = api.exchange.get_api_data(self.state)

        out: typing.List[typing.Union[ActuatorHole, VariableHole, MeterHole]] = []
        for v in exchange_points:
            if v.what == "Actuator":
                out.append(ActuatorHole(v.name, v.type, v.key))
            elif v.what == "OutputVariable":
                out.append(VariableHole(v.name, v.key))
            elif v.what == "OutputMeter":
                out.append(MeterHole(v.key))
            elif v.what == "InternalVariable":
                continue
            else:
                raise RuntimeError("Unreachable")

        return out
