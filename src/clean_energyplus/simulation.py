"""It would be nice to be able to use energyplus through some familiar reset &
step API. However, energyplus was not made for this. This module implements all
the code glue needed to make the .step function work.

Note, however, that at this point, the concept of a reward doesn't exist yet.
This module only cares about control.

"""

import pyenergyplus.api
import threading
import clean_energyplus.template as template
import collections
from dataclasses import dataclass
import typing
import queue
import pathlib
import traceback

_api = pyenergyplus.api.EnergyPlusAPI()


@dataclass
class _StepResult:
    observation: typing.Any
    finished: bool


@dataclass
class _DoneResult:
    exit_code: int


@dataclass
class _ExceptionResult:
    tb: traceback.TracebackException
    exn: Exception


_Result = typing.Union[_StepResult, _DoneResult, _ExceptionResult]


@dataclass
class VariableHole:

    inner: typing.Any


@dataclass
class ActuatorHole:
    inner: typing.Any


@dataclass
class MeterHole:
    """Works like variable, but inner contains only a str."""

    inner: typing.Any


@dataclass
class FunctionHole:
    """Function(f) will be replaced by f(state) at each timestep"""

    inner: typing.Any


ActuatorThingy = collections.namedtuple(
    "ActuatorThingy",
    [
        "component_type",
        "control_type",
        "actuator_key",
    ],
)

T = typing.TypeVar("T")


class Channel(typing.Generic[T]):
    """Since we are running the Energyplus simulation in a different thread, we
    need a mechanism for the user thread (the one in which the user might
    presumably run their policy and the .step function) to exchange actuator
    values sensor values. Moreover, this communication mechanism must act as a
    rendezvous point: a chan.put() must return only if a chan.get() has been
    executed on the other thread.

    """

    q: queue.Queue[queue.Queue[T]]

    def __init__(self):
        self.q = queue.Queue()

    def put(self, v: T) -> None:

        wait_q = self.q.get()
        wait_q.put(v)

    def get(self) -> T:
        wait_q: queue.Queue[T] = queue.Queue()
        self.q.put(wait_q)

        return wait_q.get()


