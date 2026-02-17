import requests
from bs4 import BeautifulSoup
import json, os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── CONFIGURATION ──────────────────────────────────────────────
GMAIL_SENDER   = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")  # App Password, not login password
GMAIL_RECEIVER = os.environ.get("GMAIL_RECEIVER")

KEYWORDS = [
    "product manager", "product management", "senior pm",
    "associate pm", "group product manager", "principal pm",
    "director of product", "vp of product", "head of product"
]
SEEN_JOBS_FILE = "seen_jobs.json"

# ── COMPANIES TO MONITOR ───────────────────────────────────────
COMPANY_PAGES = [
    {"company": "Google India",    "url": "https://careers.google.com/jobs/results/?location=India&q=product+manager",            "type": "google"},
    {"company": "Microsoft India", "url": "https://jobs.microsoft.com/en-us/search?q=product+manager&lc=India",                   "type": "microsoft"},
    {"company": "Amazon India",    "url": "https://www.amazon.jobs/en/search?base_query=product+manager&loc_query=India",          "type": "amazon"},
    {"company": "Adobe India",     "url": "https://careers.adobe.com/us/en/search-results?keywords=product+manager&country=India", "type": "generic"},
    {"company": "Flipkart",        "url": "https://www.flipkartcareers.com/#!/joblist",                                            "type": "generic"},
    {"company": "Swiggy",          "url": "https://careers.swiggy.com/#/careers",                                                 "type": "generic"},
    {"company": "Zomato",          "url": "https://www.zomato.com/careers",                                                       "type": "generic"},
    {"company": "PhonePe",         "url": "https://careers.phonepe.com/jobs",                                                     "type": "generic"},
    {"company": "Razorpay",        "url": "https://razorpay.com/jobs/",                                                           "type": "generic"},
    {"company": "Paytm",           "url": "https://paytm.com/care/job-openings",                                                  "type": "generic"},
    {"company": "Meesho",          "url": "https://meesho.io/careers",                                                            "type": "generic"},
    {"company": "CRED",            "url": "https://careers.cred.club/",                                                           "type": "generic"},
    {"company": "Groww",           "url": "https://groww.in/careers",                                                             "type": "generic"},
    {"company": "Ola",             "url": "https://ola.careers/",                                                                 "type": "generic"},
    {"company": "Myntra",          "url": "https://www.myntra.com/careers",                                                       "type": "generic"},
    {"company": "Infosys",         "url": "https://career.infosys.com/jobdesc",                                                   "type": "generic"},
    {"company": "TCS",             "url": "https://www.tcs.com/careers/tcs-careers",                                              "type": "generic"},
    {"company": "Wipro",           "url": "https://careers.wipro.com/careers-home/",                                              "type": "generic"},
]

