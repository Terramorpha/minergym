import clean_energyplus.simulation as simulation
from importlib import resources
import pathlib

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

    done = False
    _ = sim.start()
    while not done:
        _, done = sim.step({})
    while not done:
        _, done = sim.step({})