class EnergyPlusSimulation:

    """"""

    """A PyTree containing `Variable` and `Meter` leaves."""
    observation_template: typing.Any = None

    """ A PyTree of the same shape, but containing the associated handles"""
    observation_handles: typing.Any = None

    obs_chan: Channel
    act_chan: Channel

    building_file: typing.Union[str, pathlib.Path]
    weather_file: typing.Union[str, pathlib.Path]

    max_steps: int

    actuators: typing.Dict[str, ActuatorThingy]

    log_dir: str

    def __init__(
        self,
        building: str,
        weather: str,
        observation_template: typing.Any,
        actuators: typing.Dict[str, ActuatorThingy],
        max_steps=10_000,
        log_dir: str = "eplus_output",
    ):
        self.obs_chan = Channel()
        self.act_chan = Channel()

        self.done = False

        self.building_file = building
        self.weather_file = weather
        self.observation_template = observation_template
        self.actuators = actuators
        self.max_steps = max_steps
        self.n_steps = 0
        self.log_dir = log_dir

    def callback_timestep(self, state: int) -> None:
        # print("running one timestep...")
        try:

            api_ready = _api.exchange.api_data_fully_ready(state)
            if not api_ready:
                return

            if _api.exchange.warmup_flag(state):
                return

            if self.observation_handles is None:
                self.construct_handles()

            # We replace each Variable handle by its value,
            var_replaced = template.search_replace(
                self.observation_handles,
                VariableHole,
                lambda han: _api.exchange.get_variable_value(state, han.inner),
            )
            # then each Meter handle by its value
            meter_replaced = template.search_replace(
                var_replaced,
                MeterHole,
                lambda han: _api.exchange.get_meter_value(state, han.inner),
            )

            # then each Actuator by its value
            actuator_replaced = template.search_replace(
                meter_replaced,
                ActuatorHole,
                lambda han: _api.exchange.get_actuator_value(state, han.inner),
            )
            # and finally, each Function(f) by Function(inner=f(state))
            function_replaced = template.search_replace(
                actuator_replaced,
                FunctionHole,
                lambda fn: fn.inner(self.state),
            )
            obs = function_replaced
            # Here, we assume `variable_handles` takes the shape of a dict
            # which might not be the case.

            if not (self.n_steps < self.max_steps):
                _api.runtime.stop_simulation(self.state)
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
            if type(act) != dict:
                return

            # And we send the simulation the actuator values
            for k, v in act.items():
                _api.exchange.set_actuator_value(state, self.actuator_handles[k], v)

            self.n_steps += 1

        except Exception as e:
            _api.runtime.stop_simulation(self.state)
            raise e

    def construct_handles(self) -> None:
        try:
            # Most of Variable, Meter, Actuator need to be converted (by a
            # running simulation) into a not-so-human-readable numerical handle.
            # This is what we do here.

            def var_handle(var):
                han = _api.exchange.get_variable_handle(self.state, *var)
                assert han >= 0, f"invalid variable: {var}"
                return han

            with_variable_handles = template.search_replace(
                var_handle,
                self.observation_template,
                VariableHole,
            )

            def meter_handle(met):
                han = _api.exchange.get_meter_handle(self.state, met)
                assert han >= 0, f"invalid meter: {met}"
                return han

            with_meter_handles = template.search_replace(
                meter_handle,
                with_variable_handles,
                MeterHole,
            )

            def actuator_handle(act):
                han = _api.exchange.get_actuator_handle(self.state, *act)
                assert han >= 0, f"invalid actuator: {act}"
                return han

            with_actuator_handles = template.search_replace(
                actuator_handle,
                with_meter_handles,
                ActuatorHole,
            )
            self.observation_handles = with_actuator_handles

            self.actuator_handles = {}
            for k, act in self.actuators.items():
                self.actuator_handles[k] = actuator_handle(act)

        except Exception as e:
            _api.runtime.stop_simulation(self.state)
            raise e

    def start(self) -> typing.Any:
        state = _api.state_manager.new_state()
        self.state = state

        def eplus_thread():
            """Thread running the energyplus simulation."""
            exit_code = None
            try:
                exit_code = _api.runtime.run_energyplus(
                    self.state,
                    [
                        "-d",
                        self.log_dir,
                        "-w",
                        self.weather_file,
                        self.building_file,
                    ],
                )
                print(f"energyplus exited with code {exit_code}")
                self.obs_chan.put(_DoneResult(exit_code))
            except Exception as e:
                tb_exc = traceback.TracebackException.from_exception(e)
                self.obs_chan.put(_ExceptionResult(tb_exc, e))
            finally:
                _api.state_manager.delete_state(state)
                del self.state
                print(f"freed E+ memory")
                self.done = True

        # Like forEach
        template.search_replace(
            lambda var: _api.exchange.request_variable(self.state, *var),
            self.observation_template,
            VariableHole,
        )

        _api.runtime.callback_begin_system_timestep_before_predictor(
            self.state, self.callback_timestep
        )

        self.thread = threading.Thread(target=eplus_thread, daemon=True)
        self.thread.start()

        return self._get_obs_and_filter()

    def _filter(self, result: _Result) -> typing.Tuple[typing.Any, bool]:
        if type(result) == _StepResult:
            return (result.observation, result.finished)
        elif type(result) == _DoneResult:
            if result.exit_code != 0:
                raise Exception(
                    "energyplus exited with an error. See the eplusout.err file"
                )
            else:
                return ({}, True)
        elif type(result) == _ExceptionResult:
            # print("Original traceback from energyplus thread:")
            # for line in result.tb.format(chain=True):
            #     print(line, end="")

            raise result.exn
        else:
            raise Exception(
                "this channel should receive only a `StepResult` or a `DoneResult`."
            )

    def _get_obs_and_filter(self) -> typing.Tuple[typing.Any, bool]:
        assert not self.done, "This simulation is done. Create another one."
        return self._filter(self.obs_chan.get())

    def step(self, action: typing.Dict[str, float]) -> typing.Tuple[typing.Any, bool]:
        assert not self.done, "This simulation is done. Create another one."
        self.act_chan.put(action)
        return self._get_obs_and_filter()

    def get_api_endpoints(self):
        exchange_points = _api.exchange.get_api_data(self.state)

        def extract(v):
            return [v.key, v.name, v.type, v.what]

        t = list(map(extract, exchange_points))
        return t
