import requests
from bs4 import BeautifulSoup
import json, os, smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from urllib.parse import urlparse

# ── CONFIGURATION ──────────────────────────────────────────────
GMAIL_SENDER   = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
GMAIL_RECEIVER = os.environ.get("GMAIL_RECEIVER")

KEYWORDS = [
    "product manager", "product management", "senior pm",
    "senior product manager", "lead product manager"
]

# Words that indicate a job is NOT in India — used to filter out false positives
EXCLUDE_LOCATIONS = [
    "united states", "usa", "us only", "new york", "san francisco", "seattle",
    "london", "uk only", "united kingdom", "singapore", "dubai", "canada",
    "australia", "germany", "france", "netherlands", "ireland", "poland",
    "mexico", "brazil", "japan", "korea", "china", "hong kong"
]

# Words that confirm India location
INDIA_LOCATIONS = [
    "india", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad",
    "pune", "chennai", "kolkata", "gurugram", "gurgaon", "noida",
    "remote - india", "india remote", "remote india", "apac"
]

SEEN_JOBS_FILE = "seen_jobs.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── COMPANY CAREER PAGES ───────────────────────────────────────
# Top 50 US-listed software companies with India operations
# Listed in order of preference (MNCs first, then Indian tech)
COMPANY_PAGES = [
    # ── Tier 1: Big Tech (strong India presence)
    {
        "company": "Google India",
        "type": "google"
    },
    {
        "company": "Microsoft India",
        "type": "microsoft"
    },
    {
        "company": "Amazon India",
        "type": "amazon"
    },
    {
        "company": "Meta India",
        "url": "https://www.metacareers.com/jobs?offices[0]=India&roles[0]=product_management",
        "type": "generic"
    },
    {
        "company": "Apple India",
        "url": "https://jobs.apple.com/en-us/search?location=india-IND&team=apps-and-frameworks-SFTWR-AF",
        "type": "generic"
    },
    {
        "company": "Salesforce India",
        "url": "https://careers.salesforce.com/en/jobs/?search=product+manager&country=India",
        "type": "generic"
    },
    {
        "company": "Oracle India",
        "url": "https://careers.oracle.com/jobs/#en/sites/jobsearch/jobs?keyword=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "SAP India",
        "url": "https://jobs.sap.com/search/?q=product+manager&locname=India",
        "type": "generic"
    },
    {
        "company": "Adobe India",
        "url": "https://careers.adobe.com/us/en/search-results?keywords=product+manager&country=India",
        "type": "generic"
    },
    {
        "company": "Intuit India",
        "url": "https://jobs.intuit.com/search-jobs/product%20manager/India/28287/1/2/6252001/23.1636/80.2064/50/2",
        "type": "generic"
    },
    {
        "company": "Workday India",
        "url": "https://workday.wd5.myworkdayjobs.com/Workday/jobs?q=product+manager&locations=India",
        "type": "generic"
    },
    {
        "company": "ServiceNow India",
        "url": "https://careers.servicenow.com/careers/jobs?query=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Cisco India",
        "url": "https://jobs.cisco.com/jobs/SearchJobs/product%20manager?listFilterMode=1&totalRecords=90&scrolled=0&location=India",
        "type": "generic"
    },
    {
        "company": "VMware India",
        "url": "https://careers.vmware.com/jobs/search?q=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Nutanix India",
        "url": "https://jobs.jobvite.com/nutanix/search?q=product+manager&l=India",
        "type": "generic"
    },
    {
        "company": "Palo Alto Networks India",
        "url": "https://jobs.paloaltonetworks.com/en/jobs/?search=product+manager&country=India",
        "type": "generic"
    },
    {
        "company": "Qualcomm India",
        "url": "https://careers.qualcomm.com/careers/search?keywords=product+manager&region=India",
        "type": "generic"
    },
    {
        "company": "PayPal India",
        "url": "https://careers.pypl.com/jobs/search?q=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Uber India",
        "url": "https://www.uber.com/global/en/careers/list/?query=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Airbnb India",
        "url": "https://careers.airbnb.com/positions/?location=India&department=product-management",
        "type": "generic"
    },
    {
        "company": "Twilio India",
        "url": "https://careers.twilio.com/jobs?search=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Atlassian India",
        "url": "https://www.atlassian.com/company/careers/all-jobs?team=Product+Management&location=India",
        "type": "generic"
    },
    {
        "company": "Zendesk India",
        "url": "https://jobs.zendesk.com/us/en/search-results?keywords=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Splunk India",
        "url": "https://www.splunk.com/en_us/careers/search-jobs.html?q=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Datadog India",
        "url": "https://careers.datadoghq.com/all-jobs/?search=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "MongoDB India",
        "url": "https://www.mongodb.com/careers/jobs?q=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Elastic India",
        "url": "https://jobs.elastic.co/#/jobs?search=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Freshworks",
        "url": "https://careers.freshworks.com/jobs?q=product+manager&location=India",
        "type": "generic"
    },
    {
        "company": "Zoho",
        "url": "https://careers.zohocorp.com/jobs/Careers?search=product+manager",
        "type": "generic"
    },
    # ── Tier 2: Indian Tech Giants
    {
        "company": "Flipkart",
        "url": "https://www.flipkartcareers.com/#!/joblist",
        "type": "generic"
    },
    {
        "company": "Swiggy",
        "url": "https://careers.swiggy.com/#/careers",
        "type": "generic"
    },
    {
        "company": "Zomato",
        "url": "https://www.zomato.com/careers",
        "type": "generic"
    },
    {
        "company": "PhonePe",
        "url": "https://careers.phonepe.com/jobs",
        "type": "generic"
    },
    {
        "company": "Razorpay",
        "url": "https://razorpay.com/jobs/",
        "type": "generic"
    },
    {
        "company": "Paytm",
        "url": "https://paytm.com/care/job-openings",
        "type": "generic"
    },
    {
        "company": "Meesho",
        "url": "https://meesho.io/careers",
        "type": "generic"
    },
    {
        "company": "CRED",
        "url": "https://careers.cred.club/",
        "type": "generic"
    },
    {
        "company": "Groww",
        "url": "https://groww.in/careers",
        "type": "generic"
    },
    {
        "company": "Zepto",
        "url": "https://www.zepto.com/careers",
        "type": "generic"
    },
    {
        "company": "Ola",
        "url": "https://ola.careers/",
        "type": "generic"
    },
    {
        "company": "Myntra",
        "url": "https://www.myntra.com/careers",
        "type": "generic"
    },
    {
        "company": "InMobi",
        "url": "https://www.inmobi.com/company/careers/",
        "type": "generic"
    },
    {
        "company": "Browserstack",
        "url": "https://www.browserstack.com/careers",
        "type": "generic"
    },
    {
        "company": "Postman",
        "url": "https://www.postman.com/company/careers/",
        "type": "generic"
    },
    {
        "company": "Druva",
        "url": "https://www.druva.com/about/careers/",
        "type": "generic"
    },
    {
        "company": "Infosys",
        "url": "https://career.infosys.com/jobsearch/joblist",
        "type": "generic"
    },
    {
        "company": "TCS",
        "url": "https://www.tcs.com/careers/tcs-careers",
        "type": "generic"
    },
    {
        "company": "Wipro",
        "url": "https://careers.wipro.com/careers-home/",
        "type": "generic"
    },
    {
        "company": "HCLTech",
        "url": "https://www.hcltech.com/careers",
        "type": "generic"
    },
    {
        "company": "Tech Mahindra",
        "url": "https://careers.techmahindra.com/Search.aspx",
        "type": "generic"
    },
]

