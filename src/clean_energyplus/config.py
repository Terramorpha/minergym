"""To run an EnergyPlus simulation and wrap it into the neat

observation -> policy -> action -> environment -> observation

box commonly used in RL, it is necessary to have the following components:

1. A building file.
2. A weather file.
3. The set of EP variables which will be written to the observations.
4. The set of EP actuators which will be read from the action.

This module collects functions useful to creates those 4-tuples.

"""

import collections
import clean_energyplus.query_info as query_info
import rdflib
import typing
import clean_energyplus.simulation as simulation


SimulationConfig = collections.namedtuple(
    "SimulationConfig",
    [
        "building_file",
        "weather_file",
        "observation_template",
        "actuators",
    ],
)


def auto_get_actuators(
    rdf: rdflib.Graph,
) -> typing.Dict[str, simulation.ActuatorThingy]:
    """Add all actuators listed in the graph. This is probably not what you
    want, since actuators that are not heating/cooling setpoints will be added
    too."""
    act = {}
    for name in query_info.rdf_schedules(rdf):
        # for name in zones_with_cooling
        act[name] = simulation.ActuatorThingy(
            "Schedule:Compact", "Schedule Value", name
        )
    return act


def auto_add_actuators_observation(rdf: rdflib.Graph, variables) -> None:
    act = {}
    for name in query_info.rdf_schedules(rdf):
        # for name in zones_with_cooling
        act[name] = simulation.ActuatorHole(
            "Schedule:Compact",
            "Schedule Value",
            name,
        )
    variables["actuators"] = act


def auto_add_temperature_variables(rdf: rdflib.Graph, variables) -> None:
    """Add a "ZONE AIR TEMPERATURE" for each zone in the graph."""
    temps = {}
    temps["environment"] = simulation.VariableHole(
        "SITE OUTDOOR AIR DRYBULB TEMPERATURE",
        "ENVIRONMENT",
    )
    for z in query_info.rdf_zones(rdf):
        temps[z] = simulation.VariableHole("ZONE AIR TEMPERATURE", z)
        variables["temperature"] = temps


def auto_add_setpoint_variables(rdf: rdflib.Graph, variables) -> None:
    setpoints: typing.Any = {}
    variables["setpoints"] = setpoints

    heating: typing.Any = {}
    setpoints["heating"] = heating

    cooling: typing.Any = {}
    setpoints["cooling"] = cooling

    for z in query_info.rdf_zones(rdf):
        heating[z] = simulation.VariableHole(
            "Zone Thermostat Heating Setpoint Temperature", z
        )
        cooling[z] = simulation.VariableHole(
            "Zone Thermostat Cooling Setpoint Temperature", z
        )


def auto_add_comfort_variables(rdf: rdflib.Graph, variables) -> None:
    if "comfort" not in variables:
        variables["comfort"] = {}

    comfort = variables["comfort"]
    for z in query_info.rdf_zones(rdf):
        comfort[z + "_comfort"] = simulation.VariableHole(
            "Zone Thermal Comfort Pierce Model Thermal Sensation Index", z
        )
        comfort[z + "_discomfort"] = simulation.VariableHole(
            "Zone Thermal Comfort Pierce Model Discomfort Index", z
        )


def auto_add_energy_variables(rdf: rdflib.Graph, variables) -> None:
    if "reward" not in variables:
        variables["energy"] = {}

    r = variables["energy"]

    r["whole_building"] = simulation.MeterHole("Electricity:HVAC")

    for z in query_info.rdf_zones(rdf):
        r[z + "_cooling"] = simulation.VariableHole(
            "Zone Air System Sensible Cooling Energy", z
        )
        r[z + "_heating"] = simulation.VariableHole(
            "Zone Air System Sensible Heating Energy", z
        )


def auto_add_time_variables(rdf: rdflib.Graph, variables) -> None:
    """Add ubiquitous variables."""

    time: typing.Any = {}
    variables["time"] = time
    time["current_time"] = simulation.FunctionHole(simulation.api.exchange.current_time)

    # # All of those don't work
    # time["current_sim_time"] = myeplus.Function(myeplus.api.exchange.current_sim_time)
    # time["day_of_month"] = myeplus.Function(myeplus.api.exchange.day_of_month)
    # time["day_of_week"] = myeplus.Function(myeplus.api.exchange.day_of_week)
    time["day_of_year"] = simulation.FunctionHole(simulation.api.exchange.day_of_year)
    # time["actual_date_time"] = myeplus.Function(myeplus.api.exchange.actual_date_time)
    # time["year"] = myeplus.Function(myeplus.api.exchange.year)
