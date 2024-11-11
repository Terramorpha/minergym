from importlib import resources

_building_dir = resources.files("clean_energyplus.data.building")

crawlspace = str(_building_dir.joinpath("crawlspace.epJSON"))

all_building_files = [crawlspace]