JOB_BOARDS = [
    {"name": "Naukri",   "type": "naukri"},
    {"name": "LinkedIn", "type": "linkedin"},
]

# ── HELPERS ────────────────────────────────────────────────────

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_seen_jobs(seen):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(seen, f, indent=2)

def is_relevant_title(title):
    return any(kw in title.lower() for kw in KEYWORDS)

def is_india_location(location_text):
    """Return True if location confirms India, False if it confirms elsewhere, None if unknown."""
    text = location_text.lower()
    for loc in EXCLUDE_LOCATIONS:
        if loc in text:
            return False
    for loc in INDIA_LOCATIONS:
        if loc in text:
            return True
    return None  # Unknown — will be included with a flag

def normalize_link(link):
    """Normalize a job link to use as dedup key — strip tracking params."""
    if not link:
        return ""
    try:
        parsed = urlparse(link)
        # Keep only scheme + netloc + path
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    except:
        return link.split("?")[0].rstrip("/")

def deduplicate(jobs):
    """Remove duplicate jobs based on normalized link."""
    seen_links = {}
    result = []
    for job in jobs:
        key = normalize_link(job["link"])
        if key and key not in seen_links:
            seen_links[key] = True
            result.append(job)
    return result

# ── EMAIL ──────────────────────────────────────────────────────

