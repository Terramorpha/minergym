from importlib import resources
from pathlib import Path

_weather_dir = resources.files("minergym.data.weather")

honolulu = Path(_weather_dir.joinpath("honolulu.epw")).resolve(strict=True)
miami = Path(_weather_dir.joinpath("miami.epw")).resolve(strict=True)


all_weather_files = [honolulu, miami]
