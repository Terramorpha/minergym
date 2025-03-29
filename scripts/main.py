from datetime import datetime
from src.generator.search_idf import search_idf
from src.generator.utils import get_county_from_coords
from src.core.logging import setup_logger

if __name__ == "__main__":
    # Create timestamp for unique log file name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"idf_generation_{timestamp}.log"
    
    # Setup root logger with the unique filename
    logger = setup_logger('root', filename=log_filename)
    
    # Setup specific loggers for different modules to use the same file
    generator_logger = setup_logger('generator', filename=log_filename)
    simulator_logger = setup_logger('simulator', filename=log_filename)  # For future use
    
    logger.info("Starting IDF generation process...")
    
    # print(get_county_from_coords(61.25, -150.02))
    search_idf("AK", "Matanuska_Susitna", "SmallHotel", 1140, 6, None, 1)
