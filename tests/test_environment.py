import clean_energyplus.simulation as simulation
import clean_energyplus.environment as environment
import tests.test_simulation as test_simulation


def test_environment():
    def make_energyplus():
        simulation.EnergyPlusSimulation(
            test_simulation.default_building,
            test_simulation.default_weather,
        )

    pass