def send_email(new_jobs):
    subject = f"🎯 {len(new_jobs)} New PM Job(s) in India — {datetime.now().strftime('%d %b %Y, %I:%M %p')}"

    rows = "".join(f"""
        <tr>
          <td style="padding:12px 10px;border-bottom:1px solid #eee;">
            <strong style="font-size:15px;">{j['title']}</strong><br>
            <span style="color:#666;font-size:13px;">{j['company']}</span>
            {"<br><span style='color:#e67e22;font-size:12px;'>📍 " + j.get('location','') + "</span>" if j.get('location') else ""}
          </td>
          <td style="padding:12px 10px;border-bottom:1px solid #eee;white-space:nowrap;">
            <a href="{j['link']}" style="background:#1a73e8;color:white;padding:6px 14px;
               border-radius:4px;text-decoration:none;font-size:13px;">View Job</a>
          </td>
        </tr>""" for j in new_jobs)

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:680px;margin:auto;">
      <div style="background:#1a73e8;padding:20px 24px;border-radius:8px 8px 0 0;">
        <h2 style="color:white;margin:0;">🎯 New Product Manager Jobs in India</h2>
        <p style="color:#cce0ff;margin:4px 0 0;">{datetime.now().strftime('%d %B %Y, %I:%M %p')}</p>
      </div>
      <div style="border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px;padding:16px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
          <tr style="background:#f8f9fa;">
            <th style="padding:10px;text-align:left;color:#555;font-size:13px;">Job / Company</th>
            <th style="padding:10px;text-align:left;color:#555;font-size:13px;">Link</th>
          </tr>{rows}
        </table>
        <p style="color:#aaa;font-size:11px;text-align:center;margin-top:20px;">
          PM Job Tracker · GitHub Actions · Free Forever
        </p>
      </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = GMAIL_RECEIVER
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_SENDER, GMAIL_PASSWORD)
        s.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
    print(f"✅ Email sent with {len(new_jobs)} jobs.")

# ── SCRAPERS ───────────────────────────────────────────────────

def scrape_google(info):
    jobs = []
    try:
        r = requests.get(
            "https://careers.google.com/api/v3/search/"
            "?q=product+manager&location=India&num=20&page=1",
            headers=HEADERS, timeout=15)
        for job in r.json().get("jobs", []):
            title    = job.get("title", "")
            location = " ".join(job.get("locations", []))
            if not is_relevant_title(title):
                continue
            india_check = is_india_location(location)
            if india_check == False:   # Explicitly not India
                continue
            jid = job.get("id", title)
            jobs.append({
                "id":       f"google_{jid}",
                "title":    title,
                "company":  "Google India",
                "location": location,
                "link":     f"https://careers.google.com/jobs/results/{jid}/"
            })
    except Exception as e:
        print(f"  ⚠️  Google: {e}")
    return jobs


def scrape_amazon(info):
    jobs = []
    try:
        r = requests.get(
            "https://www.amazon.jobs/en/search.json"
            "?base_query=product+manager&loc_query=India&job_count=20&offset=0",
            headers=HEADERS, timeout=15)
        for job in r.json().get("jobs", []):
            title    = job.get("title", "")
            location = job.get("location", "")
            if not is_relevant_title(title):
                continue
            india_check = is_india_location(location)
            if india_check == False:
                continue
            jid = str(job.get("id_icims", ""))
            jobs.append({
                "id":       f"amazon_{jid}",
                "title":    title,
                "company":  "Amazon India",
                "location": location,
                "link":     f"https://www.amazon.jobs/en/jobs/{jid}"
            })
    except Exception as e:
        print(f"  ⚠️  Amazon: {e}")
    return jobs


def scrape_microsoft(info):
    jobs = []
    try:
        # Updated Microsoft API endpoint
        r = requests.get(
            "https://jobs.microsoft.com/api/jobs"
            "?q=product+manager&l=India&pg=1&pgSz=20",
            headers=HEADERS, timeout=15)
        data = r.json()
        for job in data.get("operationResult", {}).get("result", {}).get("jobs",
              data.get("value", [])):
            title    = job.get("title", "")
            location = job.get("primaryWorkLocation", job.get("location", ""))
            if not is_relevant_title(title):
                continue
            india_check = is_india_location(str(location))
            if india_check == False:
                continue
            jid = job.get("jobId", job.get("id", ""))
            jobs.append({
                "id":       f"microsoft_{jid}",
                "title":    title,
                "company":  "Microsoft India",
                "location": str(location),
                "link":     f"https://jobs.microsoft.com/en-us/job/{jid}"
            })
    except Exception as e:
        print(f"  ⚠️  Microsoft: {e}")
    return jobs


