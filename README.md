# Clean Energyplus

`clean-energyplus` aims to make it easy to create a gymnasium-compatible
environment from energyplus. Here is how to use it:

```python
import numpy as np
import gymnasium.spaces as spaces
import typing

import clean_energyplus.simulation as simulation  # Exports EnergyPlusSimulation
import clean_energyplus.config as config  # automatically generates observation_template objects
import clean_energyplus.data.building as building  # points to building files shipped with the library
import clean_energyplus.data.weather as weather  # points to weather files
import clean_energyplus.query_info as query_info  # extracts information from epJSON files
import clean_energyplus.environment as environment  # wraps a simulation into a gym environment

building_file = building.crawlspace
weather_file = weather.honolulu

obs_template = {}
rdf = query_info.rdf_from_json(building_file)
config.auto_add_time(rdf, obs_template)
config.auto_add_temperature(rdf, obs_template)
actuators = config.auto_get_actuators(rdf)

print(f"{obs_template=}") # Look at what those are!
print(f"{actuators=}")

def make_energyplus() -> simulation.EnergyPlusSimulation:
    # For a simulation to run, we need a building file,
    # a weather file, an observation template and the dict
    # of actuators we want to control.
    return simulation.EnergyPlusSimulation(
        building_file,
        weather_file,
        obs_template,
        actuators,
    )


def reward_function(obs) -> float:
    """Calculate a reward term from a "raw observation"."""
    zone_blacklist = [
        "environment",
        "attic",
        "Breezeway",
        "crawlspace",
    ]

    def penalty(min, x, max):
        if x < min:
            return min - x
        elif max < x:
            return x - max
        else:
            return 0.0

    def zone_sum(obs, min, max):
        s = 0.0
        for i, v in obs["temperature"].items():
            if i in zone_blacklist:
                continue
            s += penalty(min, v, max)
        return s

    reward = 0.0

    # Temperature reward

    if 7 <= obs["time"]["current_time"] <= 19:
        reward -= zone_sum(obs, 20, 23)
    else:
        reward -= zone_sum(obs, 15, 30)
    return reward


def to_list(obs):
    """Extract from a raw observation the values we are interested in"""
    pre_obs = [
        # temperatures
        *[v for zone, v in obs["temperature"].items()],
        # temps
        obs["time"]["current_time"],
    ]
    return pre_obs


def observation_transform(obs):
    """Extract from a raw observation the values we are interested in. Turn
    it into an array"""

    obs = np.array(to_list(obs))
    return obs


observation_mock = to_list(obs_template)
observation_space = spaces.Box(
    np.array([0.0] * len(observation_mock)),
    np.array([30.0] * len(observation_mock)),
)

action_space = spaces.Box(
    np.array([0.0, 0.0]),
    np.array([30.0, 30.0]),
)


def action_transform(act):
    """The heating setpoint acts as some kind of "lower temperature bound" on
    the environment. The policy will produce, instead of a cooling setpoint,
    cooling - heating. This means the raw actions will always be consistent
    (heating < cooling).

    """

    return {
        "heating_sch": act[0],
        "cooling_sch": act[0] + act[1],
    }


gymenv = environment.EnergyPlusEnvironment[typing.Any, typing.Any](
    make_energyplus,
    reward_function,
    observation_space,
    observation_transform,
    action_space,
    action_transform,
)
```
