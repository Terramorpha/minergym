import minergym.config as config
from minergym.ontology import Ontology
import tests.test_data as test_data
import minergym.simulation as simulation
import minergym.data.building as building
import minergym.data.weather as weather


def test_full_config() -> None:

    obs_template = {}
    ont = Ontology.from_json(building.crawlspace)

    config.auto_add_temperature(ont, obs_template)
    config.auto_add_energy(ont, obs_template)

    sim = simulation.EnergyPlusSimulation(
        building.crawlspace,
        weather.honolulu,
        obs_template,
        {},
    )
    sim.start()
