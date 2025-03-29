import requests
import os
import pandas as pd
import glob

def get_county_from_coords(lat, lon):
    """
    Returns the US county name for given latitude and longitude using FCC API.
    Formats the county name by removing the last word and replacing spaces/hyphens with underscores.

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
                return formatted_name
        return None
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return None

def process_metadata(state: str):
    """
    Process all metadata CSV files in the metadata directory to get the county name for each row.
    For each file:
    1. Loads the CSV
    2. If County column exists, skip the file as it's already processed
    3. Parses the Centroid column to extract latitude and longitude
    4. Creates a new County column with the county name for each coordinate pair
    """
    
    csv_file = os.path.join("data", "metadata", f"{state}.csv")
    
    # Process each CSV file in the metadata directory
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Skip if County column already exists
        if 'County' in df.columns:
            print(f"Skipping {csv_file} - already processed")
            return
        
        # Split the Centroid column into latitude and longitude
        df[['Latitude', 'Longitude']] = df['Centroid'].str.split('/', expand=True)
        
        # Convert to float
        df['Latitude'] = df['Latitude'].astype(float)
        df['Longitude'] = df['Longitude'].astype(float)
        
        # Get county for each coordinate pair
        df['County'] = df.apply(
            lambda row: get_county_from_coords(row['Latitude'], row['Longitude']), 
            axis=1
        )
        
        # Save the updated CSV file
        df.to_csv(csv_file, index=False)
        print(f"Processed and updated {csv_file}")
            
    except Exception as e:
        print(f"Error processing {csv_file}: {e}")

