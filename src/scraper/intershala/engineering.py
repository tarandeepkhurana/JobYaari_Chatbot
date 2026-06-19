import re
import uuid
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
import json
from src.utils.scraper_utils import (generate_dedupe_key, parse_posted_relative, parse_salary_range,
                                     parse_location, create_base_job)
import logging


logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


logger = logging.getLogger("intershala.engineering")

async def scrape_internshala_engineering():
    URL = "https://internshala.com/internships/engineering-internship/"
    HEADERS = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        response = await client.get(URL)
    soup = BeautifulSoup(response.text, "lxml")
    cards = soup.find_all("div", class_=re.compile(r"individual_internship"))

    internships = []

    for card in cards:
        try:
            title_tag = card.find("a", id="job_title")
            title = title_tag.get_text(strip=True) if title_tag else None
            if not title:
                continue

            link = title_tag.get("href")
            if link:
                link = urljoin("https://internshala.com", link)

            company_tag = card.find("p", class_="company-name")
            company = company_tag.get_text(strip=True) if company_tag else None

            location_div = card.find("div", class_="locations")
            location = location_div.get_text(" ", strip=True) if location_div else None

            stipend_tag = card.find("span", class_="stipend")
            stipend_text = (
                stipend_tag.get_text(strip=True).replace("₹", "Rs.")
                if stipend_tag else None
            )

            duration = None
            row_items = card.find_all("div", class_="row-1-item")
            for item in row_items:
                text = item.get_text(" ", strip=True)
                if "Month" in text:
                    duration = text
                    break

            desc = None
            desc_tag = card.find("div", class_="about_job")
            if desc_tag:
                text_div = desc_tag.find("div", class_="text")
                if text_div:
                    desc = text_div.get_text(strip=True)

            skills = []
            for skill in card.find_all("div", class_="job_skill"):
                normalized_skill = skill.get_text(strip=True).lower()
                if normalized_skill:
                    skills.append(normalized_skill)

            # remove duplicates while preserving order
            skills = list(dict.fromkeys(skills))

            posted_div = card.find("div", class_=re.compile(r"status-"))
            posted = posted_div.get_text(" ", strip=True) if posted_div else None

            ppo_div = card.find("div", class_="ppo_status")
            ppo = ppo_div.get_text(" ", strip=True) if ppo_div else None

            internship_id = card.get("internshipid")

            # --- Fetch detail page ---
            detail_data = {}
            if link:
                detail_data = await scrape_internshala_detail(link)
        
            stipend_min, stipend_max, stipend_display = parse_salary_range(stipend_text)

            # Determine cities, work_mode, remote based on location text
            cities, work_mode, is_remote = parse_location(location)

            job = create_base_job()
            job.update({
                "source": "internshala",
                "source_job_id": internship_id or str(uuid.uuid4()),
                "source_url": link,
                "application_url": link,

                "title": title,
                "description": desc,

                "job_type": "internship",
                "work_mode": work_mode,
                "remote": is_remote,

                "org_name": company,
                "org_logo_url": detail_data.get("org_logo_url"),

                "cities": cities,

                "stipend_min": stipend_min,
                "stipend_max": stipend_max,
                "stipend_display": stipend_display,
                "is_paid": stipend_min is not None,

                "duration_display": duration,
                "duration_days": parse_duration_to_days(duration),

                "skills": skills,
                "categories": ["engineering"],
                "eligibility": detail_data.get("eligibility", []),
                "benefits": detail_data.get("perks", []),
                "work_functions": [
                    line.strip() for line in (desc or "").split("\n")
                    if line.strip() and re.match(r"^\d+\.", line.strip())
                ],

                "posted_at": parse_posted_relative(posted),

                "embedding_text": (
                    f"{title} {company} "
                    f"{desc or ''} "
                    f"{' '.join(skills)} "
                    f"{' '.join(detail_data.get('other_requirements', []))}"
                ).strip(),

                "raw_payload": {
                },

                "extra_metadata": {
                    "posted_text": posted,
                    "ppo_info": ppo,
                    "who_can_apply": detail_data.get("who_can_apply"),
                    "other_requirements": detail_data.get("other_requirements", []),
                    "additional_info": detail_data.get("additional_info", []),
                    "openings": detail_data.get("openings"),
                    "about_company": detail_data.get("about_company"),
                },
            })

            job["dedupe_key"] = generate_dedupe_key(
                job["source"],
                job["source_job_id"],
                title,
                company
            )

            internships.append(job)

        except Exception as e:
            logger.error("Internshala Parse Error: %s", e)
    
    logger.info(f"Scraped {len(internships)} engineering internships from Internshala.")
    return internships


