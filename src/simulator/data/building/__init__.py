from importlib import resources

_building_dir = resources.files("minergym.data.building")

crawlspace = str(_building_dir.joinpath("crawlspace.epJSON"))

all_building_files = [crawlspace]
