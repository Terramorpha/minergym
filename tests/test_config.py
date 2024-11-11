import clean_energyplus.config as config
import clean_energyplus.query_info as query_info
import tests.test_data as test_data
import clean_energyplus.simulation as simulation


def test_full_config() -> None:
    building = str(test_data.building.joinpath("crawlspace.epJSON"))
    weather = str(test_data.weather.joinpath("honolulu.epw"))

    obs_template = {}
    rdf = query_info.json_to_rdf(building)

    config.auto_add_temperature_variables(rdf, obs_template)
    config.auto_add_energy_variables(rdf, obs_template)
    print(obs_template)

    sim = simulation.EnergyPlusSimulation(building, weather, obs_template, {})
    sim.start()
