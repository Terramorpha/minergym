"""To run an EnergyPlus simulation and wrap it into the neat

observation -> policy -> action -> environment -> observation

box commonly used in RL, it is necessary to have the following components:

1. A building file.
2. A weather file.
3. The set of EP variables which will be written to the observations.
4. The set of EP actuators which will be read from the action.

This module collects functions useful to creates those 4-tuples.

"""

from minergym.ontology import Ontology
import rdflib
from typing import Any
import minergym.simulation as simulation


def auto_get_actuators(
    ont: Ontology,
) -> dict[str, simulation.ActuatorHole]:
    """Add all actuators listed in the graph. This is probably not what you
    want, since actuators that are not heating/cooling setpoints will be added
    too."""
    act = {}
    for node in ont.schedules():
        name = node.toPython()
        # for name in zones_with_cooling
        act[name] = simulation.ActuatorHole("Schedule:Compact", "Schedule Value", name)
    return act


def auto_add_temperature(
    ont: Ontology, obs_template: dict[str, Any]
) -> None:
    """Add a "ZONE AIR TEMPERATURE" for each zone in the graph."""
    temps = {}
    temps["environment"] = simulation.VariableHole(
        "SITE OUTDOOR AIR DRYBULB TEMPERATURE",
        "ENVIRONMENT",
    )
    for node in ont.zones():
        z = node.toPython()
        temps[z] = simulation.VariableHole("ZONE AIR TEMPERATURE", z)
        obs_template["temperature"] = temps


def auto_add_setpoint_variables(
    ont: Ontology, obs_template: dict[str, Any]
) -> None:
    setpoints: Any = {}
    obs_template["setpoints"] = setpoints

    heating: Any = {}
    setpoints["heating"] = heating

    cooling: Any = {}
    setpoints["cooling"] = cooling

    for node in ont.zones():
        z = node.toPython()
        heating[z] = simulation.VariableHole(
            "Zone Thermostat Heating Setpoint Temperature", z
        )
        cooling[z] = simulation.VariableHole(
            "Zone Thermostat Cooling Setpoint Temperature", z
        )


def auto_add_comfort(
    ont: Ontology, obs_template: dict[str, Any]
) -> None:
    if "comfort" not in obs_template:
        obs_template["comfort"] = {}

    comfort = obs_template["comfort"]
    for node in ont.zones():
        z = node.toPython()
        comfort[z + "_comfort"] = simulation.VariableHole(
            "Zone Thermal Comfort Pierce Model Thermal Sensation Index", z
        )
        comfort[z + "_discomfort"] = simulation.VariableHole(
            "Zone Thermal Comfort Pierce Model Discomfort Index", z
        )


def auto_add_energy(
    ont: Ontology, obs_template: dict[str, Any]
) -> None:
    if "reward" not in obs_template:
        obs_template["energy"] = {}

    r = obs_template["energy"]

    r["whole_building"] = simulation.MeterHole("Electricity:HVAC")

    for node in ont.zones():
        z = node.toPython()
        r[z + "_cooling"] = simulation.VariableHole(
            "Zone Air System Sensible Cooling Energy", z
        )
        r[z + "_heating"] = simulation.VariableHole(
            "Zone Air System Sensible Heating Energy", z
        )


def auto_add_time(
    ont: Ontology, obs_template: dict[str, any]
) -> None:
    """Add ubiquitous variables."""

    time: Any = {}
    obs_template["time"] = time
    time["current_time"] = simulation.FunctionHole(simulation.api.exchange.current_time)
    time["day_of_year"] = simulation.FunctionHole(simulation.api.exchange.day_of_year)

    # # All of those don't work
    # time["current_sim_time"] = myeplus.Function(myeplus.api.exchange.current_sim_time)
    # time["day_of_month"] = myeplus.Function(myeplus.api.exchange.day_of_month)
    # time["day_of_week"] = myeplus.Function(myeplus.api.exchange.day_of_week)
    # time["actual_date_time"] = myeplus.Function(myeplus.api.exchange.actual_date_time)
    # time["year"] = myeplus.Function(myeplus.api.exchange.year)

def auto_add_weather(
        ont: Ontology, obs_template: dict[str, Any]
) -> None:
    """Add outdoor air measurements to the observation template."""
    if "weather" not in obs_template:
        obs_template["weather"] = {}

    weather = obs_template["weather"]
    weather["drybulb_temp"] = simulation.VariableHole(
        "Site Outdoor Air Drybulb Temperature", "Environment"
    )
    weather["relative_humidity"] = simulation.VariableHole(
        "Site Outdoor Air Relative Humidity", "Environment"
    )