def scrape_naukri(board):
    jobs = []
    try:
        r = requests.get(
            "https://www.naukri.com/jobapi/v3/search"
            "?noOfResults=30&urlType=search_by_key_loc"
            "&searchType=adv&keyword=product+manager"
            "&location=india&jobAge=1&pageNo=1",
            headers={**HEADERS, "appid": "109", "systemid": "109"},
            timeout=15)
        for job in r.json().get("jobDetails", []):
            title    = job.get("title", "")
            location = job.get("placeholders", [{}])[0].get("label", "") if job.get("placeholders") else ""
            if not is_relevant_title(title):
                continue
            india_check = is_india_location(location + " india")  # Naukri is India-only
            if india_check == False:
                continue
            jid = str(job.get("jobId", ""))
            co  = job.get("companyName", "Unknown")
            jobs.append({
                "id":       f"naukri_{jid}",
                "title":    title,
                "company":  f"{co} (Naukri)",
                "location": location,
                "link":     job.get("jdURL", f"https://www.naukri.com/job-listings-{jid}")
            })
    except Exception as e:
        print(f"  ⚠️  Naukri: {e}")
    return jobs


def scrape_linkedin(board):
    jobs = []
    try:
        r = requests.get(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=product+manager&location=India&f_TPR=r7200&start=0",
            headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("li"):
            t = card.find("h3", class_="base-search-card__title")
            l = card.find("a",  class_="base-card__full-link")
            c = card.find("h4", class_="base-search-card__subtitle")
            loc_tag = card.find("span", class_="job-search-card__location")
            if not (t and l):
                continue
            title    = t.get_text(strip=True)
            link     = l.get("href", "").split("?")[0]
            company  = c.get_text(strip=True) if c else "Unknown"
            location = loc_tag.get_text(strip=True) if loc_tag else ""
            if not is_relevant_title(title):
                continue
            india_check = is_india_location(location)
            if india_check == False:
                continue
            jid = link.split("-")[-1] if link else title[:20]
            jobs.append({
                "id":       f"linkedin_{jid}",
                "title":    title,
                "company":  f"{company} (LinkedIn)",
                "location": location,
                "link":     link
            })
    except Exception as e:
        print(f"  ⚠️  LinkedIn: {e}")
    return jobs


def scrape_generic(info):
    jobs, seen_titles = [], set()
    try:
        r    = requests.get(info["url"], headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup.find_all(["a", "h2", "h3", "h4", "li", "div", "span"]):
            text = tag.get_text(strip=True)
            if not (10 < len(text) < 120) or text in seen_titles:
                continue
            if not is_relevant_title(text):
                continue
            # For generic pages we trust the company's India-specific URL
            # but still reject if text itself mentions another country
            if is_india_location(text) == False:
                continue
            seen_titles.add(text)
            link = tag.get("href") if tag.name == "a" else None
            if link and link.startswith("/"):
                b    = urlparse(info["url"])
                link = f"{b.scheme}://{b.netloc}{link}"
            if not link or not link.startswith("http"):
                link = info["url"]
            jobs.append({
                "id":       f"{info['company']}_{text[:50]}".replace(" ", "_"),
                "title":    text,
                "company":  info["company"],
                "location": "India",
                "link":     link
            })
    except Exception as e:
        print(f"  ⚠️  {info['company']}: {e}")
    return jobs


# ── MAIN ───────────────────────────────────────────────────────

def run():
    print(f"\n{'='*55}")
    print(f"🔍 PM Job Tracker — {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
    print(f"{'='*55}")

    seen      = load_seen_jobs()
    all_jobs  = []   # Collect ALL jobs first (company pages + boards)

    # ── Step 1: Company career pages (higher priority)
    print("\n📋 Checking company career pages...")
    for co in COMPANY_PAGES:
        print(f"  → {co['company']}")
        fn = {
            "google":    scrape_google,
            "amazon":    scrape_amazon,
            "microsoft": scrape_microsoft,
        }.get(co["type"], scrape_generic)
        all_jobs.extend(fn(co))

    # ── Step 2: Job boards
    print("\n📋 Checking job boards...")
    for board in JOB_BOARDS:
        print(f"  → {board['name']}")
        fn = {"naukri": scrape_naukri, "linkedin": scrape_linkedin}.get(board["type"])
        if fn:
            all_jobs.extend(fn(board))

    # ── Step 3: Deduplicate across ALL sources by normalized link
    all_jobs = deduplicate(all_jobs)
    print(f"\n🔗 After deduplication: {len(all_jobs)} unique jobs")

    # ── Step 4: Filter to only new jobs
    new_jobs = []
    for job in all_jobs:
        if job["id"] not in seen:
            seen[job["id"]] = datetime.now().isoformat()
            new_jobs.append(job)
            print(f"  ✨ NEW: {job['title']} @ {job['company']} [{job.get('location','')}]")

    save_seen_jobs(seen)

    # ── Step 5: Send email
    print(f"\n{'─'*55}")
    if new_jobs:
        print(f"📧 {len(new_jobs)} new job(s) found! Sending email...")
        send_email(new_jobs)
    else:
        print("✅ No new jobs this run. All quiet.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run()
