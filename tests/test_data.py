from importlib import resources

building = resources.files("clean_energyplus.data.building")
weather = resources.files("clean_energyplus.data.weather")


def test_data_sanity():
    assert not building.joinpath("does_not_exist.epJSON").exists()


def test_crawlspace():

    assert building.joinpath("crawlspace.epJSON").exists()


def test_honolulu():

    assert weather.joinpath("honolulu.epw").exists()
