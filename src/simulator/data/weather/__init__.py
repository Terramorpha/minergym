from importlib import resources

_weather_dir = resources.files("minergym.data.weather")

honolulu = str(_weather_dir.joinpath("honolulu.epw"))
miami = str(_weather_dir.joinpath("miami.epw"))


all_weather_files = [honolulu, miami]
