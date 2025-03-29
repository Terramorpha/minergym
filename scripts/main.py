from src.generator.search_idf import search_idf
from src.generator.utils import get_county_from_coords

if __name__ == "__main__":
    # print(get_county_from_coords(61.25, -150.02))
    search_idf("AK", "Matanuska_Susitna", "SmallHotel", 1140, 6, None, 1)
