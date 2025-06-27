from importlib import resources
from pathlib import Path


_building_dir = resources.files("minergym.data.building")

crawlspace = Path(_building_dir.joinpath("crawlspace.epJSON")).resolve(strict=True)

all_building_files = [crawlspace]
