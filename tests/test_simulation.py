import clean_energyplus.simulation as simulation
from importlib import resources
import pytest


default_building = str(
    resources.files("clean_energyplus.data.building").joinpath("crawlspace.epJSON")
)
default_weather = str(
    resources.files("clean_energyplus.data.weather").joinpath("honolulu.epw")
)


def test_simulation_runs() -> None:
    sim = simulation.EnergyPlusSimulation(
        default_building, default_weather, None, {}, max_steps=100
    )

    obs, done = sim.start()
    while not done:
        assert obs is None
        obs, done = sim.step({})


def test_simulation_obs() -> None:

    obs_template = {
        "temp": simulation.VariableHole("ZONE AIR TEMPERATURE", "crawlspace")
    }

    sim = simulation.EnergyPlusSimulation(
        default_building, default_weather, obs_template, {}, max_steps=100
    )
    obs, done = sim.start()
    assert obs["temp"] != 0.0


def test_simulation_invalid_variable() -> None:

    # an invalid variable
    obs_template = simulation.VariableHole("", "")

    sim = simulation.EnergyPlusSimulation(
        default_building, default_weather, obs_template, {}, max_steps=100
    )

    with pytest.raises(simulation.InvalidVariable) as exn_info:
        obs, done = sim.start()


def test_simulation_invalid_meter() -> None:

    obs_template = simulation.MeterHole("")

    sim = simulation.EnergyPlusSimulation(
        default_building, default_weather, obs_template, {}, max_steps=100
    )

    with pytest.raises(simulation.InvalidMeter) as exn_info:
        obs, done = sim.start()
