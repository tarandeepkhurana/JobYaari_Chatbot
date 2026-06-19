import asyncio
import json
import logging
import re
import uuid
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.scraper.intershala.engineering import (
    parse_duration_to_days,
    scrape_internshala_detail,
)
from src.utils.scraper_utils import (
    create_base_job,
    generate_dedupe_key,
    parse_location,
    parse_posted_relative,
    parse_salary_range,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("intershala.android_app_development")


async def scrape_internshala_android_app_development():
    url = "https://internshala.com/internships/android-app-development-internship/"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()

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
                stipend_tag.get_text(strip=True).replace("Ã¢â€šÂ¹", "Rs.")
                if stipend_tag
                else None
            )

            duration = None
            for item in card.find_all("div", class_="row-1-item"):
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
            skills = list(dict.fromkeys(skills))

            posted_div = card.find("div", class_=re.compile(r"status-"))
            posted = posted_div.get_text(" ", strip=True) if posted_div else None

            ppo_div = card.find("div", class_="ppo_status")
            ppo = ppo_div.get_text(" ", strip=True) if ppo_div else None

            internship_id = card.get("internshipid")
            detail_data = await scrape_internshala_detail(link) if link else {}

            stipend_min, stipend_max, stipend_display = parse_salary_range(stipend_text)
            cities, work_mode, is_remote = parse_location(location)

            job = create_base_job()
            job.update(
                {
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
                    "categories": [
                        "android app development",
                        "mobile app development"
                    ],
                    "eligibility": detail_data.get("eligibility", []),
                    "benefits": detail_data.get("perks", []),
                    "work_functions": [
                        line.strip()
                        for line in (desc or "").split("\n")
                        if line.strip() and re.match(r"^\d+\.", line.strip())
                    ],
                    "posted_at": parse_posted_relative(posted),
                    "embedding_text": (
                        f"{title} {company} "
                        f"{desc or ''} "
                        f"{' '.join(skills)} "
                        f"{' '.join(detail_data.get('other_requirements', []))} "
                        "android app development mobile app development kotlin java "
                        "android studio firebase"
                    ).strip(),
                    "raw_payload": {},
                    "extra_metadata": {
                        "posted_text": posted,
                        "ppo_info": ppo,
                        "who_can_apply": detail_data.get("who_can_apply"),
                        "other_requirements": detail_data.get("other_requirements", []),
                        "additional_info": detail_data.get("additional_info", []),
                        "openings": detail_data.get("openings"),
                        "about_company": detail_data.get("about_company"),
                    },
                }
            )

            job["dedupe_key"] = generate_dedupe_key(
                job["source"],
                job["source_job_id"],
                title,
                company,
            )

            internships.append(job)

        except Exception as exc:
            logger.error("Internshala Android App Development Parse Error: %s", exc)

    logger.info(
        "Scraped %d android app development internships from Internshala.",
        len(internships),
    )
    return internships


if __name__ == "__main__":
    jobs = asyncio.run(scrape_internshala_android_app_development())
    print(f"Scraped {len(jobs)} android app development internships from Internshala.")
    print(json.dumps(jobs[:5], indent=2, default=str))
