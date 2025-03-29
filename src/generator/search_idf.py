import pandas as pd
import os
from src.generator.utils import process_metadata
from src.generator.downloader import download_and_extract_county_idf
from src.generator.downloader import download_metadata
from src.generator.processing import process_idf


def search_metadata(metadata: pd.DataFrame, building_type: str, area: float, num_floors: int, height: float=None, n_buildings: int=1):

    # Filter by building type
    filtered = metadata[metadata['BuildingType'] == building_type].copy()
    
    if filtered.empty:
        return []

    # Compute distances for sorting
    filtered['Area_diff'] = (filtered['Area'] - area).abs()
    filtered['Floors_diff'] = (filtered['NumFloors'] - num_floors).abs()
    if height is not None:
        filtered['Height_diff'] = (filtered['Height'] - height).abs()
    else:
        filtered['Height_diff'] = 0 

    # Sort by area difference, then floors, then height
    sorted_filtered = filtered.sort_values(by=['Area_diff', 'Floors_diff', 'Height_diff'])

    # Return the top n_buildings IDs
    return sorted_filtered['ID'].head(n_buildings).tolist()

def load_metadata(state: str, county: str=None):
    metadata = pd.read_csv(os.path.join("data", "metadata", f"{state}.csv"))
    if county is not None:
        metadata = metadata[metadata['County'] == county]
    return metadata


def search_idf(state: str, county:str, building_type: str, area: float, num_floors: int, height: float, n_buildings: int):

    # Download idf files if not already downloaded

    county_dir = download_and_extract_county_idf(state, county)
    print(county_dir)

    # Load metadata
    download_metadata(state=state)
    process_metadata(state=state)
    metadata = load_metadata(state, county=county)
    print(metadata.shape)   

    # Search for matching IDF files
    idf_files = search_metadata(metadata, building_type, area, num_floors, height, n_buildings)
    print("IDF files found:")
    print(idf_files)

    process_idf(idf_files, state, county)

    
