import requests
import logging

logger = logging.getLogger('generator')

def get_county_from_coords(lat, lon):
    """
    Returns the US county name for given latitude and longitude using FCC API.
    Formats to fit dataset format: removes the last word and replaces spaces/hyphens with underscores.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        str: Formatted county name if found, else None
    """
    url = "https://geo.fcc.gov/api/census/block/find"
    params = {
        "latitude": lat,
        "longitude": lon,
        "format": "json"
    }

    try:
        logger.debug(f"Querying FCC API for coordinates: ({lat}, {lon})")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        county_name = data.get('County', {}).get('name')
        
        if county_name:
            # Remove the last word (usually 'County') and split remaining words
            words = county_name.split()[:-1]
            if words:
                # Join remaining words and replace spaces/hyphens with underscore
                formatted_name = '_'.join(''.join(words).replace('-', '_').split())
                logger.debug(f"Found county: {county_name} -> formatted as: {formatted_name}")
                return formatted_name
            
        logger.warning(f"No county name found for coordinates ({lat}, {lon})")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Request error for coordinates ({lat}, {lon}): {e}")
    except Exception as e:
        logger.error(f"Unexpected error while getting county for coordinates ({lat}, {lon}): {e}")
    
    return None
