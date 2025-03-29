import os
import pandas as pd
import subprocess
from typing import List
from src.generator.utils import get_county_from_coords


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


def find_transitioned_file(original_file: str, to_ver: str) -> str:
    """Helper function to find the transitioned file which might have different naming patterns"""
    idf_dir = os.path.dirname(original_file)
    base_name = os.path.splitext(os.path.basename(original_file))[0]
    
    # Different possible patterns for the output file
    possible_patterns = [
        # Pattern 1: original_name.idfnew (actual pattern we're seeing)
        os.path.join(idf_dir, f"{base_name}.idfnew"),
        # Pattern 2: original_name-V{version}.idf
        os.path.join(idf_dir, f"{base_name}-V{to_ver.replace('.', '-')}.idf"),
        # Pattern 3: original_name.V{version}.idf
        os.path.join(idf_dir, f"{base_name}.V{to_ver.replace('.', '-')}.idf"),
        # Pattern 4: original_name-{version}.idf
        os.path.join(idf_dir, f"{base_name}-{to_ver.replace('.', '-')}.idf"),
        # Pattern 5: original_name.{version}.idf
        os.path.join(idf_dir, f"{base_name}.{to_ver}.idf"),
        # Pattern 6: original_name.new
        os.path.join(idf_dir, f"{base_name}.new"),
        # Pattern 7: The original file might have been modified in place
        original_file,
    ]
    
    for pattern in possible_patterns:
        if os.path.exists(pattern):
            print(f"Found matching file: {pattern}")
            return pattern
            
    # If no pattern matches, print all files in directory for debugging
    print(f"Available files in {idf_dir}:")
    for file in os.listdir(idf_dir):
        print(f"  {file}")
            
    return None

def transition_idf(idf_path: str, state: str, county: str, target_version: str = "24.1") -> str:
    """
    Transition an IDF file to the target EnergyPlus version using the transition executables.
    Saves the processed file in data/processed_idf/state/county/ directory.

    Args:
        idf_path (str): Path to the input IDF file
        state (str): Two-letter state code
        county (str): County name
        target_version (str): Target EnergyPlus version (default: "24.1")

    Returns:
        str: Path to the transitioned file in the processed_idf directory
    """

    # Create the output directory structure
    processed_dir = os.path.join("data", "processed_idf", state, county)
    os.makedirs(processed_dir, exist_ok=True)

    idf_dir = os.path.dirname(idf_path)
    idf_name = os.path.basename(idf_path)
    
    # Define the final output path
    final_output_path = os.path.join(processed_dir, idf_name)
    
    # Create a temporary directory for transition files
    temp_dir = os.path.join(idf_dir, "temp_transition")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Copy the original file to temp directory to work with
    working_file = os.path.join(temp_dir, idf_name)
    with open(idf_path, 'r') as src, open(working_file, 'w') as dst:
        dst.write(src.read())
    
    try:
        # Define the transition sequence from 9.4 to 24.1
        transitions = [
            "9.4.0-to-9.5.0",
            "9.5.0-to-9.6.0",
            "9.6.0-to-22.1.0",
            "22.1.0-to-22.2.0",
            "22.2.0-to-23.1.0",
            "23.1.0-to-23.2.0",
            "23.2.0-to-24.1.0"
        ]
        
        # Path to the transition executables directory
        energyplus_dir = "/usr/local/EnergyPlus-24-1-0"
        transition_dir = os.path.join(energyplus_dir, "PreProcess", "IDFVersionUpdater")
        
        for transition in transitions:
            from_ver, to_ver = transition.split("-to-")
            
            # Get paths for the transition executable and IDD files
            transition_exe = os.path.join(transition_dir, f"Transition-V{from_ver.replace('.', '-')}-to-V{to_ver.replace('.', '-')}")
            from_idd = os.path.join(transition_dir, f"V{from_ver.replace('.', '-')}-Energy+.idd")
            to_idd = os.path.join(transition_dir, f"V{to_ver.replace('.', '-')}-Energy+.idd")
            
            # Check if required files exist
            if not os.path.exists(transition_exe):
                print(f"Error: Transition executable not found at {transition_exe}")
                return None
            if not os.path.exists(from_idd):
                print(f"Error: Source IDD file not found at {from_idd}")
                return None
            if not os.path.exists(to_idd):
                print(f"Error: Target IDD file not found at {to_idd}")
                return None
                
            # Create symbolic links to IDD files in the working directory
            current_dir = os.getcwd()
            from_idd_link = os.path.join(current_dir, os.path.basename(from_idd))
            to_idd_link = os.path.join(current_dir, os.path.basename(to_idd))
            
            try:
                if os.path.exists(from_idd_link):
                    os.remove(from_idd_link)
                if os.path.exists(to_idd_link):
                    os.remove(to_idd_link)
                    
                os.symlink(from_idd, from_idd_link)
                os.symlink(to_idd, to_idd_link)
                
                print(f"\nRunning transition from {from_ver} to {to_ver}")
                print(f"Using: {transition_exe}")
                print(f"Input: {working_file}")
                
                result = subprocess.run(
                    [transition_exe, working_file],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={"DISPLAY": ""}
                )
                
                if result.stdout:
                    print("Transition output:", result.stdout)
                if result.stderr:
                    print("Transition errors:", result.stderr)
                
                # Clean up any .idfold files that might have been created
                old_file = working_file + "old"
                if os.path.exists(old_file):
                    os.remove(old_file)
                
                # Look for the transitioned file
                transitioned_file = find_transitioned_file(working_file, to_ver)
                if transitioned_file:
                    print(f"Found transitioned file at: {transitioned_file}")
                    if transitioned_file != working_file:
                        # Replace working file with transitioned file
                        with open(transitioned_file, 'r') as src, open(working_file, 'w') as dst:
                            dst.write(src.read())
                        # Remove the transitioned file after copying
                        os.remove(transitioned_file)
                else:
                    print(f"Error: Could not find transitioned file for {working_file}")
                    return None
                    
            finally:
                # Clean up symbolic links
                if os.path.exists(from_idd_link):
                    os.remove(from_idd_link)
                if os.path.exists(to_idd_link):
                    os.remove(to_idd_link)
        
        # Copy the final file to the processed_idf directory instead of original location
        with open(working_file, 'r') as src, open(final_output_path, 'w') as dst:
            dst.write(src.read())
        
        print(f"\nFinal transitioned file saved to: {final_output_path}")
        
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass
    
    return final_output_path

def process_idf(idf_files: List[int], state: str, county: str):
    """
    Process IDF files if they haven't been processed already.
    
    Args:
        idf_files (List[int]): List of IDF file IDs
        state (str): Two-letter state code
        county (str): County name
    
    Returns:
        List[str]: List of paths to processed IDF files
    """
    processed_dir = os.path.join("data", "processed_idf", state, county)
    os.makedirs(processed_dir, exist_ok=True)
    
    processed_paths = []
    for idf_id in idf_files:
        # Check if processed file already exists
        processed_path = os.path.join(processed_dir, f"{idf_id}.idf")
        if os.path.exists(processed_path):
            print(f"Skipping {idf_id}.idf - already processed")
            processed_paths.append(processed_path)
            continue
            
        # Get path to original file
        original_path = os.path.join("data", "idf", f"{state}_{county}_IDF", f"{idf_id}.idf")
        if not os.path.exists(original_path):
            print(f"Warning: Original file not found at {original_path}")
            continue
            
        # Process the file
        processed_path = transition_idf(original_path, state, county)
        if processed_path:
            processed_paths.append(processed_path)
            
    return processed_paths
