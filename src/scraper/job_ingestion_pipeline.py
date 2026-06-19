import asyncio
from src.scraper.fetch_all_jobs import fetch_all_jobs
from src.db.job_ops import upsert_jobs, remove_old_jobs
from src.utils.embeddings import generate_embeddings_azure_endpoint
import logging

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Silence noisy libraries
# logging.getLogger("chromadb").setLevel(logging.WARNING)
# logging.getLogger("httpcore").setLevel(logging.WARNING)
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("urllib3").setLevel(logging.WARNING)
# logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

logger = logging.getLogger("job_ingestion_pipeline")

async def run_pipeline():
    logger.info("Running scraper pipeline...")

    # 1. scrape (must be async)
    jobs = await fetch_all_jobs()
    logger.info(f"Scraped jobs total before dedupe: {len(jobs)}")
    
    # 2. embeddings (async)
    jobs = await generate_embeddings_azure_endpoint(jobs)

    # 3. DB write
    await upsert_jobs(jobs)

    # 4. cleanup
    await remove_old_jobs(days=30)

    logger.info("Pipeline completed.")
        
        
# -------------------------
# MAIN LOOP (ASYNC)
# -------------------------
async def main_loop():
    while True:
        try:
            await run_pipeline()

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")

        logger.info("Sleeping 20 minutes...")
        await asyncio.sleep(20 * 60)


if __name__ == "__main__":
    asyncio.run(main_loop())
