import clean_energyplus.config as config
import clean_energyplus.query_info as query_info
import tests.test_data as test_data
import clean_energyplus.simulation as simulation
import clean_energyplus.data.building as building
import clean_energyplus.data.weather as weather


def test_full_config() -> None:

    obs_template = {}
    rdf = query_info.rdf_from_json(building.crawlspace)

    config.auto_add_temperature(rdf, obs_template)
    config.auto_add_energy(rdf, obs_template)

    sim = simulation.EnergyPlusSimulation(
        building.crawlspace,
        weather.honolulu,
        obs_template,
        {},
    )
    sim.start()
