from selenium import webdriver
from bs4 import BeautifulSoup
import logging
import time

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

logger = logging.getLogger("fetch_jobs_info.py")

def fetch_engineering_jobs_info():
    logger.info("Fetching Engineering Jobs.")

    # Setup Selenium
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    url = "https://jobyaari.com/category/engineering?type=graduate"
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 🔑 Use the right card container
    job_cards = soup.find_all("div", class_="drop__card")

    jobs_data = []
    for card in job_cards:
        job = {}

        # Title
        title = card.select_one(".drop-sub-name .badge.badge-warning")
        job["title"] = title.get_text(strip=True) if title else None

        # Organization
        org = card.select_one(".drop-sub-name .drop__profession")
        job["organization"] = org.get_text(strip=True) if org else None

        # Salary
        salary = card.select_one(".exp-salary .salary-price span:nth-of-type(2)")
        job["salary"] = salary.get_text(strip=True) if salary else None

        # Experience
        exp = card.select_one(".exp-salary .drop__exp span:nth-of-type(2)")
        job["experience"] = exp.get_text(strip=True) if exp else None

        # Qualification
        qualification = card.find("div", class_="salary")
        job["qualification"] = qualification.get_text(strip=True) if qualification else None

        # Location
        location = card.find("div", class_="location")
        job["location"] = location.get_text(strip=True) if location else None

        # Discipline
        tags = card.find("div", class_="tags-part")
        if tags:
            job["discipline"] = ", ".join(
                t.get_text(strip=True) for t in tags.find_all("a", class_="tags-item")
            )
        else:
            job["discipline"] = None

        # Dates
        post_items = card.find_all("div", class_="post-item")
        if len(post_items) >= 1:
            job["last_date"] = post_items[0].get_text(strip=True).replace("Last Date:", "").strip()
        if len(post_items) >= 2:
            job["posted_date"] = post_items[1].get_text(strip=True).replace("Posted", "").strip()

        jobs_data.append(job)

    driver.quit()
    
    return jobs_data
    
def fetch_science_jobs_info():
    logger.info("Fetching Science Jobs.")

    # Setup Selenium
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    url = "https://jobyaari.com/category/science?type=graduate"
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 🔑 Use the right card container
    job_cards = soup.find_all("div", class_="drop__card")

    jobs_data = []
    for card in job_cards:
        job = {}

        # Title
        title = card.select_one(".drop-sub-name .badge.badge-warning")
        job["title"] = title.get_text(strip=True) if title else None

        # Organization
        org = card.select_one(".drop-sub-name .drop__profession")
        job["organization"] = org.get_text(strip=True) if org else None

        # Salary
        salary = card.select_one(".exp-salary .salary-price span:nth-of-type(2)")
        job["salary"] = salary.get_text(strip=True) if salary else None

        # Experience
        exp = card.select_one(".exp-salary .drop__exp span:nth-of-type(2)")
        job["experience"] = exp.get_text(strip=True) if exp else None

        # Qualification
        qualification = card.find("div", class_="salary")
        job["qualification"] = qualification.get_text(strip=True) if qualification else None

        # Location
        location = card.find("div", class_="location")
        job["location"] = location.get_text(strip=True) if location else None

        # Discipline
        tags = card.find("div", class_="tags-part")
        if tags:
            job["discipline"] = ", ".join(
                t.get_text(strip=True) for t in tags.find_all("a", class_="tags-item")
            )
        else:
            job["discipline"] = None

        # Dates
        post_items = card.find_all("div", class_="post-item")
        if len(post_items) >= 1:
            job["last_date"] = post_items[0].get_text(strip=True).replace("Last Date:", "").strip()
        if len(post_items) >= 2:
            job["posted_date"] = post_items[1].get_text(strip=True).replace("Posted", "").strip()

        jobs_data.append(job)

    driver.quit()
    
    return jobs_data

