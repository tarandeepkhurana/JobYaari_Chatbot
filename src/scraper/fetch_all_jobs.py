from src.scraper.intershala.engineering import scrape_internshala_engineering
from src.scraper.intershala.bank import scrape_internshala_bank
from src.scraper.intershala.ai_agent_development import (
    scrape_internshala_ai_agent_development,
)
from src.scraper.intershala.accounts import scrape_internshala_accounts
from src.scraper.intershala.android_app_development import (
    scrape_internshala_android_app_development,
)
from src.scraper.intershala.backend_development import (
    scrape_internshala_backend_development,
)
from src.scraper.intershala.cad_design import scrape_internshala_cad_design
from src.scraper.intershala.chartered_accountancy_ca import (
    scrape_internshala_chartered_accountancy_ca,
)
from src.scraper.intershala.cloud_computing import scrape_internshala_cloud_computing
from src.scraper.intershala.electronics import scrape_internshala_electronics
from src.scraper.intershala.front_end_development import (
    scrape_internshala_front_end_development,
)
from src.scraper.intershala.full_stack_development import (
    scrape_internshala_full_stack_development,
)
from src.scraper.intershala.hr import scrape_internshala_hr
from src.scraper.intershala.cyber_security import scrape_internshala_cyber_security
from src.scraper.intershala.teaching import scrape_internshala_teaching
from src.scraper.intershala.product import scrape_internshala_product
import logging
import asyncio

logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


logger = logging.getLogger("fetch_jobs_info")


async def fetch_all_jobs():
    logger.info("Starting to fetch all jobs.")  
    
    engineering_task = scrape_internshala_engineering()
    bank_task = scrape_internshala_bank()
    ai_agent_task = scrape_internshala_ai_agent_development()
    accounts_task = scrape_internshala_accounts()
    android_task = scrape_internshala_android_app_development()
    backend_task = scrape_internshala_backend_development()
    cad_task = scrape_internshala_cad_design()
    ca_task = scrape_internshala_chartered_accountancy_ca()
    cloud_task = scrape_internshala_cloud_computing()
    electronics_task = scrape_internshala_electronics()
    frontend_task = scrape_internshala_front_end_development()
    fullstack_task = scrape_internshala_full_stack_development()
    hr_task = scrape_internshala_hr()
    cyber_security_task = scrape_internshala_cyber_security()
    teaching_task = scrape_internshala_teaching()
    product_task = scrape_internshala_product()

    engineering_jobs, bank_jobs, ai_agent_jobs, accounts_jobs, android_jobs, backend_jobs, cad_jobs, ca_jobs, cloud_jobs, electronics_jobs, frontend_jobs, fullstack_jobs, hr_jobs, cyber_security_jobs, teaching_jobs, product_jobs = await asyncio.gather(
        engineering_task,
        bank_task,
        ai_agent_task,
        accounts_task,
        android_task,
        backend_task,
        cad_task,
        ca_task,
        cloud_task,
        electronics_task,
        frontend_task,
        fullstack_task,
        hr_task,
        cyber_security_task,
        teaching_task,
        product_task,
    )

    all_jobs = (
        engineering_jobs
        + bank_jobs
        + ai_agent_jobs
        + accounts_jobs
        + android_jobs
        + backend_jobs
        + cad_jobs
        + ca_jobs
        + cloud_jobs
        + electronics_jobs
        + frontend_jobs
        + fullstack_jobs
        + hr_jobs
        + cyber_security_jobs
        + teaching_jobs
        + product_jobs
    )

    logger.info(f"Total jobs fetched: {len(all_jobs)}")

    return all_jobs

if __name__ == "__main__":
    result = asyncio.run(fetch_all_jobs())
    print(len(result))
    print(result[:5])
