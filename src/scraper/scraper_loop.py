import time
from datetime import datetime
from src.scraper.fetch_jobs_info import fetch_jobs_info
from src.scraper.vector_utils import update_chroma
import logging

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Silence noisy libraries
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

logger = logging.getLogger("scraper_loop.py")

def main():
    while True:
        logger.info(f"Running scraper...")

        jobs = fetch_jobs_info()
        logger.info(f"Scraped jobs: {len(jobs)}")
        
        update_chroma(jobs)
        logger.info(f"Completed update. Sleeping 20 mins...")
        
        time.sleep(20 * 60)

if __name__ == "__main__":
    main()
