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
import graph
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


def auto_add_actuators(rdf, actuators):
    """Add all actuators listed in the graph. This is probably not what you
    want, since actuators that are not heating/cooling setpoints will be added
    too."""
    for name in graph.rdf_schedules(rdf):
        # for name in zones_with_cooling
        actuators[name] = ("Schedule:Compact", "Schedule Value", name)


def auto_add_actuators_observation(rdf, variables):
    act = {}
    for name in graph.rdf_schedules(rdf):
        # for name in zones_with_cooling
        act[name] = simulation.Actuator(
            (
                "Schedule:Compact",
                "Schedule Value",
                name,
            )
        )
    variables["actuators"] = act


def auto_add_temperature_variables(rdf, variables):
    """Add a "ZONE AIR TEMPERATURE" for each zone in the graph."""
    temps = {}
    temps["environment"] = simulation.Variable(
        (
            "SITE OUTDOOR AIR DRYBULB TEMPERATURE",
            "ENVIRONMENT",
        )
    )
    for z in graph.rdf_zones(rdf):
        temps[z] = simulation.Variable(("ZONE AIR TEMPERATURE", z))
        variables["temperature"] = temps


def auto_add_setpoint_variables(rdf, variables):
    setpoints = {}
    variables["setpoints"] = setpoints

    heating = {}
    setpoints["heating"] = heating

    cooling = {}
    setpoints["cooling"] = cooling

    for z in graph.rdf_zones(rdf):
        heating[z] = simulation.Variable(
            ("Zone Thermostat Heating Setpoint Temperature", z)
        )
        cooling[z] = simulation.Variable(
            ("Zone Thermostat Cooling Setpoint Temperature", z)
        )


def auto_add_comfort_variables(rdf, variables):
    if "comfort" not in variables:
        variables["comfort"] = {}

    comfort = variables["comfort"]
    for z in graph.rdf_zones(rdf):
        comfort[z + "_comfort"] = simulation.Variable(
            ("Zone Thermal Comfort Pierce Model Thermal Sensation Index", z)
        )
        comfort[z + "_discomfort"] = simulation.Variable(
            ("Zone Thermal Comfort Pierce Model Discomfort Index", z)
        )


def auto_add_energy_variables(rdf, variables):
    if "reward" not in variables:
        variables["energy"] = {}

    r = variables["energy"]

    r["whole_building"] = simulation.Meter("Electricity:HVAC")

    for z in graph.rdf_zones(rdf):
        r[z + "_cooling"] = simulation.Variable(
            ("Zone Air System Sensible Cooling Energy", z)
        )
        r[z + "_heating"] = simulation.Variable(
            ("Zone Air System Sensible Heating Energy", z)
        )


def auto_add_base_variables(rdf, variables):
    """Add ubiquitous variables."""

    time = {}
    variables["time"] = time
    time["current_time"] = simulation.FunctionHole(simulation.api.exchange.current_time)

    # # All of those don't work
    # time["current_sim_time"] = myeplus.Function(myeplus.api.exchange.current_sim_time)
    # time["day_of_month"] = myeplus.Function(myeplus.api.exchange.day_of_month)
    # time["day_of_week"] = myeplus.Function(myeplus.api.exchange.day_of_week)
    time["day_of_year"] = simulation.FunctionHole(simulation.api.exchange.day_of_year)
    # time["actual_date_time"] = myeplus.Function(myeplus.api.exchange.actual_date_time)
    # time["year"] = myeplus.Function(myeplus.api.exchange.year)


def auto_add_debug_variables(_, variables):
    debug = {}
    variables["debug"] = debug
    debug["api_data_fully_ready"] = simulation.FunctionHole(
        simulation.api.exchange.api_data_fully_ready
    )


def alburquerque():
    buildingfile = "./buildings/alburquerque.epJSON"
    weatherfile = "./honolulu.epw"

    rdf = graph.json_to_rdf(buildingfile)
    actuators = {}
    variables = {}

    auto_add_energy_variables(rdf, variables)
    auto_add_actuators(rdf, actuators)
    auto_add_actuators_observation(rdf, variables)
    auto_add_base_variables(rdf, variables)
    auto_add_temperature_variables(rdf, variables)
    return SimulationConfig(buildingfile, weatherfile, variables, actuators)


def crawlspace():
    buildingfile = "./buildings/crawlspace.epJSON"
    weatherfile = "./miami.epw"

    rdf = graph.json_to_rdf(buildingfile)
    actuators = {}
    variables = {}

    auto_add_energy_variables(rdf, variables)
    auto_add_actuators(rdf, actuators)
    auto_add_actuators_observation(rdf, variables)
    auto_add_base_variables(rdf, variables)
    auto_add_temperature_variables(rdf, variables)
    auto_add_debug_variables(rdf, variables)
    # auto_add_comfort_variables(rdf, variables)
    # auto_add_setpoint_variables(rdf, variables)
    return SimulationConfig(buildingfile, weatherfile, variables, actuators)