JOB_BOARDS = [
    {"name": "Naukri",   "type": "naukri"},
    {"name": "LinkedIn", "type": "linkedin"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

# ── HELPERS ────────────────────────────────────────────────────
def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_seen_jobs(seen):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(seen, f, indent=2)

def is_relevant(title):
    return any(kw in title.lower() for kw in KEYWORDS)

# ── EMAIL ──────────────────────────────────────────────────────
def send_email(new_jobs):
    subject = f"🚨 {len(new_jobs)} New PM Job(s) in India — {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    rows = "".join(f"""
        <tr>
          <td style="padding:12px 10px;border-bottom:1px solid #eee;">
            <strong>{j['title']}</strong><br>
            <span style="color:#666;font-size:13px;">{j['company']}</span>
          </td>
          <td style="padding:12px 10px;border-bottom:1px solid #eee;">
            <a href="{j['link']}" style="background:#1a73e8;color:white;padding:6px 14px;border-radius:4px;text-decoration:none;font-size:13px;">View Job</a>
          </td>
        </tr>""" for j in new_jobs)

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:680px;margin:auto;">
      <div style="background:#1a73e8;padding:20px 24px;border-radius:8px 8px 0 0;">
        <h2 style="color:white;margin:0;">🎯 New Product Manager Jobs Found</h2>
        <p style="color:#cce0ff;margin:4px 0 0;">{datetime.now().strftime('%d %B %Y, %I:%M %p')}</p>
      </div>
      <div style="border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px;padding:16px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
          <tr style="background:#f8f9fa;">
            <th style="padding:10px;text-align:left;color:#555;">Job / Company</th>
            <th style="padding:10px;text-align:left;color:#555;">Link</th>
          </tr>{rows}
        </table>
        <p style="color:#aaa;font-size:11px;text-align:center;margin-top:20px;">PM Job Tracker · GitHub Actions · Free Forever</p>
      </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, GMAIL_SENDER, GMAIL_RECEIVER
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_SENDER, GMAIL_PASSWORD)
        s.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
    print(f"✅ Email sent with {len(new_jobs)} jobs.")

# ── SCRAPERS ───────────────────────────────────────────────────
def scrape_google(info):
    jobs = []
    try:
        r = requests.get("https://careers.google.com/api/v3/search/?q=product+manager&location=India&num=20", headers=HEADERS, timeout=15)
        for job in r.json().get("jobs", []):
            title = job.get("title", "")
            if is_relevant(title):
                jid = job.get("id", title)
                jobs.append({"id": f"google_{jid}", "title": title, "company": "Google India",
                              "link": f"https://careers.google.com/jobs/results/{jid}/"})
    except Exception as e:
        print(f"  ⚠️  Google: {e}")
    return jobs

def scrape_amazon(info):
    jobs = []
    try:
        r = requests.get("https://www.amazon.jobs/en/search.json?base_query=product+manager&loc_query=India&job_count=20", headers=HEADERS, timeout=15)
        for job in r.json().get("jobs", []):
            title = job.get("title", "")
            if is_relevant(title):
                jid = str(job.get("id_icims", ""))
                jobs.append({"id": f"amazon_{jid}", "title": title, "company": "Amazon India",
                              "link": f"https://www.amazon.jobs/en/jobs/{jid}"})
    except Exception as e:
        print(f"  ⚠️  Amazon: {e}")
    return jobs

def scrape_microsoft(info):
    jobs = []
    try:
        r = requests.get("https://gcsb.microsoft.com/api/search/V2?q=product+manager&lc=India&l=en_us&pg=1&pgSz=20", headers=HEADERS, timeout=15)
        for job in r.json().get("operationResult", {}).get("result", {}).get("jobs", []):
            title = job.get("title", "")
            if is_relevant(title):
                jid = job.get("jobId", "")
                jobs.append({"id": f"microsoft_{jid}", "title": title, "company": "Microsoft India",
                              "link": f"https://jobs.microsoft.com/en-us/job/{jid}"})
    except Exception as e:
        print(f"  ⚠️  Microsoft: {e}")
    return jobs

def scrape_naukri(board):
    jobs = []
    try:
        r = requests.get(
            "https://www.naukri.com/jobapi/v3/search?noOfResults=20&urlType=search_by_key_loc"
            "&searchType=adv&keyword=product+manager&location=india&jobAge=1&pageNo=1",
            headers={**HEADERS, "appid": "109", "systemid": "109"}, timeout=15)
        for job in r.json().get("jobDetails", []):
            title = job.get("title", "")
            if is_relevant(title):
                jid = str(job.get("jobId", ""))
                co  = job.get("companyName", "Unknown")
                jobs.append({"id": f"naukri_{jid}", "title": title,
                              "company": f"{co} (Naukri)",
                              "link": job.get("jdURL", f"https://www.naukri.com/job-listings-{jid}")})
    except Exception as e:
        print(f"  ⚠️  Naukri: {e}")
    return jobs

def scrape_linkedin(board):
    jobs = []
    try:
        r = requests.get(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=product+manager&location=India&f_TPR=r86400&start=0",
            headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.find_all("li"):
            t = card.find("h3", class_="base-search-card__title")
            l = card.find("a",  class_="base-card__full-link")
            c = card.find("h4", class_="base-search-card__subtitle")
            if t and l:
                title = t.get_text(strip=True)
                link  = l.get("href", "").split("?")[0]
                co    = c.get_text(strip=True) if c else "Unknown"
                jid   = link.split("-")[-1] if link else title[:20]
                if is_relevant(title):
                    jobs.append({"id": f"linkedin_{jid}", "title": title,
                                 "company": f"{co} (LinkedIn)", "link": link})
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
            if is_relevant(text):
                seen_titles.add(text)
                link = tag.get("href") if tag.name == "a" else None
                if link and link.startswith("/"):
                    from urllib.parse import urlparse
                    b = urlparse(info["url"])
                    link = f"{b.scheme}://{b.netloc}{link}"
                if not link or not link.startswith("http"):
                    link = info["url"]
                jobs.append({"id": f"{info['company']}_{text[:50]}".replace(" ","_"),
                             "title": text, "company": info["company"], "link": link})
    except Exception as e:
        print(f"  ⚠️  {info['company']}: {e}")
    return jobs

# ── MAIN ───────────────────────────────────────────────────────
def run():
    print(f"\n{'='*50}\n🔍 PM Job Tracker — {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n{'='*50}")
    seen, new_jobs = load_seen_jobs(), []

    print("\n📋 Company pages...")
    for co in COMPANY_PAGES:
        print(f"  → {co['company']}")
        fn   = {"google": scrape_google, "amazon": scrape_amazon,
                "microsoft": scrape_microsoft}.get(co["type"], scrape_generic)
        for job in fn(co):
            if job["id"] not in seen:
                seen[job["id"]] = datetime.now().isoformat()
                new_jobs.append(job)
                print(f"    ✨ {job['title']}")

    print("\n📋 Job boards...")
    for board in JOB_BOARDS:
        print(f"  → {board['name']}")
        fn = {"naukri": scrape_naukri, "linkedin": scrape_linkedin}.get(board["type"])
        if fn:
            for job in fn(board):
                if job["id"] not in seen:
                    seen[job["id"]] = datetime.now().isoformat()
                    new_jobs.append(job)
                    print(f"    ✨ {job['title']} @ {job['company']}")

    save_seen_jobs(seen)

    if new_jobs:
        print(f"\n📧 Sending email with {len(new_jobs)} new job(s)...")
        send_email(new_jobs)
    else:
        print("\n✅ No new jobs this run.")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    run()