async def scrape_internshala_detail(url: str) -> dict:
    """Fetch extra fields from internship detail page."""
    try:
        HEADERS = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            response = await client.get(url)
        soup = BeautifulSoup(response.text, "lxml")

        # Who can apply (raw text block)
        who_can_apply = None
        eligibility = []
        wca_div = soup.find("div", class_="who_can_apply")
        if wca_div:
            who_can_apply = wca_div.get_text("\n", strip=True)
            for p in wca_div.find_all("p"):
                text = re.sub(r"^\d+\.\s*|\*\s*", "", p.get_text(strip=True)).strip()
                if text and "Only those candidates" not in text:
                    eligibility.append(text)

        # Other requirements → list of strings
        other_requirements = []
        additional_div = soup.find("div", class_="additional_detail")
        if additional_div:
            for p in additional_div.find_all("p"):
                text = p.get_text(strip=True)
                if text:
                    # strip leading "1. ", "2. " etc
                    text = re.sub(r"^\d+\.\s*", "", text)
                    other_requirements.append(text)

        # Perks → benefits[]
        perks = []
        for h3 in soup.find_all("h3", class_="section_heading"):
            if "Perks" in h3.get_text():
                perks_container = h3.find_next_sibling("div", class_="round_tabs_container")
                if perks_container:
                    for span in perks_container.find_all("span", class_="round_tabs"):
                        perk = span.get_text(strip=True)
                        if perk:
                            perks.append(perk)
                break

        # Number of openings
        openings = None
        for h3 in soup.find_all("h3", class_="section_heading"):
            if "Number of openings" in h3.get_text():
                sib = h3.find_next_sibling("div", class_="text-container")
                if sib:
                    openings_text = sib.get_text(strip=True)
                    try:
                        openings = int(openings_text)
                    except ValueError:
                        openings = None
                break

        # About company
        about_company = None
        about_div = soup.find("div", class_="about_company_text_container")
        if about_div:
            about_company = about_div.get_text(strip=True)

        # Org logo
        org_logo_url = None
        logo_tag = soup.find("img", class_=re.compile(r"company.logo|internship.logo", re.I))
        if logo_tag:
            org_logo_url = logo_tag.get("src")
       
        # Additional information section
        additional_info = []
        for div in soup.find_all("div", class_="section_heading"):
            if "additional information" in div.get_text(strip=True).lower():
                sib = div.find_next_sibling("div")
                if sib:
                    raw_text = sib.get_text("\n", strip=True)
                    for line in raw_text.split("\n"):
                        line = re.sub(r"^\d+\.\s*", "", line).strip()
                        if line:
                            additional_info.append(line)
                break
        
        return {
            "who_can_apply": who_can_apply,
            "other_requirements": other_requirements,
            "perks": perks,
            "openings": openings,
            "about_company": about_company,
            "org_logo_url": org_logo_url,
            "eligibility": eligibility,
            "additional_info": additional_info,
        }

    except Exception as e:
        logger.error("Internshala Detail Scrape Error (%s): %s", url, e)
        return {}


def parse_duration_to_days(duration_display: str) -> int | None:
    """Convert '2 Months' → 60, '3 Weeks' → 21, etc."""
    if not duration_display:
        return None
    duration_display = duration_display.lower()
    match = re.search(r"(\d+)\s*(month|week|day)", duration_display)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    if unit == "month":
        return value * 30
    elif unit == "week":
        return value * 7
    elif unit == "day":
        return value
    return None

if __name__ == "__main__":
    import asyncio
    jobs = asyncio.run(scrape_internshala_engineering())
    print(f"Scraped {len(jobs)} internships from Internshala.")
    print(json.dumps(jobs[:5], indent=2, default=str))
