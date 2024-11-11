import clean_energyplus.simulation as simulation
import clean_energyplus.environment as environment
from clean_energyplus.data.building import crawlspace
from clean_energyplus.data.weather import honolulu

import gymnasium
import numpy as np


def test_environment() -> None:
    def make_energyplus():
        return simulation.EnergyPlusSimulation(
            crawlspace,
            honolulu,
            None,
            {},
            max_steps=100,
        )

    empty_space = gymnasium.spaces.Box(
        low=np.array([]), high=np.array([]), shape=(0,), dtype=np.float32
    )

    env = environment.EnergyPlusEnvironment(
        make_energyplus,
        lambda _: 0.0,
        empty_space,
        lambda _: np.array([]),
        empty_space,
        lambda _: {},
    )

    obs, _ = env.reset()
    done = False
    while not done:
        obs, reward, done, _, _ = env.step(np.array([]))