def fetch_commerce_jobs_info():
    logger.info("Fetching Commerce Jobs.")

    # Setup Selenium
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    url = "https://jobyaari.com/category/commerce?type=graduate"
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 🔑 Use the right card container
    job_cards = soup.find_all("div", class_="drop__card")

    jobs_data = []
    for card in job_cards:
        job = {}

        # Title
        title = card.select_one(".drop-sub-name .badge.badge-warning")
        job["title"] = title.get_text(strip=True) if title else None

        # Organization
        org = card.select_one(".drop-sub-name .drop__profession")
        job["organization"] = org.get_text(strip=True) if org else None

        # Salary
        salary = card.select_one(".exp-salary .salary-price span:nth-of-type(2)")
        job["salary"] = salary.get_text(strip=True) if salary else None

        # Experience
        exp = card.select_one(".exp-salary .drop__exp span:nth-of-type(2)")
        job["experience"] = exp.get_text(strip=True) if exp else None

        # Qualification
        qualification = card.find("div", class_="salary")
        job["qualification"] = qualification.get_text(strip=True) if qualification else None

        # Location
        location = card.find("div", class_="location")
        job["location"] = location.get_text(strip=True) if location else None

        # Discipline
        tags = card.find("div", class_="tags-part")
        if tags:
            job["discipline"] = ", ".join(
                t.get_text(strip=True) for t in tags.find_all("a", class_="tags-item")
            )
        else:
            job["discipline"] = None

        # Dates
        post_items = card.find_all("div", class_="post-item")
        if len(post_items) >= 1:
            job["last_date"] = post_items[0].get_text(strip=True).replace("Last Date:", "").strip()
        if len(post_items) >= 2:
            job["posted_date"] = post_items[1].get_text(strip=True).replace("Posted", "").strip()

        jobs_data.append(job)

    driver.quit()
    
    return jobs_data

def fetch_education_jobs_info():
    logger.info("Fetching Education Jobs.")

    # Setup Selenium
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    url = "https://jobyaari.com/category/education?type=graduate"
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 🔑 Use the right card container
    job_cards = soup.find_all("div", class_="drop__card")

    jobs_data = []
    for card in job_cards:
        job = {}

        # Title
        title = card.select_one(".drop-sub-name .badge.badge-warning")
        job["title"] = title.get_text(strip=True) if title else None

        # Organization
        org = card.select_one(".drop-sub-name .drop__profession")
        job["organization"] = org.get_text(strip=True) if org else None

        # Salary
        salary = card.select_one(".exp-salary .salary-price span:nth-of-type(2)")
        job["salary"] = salary.get_text(strip=True) if salary else None

        # Experience
        exp = card.select_one(".exp-salary .drop__exp span:nth-of-type(2)")
        job["experience"] = exp.get_text(strip=True) if exp else None

        # Qualification
        qualification = card.find("div", class_="salary")
        job["qualification"] = qualification.get_text(strip=True) if qualification else None

        # Location
        location = card.find("div", class_="location")
        job["location"] = location.get_text(strip=True) if location else None

        # Discipline
        tags = card.find("div", class_="tags-part")
        if tags:
            job["discipline"] = ", ".join(
                t.get_text(strip=True) for t in tags.find_all("a", class_="tags-item")
            )
        else:
            job["discipline"] = None

        # Dates
        post_items = card.find_all("div", class_="post-item")
        if len(post_items) >= 1:
            job["last_date"] = post_items[0].get_text(strip=True).replace("Last Date:", "").strip()
        if len(post_items) >= 2:
            job["posted_date"] = post_items[1].get_text(strip=True).replace("Posted", "").strip()

        jobs_data.append(job)

    driver.quit()
    
    return jobs_data

def fetch_jobs_info():
    eng_jobs = fetch_engineering_jobs_info()
    comm_jobs = fetch_commerce_jobs_info()
    sci_jobs = fetch_science_jobs_info()
    edu_jobs = fetch_education_jobs_info()

    jobs_list = eng_jobs + comm_jobs + sci_jobs + edu_jobs
    logger.info("All jobs information merged.")

    return jobs_list

if __name__ == "__main__":
    result = fetch_jobs_info()
    print(len(result))
    print(result[:5])