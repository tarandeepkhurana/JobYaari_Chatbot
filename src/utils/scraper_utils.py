import re
import hashlib
from datetime import datetime, timedelta, UTC

# ============================================================
# BASE JOB TEMPLATE
# ============================================================

def create_base_job():
    return {
        "source": None,
        "source_job_id": None,
        "source_url": None,
        "application_url": None,

        "title": None,
        "description": None,
        "job_type": None,
        "work_mode": None,
        "remote": False,

        "org_name": None,
        "org_logo_url": None,
        "org_size": None,

        "state": None,
        "country": "India",

        "salary_min": None,
        "salary_max": None,
        "salary_currency": "INR",
        "salary_period": None,
        "salary_display": None,
        "is_paid": True,

        "stipend_min": None,
        "stipend_max": None,
        "stipend_display": None,

        "experience_min_years": None,
        "experience_max_years": None,
        "experience_label": None,

        "duration_display": None,
        "duration_days": None,

        "skills": [],
        "categories": [],
        "eligibility": [],
        "benefits": [],
        "work_functions": [],

        "posted_at": None,
        "expires_at": None,

        "dedupe_key": None,
        "status": "active",
        "is_active": True,

        "embedding_text": None,

        "raw_payload": {},
        "extra_metadata": {},
    }


def parse_location(location: str):

    if not location:
        return [], "onsite", False

    location_lower = location.lower()

    # defaults
    work_mode = "onsite"
    remote = False

    # remote
    if "work from home" in location_lower:
        work_mode = "remote"
        remote = True

    # hybrid
    elif "hybrid" in location_lower:
        work_mode = "hybrid"

    # remove brackets metadata
    clean_location = re.sub(r"\(.*?\)", "", location)
 
    # split cities
    cities = [
        city.strip().lower()
        for city in clean_location.split(",")
        if city.strip()
    ]
    
    if remote:
        cities = []
        
    return cities, work_mode, remote

def generate_dedupe_key(source, source_job_id, title, org):
    raw = f"{source}|{source_job_id}|{title}|{org}"
    return hashlib.md5(raw.encode()).hexdigest()


def parse_salary_range(text):
    """
    Extract salary/stipend range from strings.

    Returns:
        min_salary, max_salary, display
    """

    if not text:
        return None, None, None

    cleaned = text.replace(",", "")

    numbers = re.findall(r"\d+", cleaned)

    if not numbers:
        return None, None, text

    numbers = [int(n) for n in numbers]

    if len(numbers) == 1:
        return numbers[0], numbers[0], text

    return min(numbers), max(numbers), text


def parse_experience(text):
    """
    Examples:
    Fresher
    1+ Years
    2-4 Years
    """

    if not text:
        return None, None, None

    text = text.strip()

    if "fresher" in text.lower():
        return 0.0, 0.0, "Fresher"

    nums = re.findall(r"\d+(?:\.\d+)?", text)

    if not nums:
        return None, None, text

    nums = [float(x) for x in nums]

    if len(nums) == 1:
        return nums[0], nums[0], text

    return min(nums), max(nums), text


def parse_date(date_str):
    """
    Supports:
    07/05/2026
    18-05-2026
    """

    if not date_str:
        return None

    date_str = date_str.strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            pass

    return None


def parse_posted_relative(text):
    """
    Example:
    3 days ago
    """

    if not text:
        return None

    text = text.lower()

    now = datetime.now(UTC)

    match = re.search(r"(\d+)\s+day", text)
    if match:
        return now - timedelta(days=int(match.group(1)))

    match = re.search(r"(\d+)\s+hour", text)
    if match:
        return now - timedelta(hours=int(match.group(1)))

    return now


def normalize_work_mode(value):
    if not value:
        return None

    value = value.lower()

    if "remote" in value or "online" in value:
        return "remote"

    if "hybrid" in value:
        return "hybrid"

    if "office" in value:
        return "in_office"

    return value

if __name__ == "__main__":
    # Test cases for parse_location
    test_locations = [
        "Mumbai (Hybrid)",
        "Hyderabad, mumbai, Bangalore (Hybrid)",
        "Work From Home",
    ]

    for loc in test_locations:
        cities, work_mode, remote = parse_location(loc)
        print(f"Input: {loc}")
        print(f"Cities: {cities}, Work Mode: {work_mode}, Remote: {remote}")
        print("-" * 50)
