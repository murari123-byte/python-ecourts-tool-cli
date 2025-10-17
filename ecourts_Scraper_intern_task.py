
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
from pathlib import Path
import json

# Confiming
BASE_URL = "https://services.ecourts.gov.in/ecourtindia_v6/"
OUTPUT_DIR = Path("ecourts_data")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent":(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    )
}

# Case Functions
def fetch_case_html(cnr_number):
    """Fetch case status page HTML"""
    session = requests.Session()
    session.get(f"{BASE_URL}?p=casestatus/index/", headers=HEADERS)
    result = session.post(
        f"{BASE_URL}?p=casestatus/getCaseStatus",
        data={"cnrno": cnr_number},
        headers=HEADERS
    )
    if result.status_code !=200:
        return None, session
    soup=BeautifulSoup(result.text, "lxml")
    return soup, session

def parse_case_listing(soup):
    """Check if case is listed today or tomorrow"""
    today_str =date.today().strftime("%d-%m-%Y")
    tomorrow_str= (date.today() + timedelta(days=1)).strftime("%d-%m-%Y")
    listing_info={"is_listed": False}

    listing_table=soup.find("table", id="listing_table")
    if not listing_table:
        return listing_info

    for row in listing_table.find_all("tr")[1:]:
        columns=[td.get_text(strip=True) for td in row.find_all("td")]
        if len(columns)>=4:
            serial_number, listing_date, court_name, *_ =columns
            if listing_date in {today_str, tomorrow_str}:
                listing_info.update({
                    "is_listed": True,
                    "listing_date": listing_date,
                    "serial_number": serial_number,
                    "court_name": court_name
                })
                break
    return listing_info

def download_case_pdf(soup, session, cnr_number):
    """Download PDF of the case if available"""
    pdf_link_element = soup.find("a", string=lambda x: "PDF" in x if x else False)
    if not pdf_link_element:
        return None
    pdf_url = BASE_URL + pdf_link_element["href"]
    pdf_response = session.get(pdf_url, headers=HEADERS)
    if pdf_response.headers.get("content-type") == "application/pdf":
        pdf_file_path = OUTPUT_DIR / f"case_{cnr_number}.pdf"
        with open(pdf_file_path, "wb") as f:
            f.write(pdf_response.content)
        return pdf_file_path
    return None


# Cause List Functions
def fetch_json(url):
    """Fetch JSON data from eCourts API"""
    try:
        response=requests.get(url, headers=HEADERS)
        return response.json() if response.status_code == 200 else []
    except Exception:
        return []

def fetch_states():
    """Fetch states (with preloaded fallback)"""
    states = fetch_json(f"{BASE_URL}?p=cause_list/get_state_list")
    if not states:
        # Preloaded states if API fails
        states=[
            {"name": "Delhi", "code": "1"},
            {"name": "Karnataka", "code": "2"},
            {"name": "Tamil Nadu", "code": "3"},
            {"name": "Maharashtra", "code": "4"},
            {"name": "Andhra Pradesh", "code": "5"},
            {"name": "Telangana", "code": "6"}
        ]
    return states

def fetch_districts(state_code):
    districts = fetch_json(f"{BASE_URL}?p=cause_list/get_district_list&state_code={state_code}")
    if not districts:
        districts = [{"name": "Default District", "code": "1"}]
    return districts

def fetch_complexes(state_code, district_code):
    complexes = fetch_json(f"{BASE_URL}?p=cause_list/get_complex_list&state_code={state_code}&dist_code={district_code}")
    if not complexes:
        complexes = [{"name": "Main Complex", "code": "1"}]
    return complexes

def fetch_courts(state_code, district_code, complex_code):
    courts=fetch_json(f"{BASE_URL}?p=cause_list/get_court_list&state_code={state_code}&dist_code={district_code}&complex_code={complex_code}")
    if not courts:
        courts=[{"name": "Main Court", "code": "1"}]
    return courts

def download_cause_list_pdf(state_code, district_code, court_code, target_date):
    """Download cause list PDF"""
    url = f"{BASE_URL}?p=cause_list/download_pdf&state_code={state_code}&dist_code={district_code}&court_code={court_code}&date={target_date}"
    response = requests.get(url, headers=HEADERS)
    if response.headers.get("content-type") == "application/pdf":
        pdf_file_path = OUTPUT_DIR / f"cause_{state_code}_{district_code}_{court_code}_{target_date}.pdf"
        with open(pdf_file_path, "wb") as f:
            f.write(response.content)
        return pdf_file_path
    return None


# CLI Helpers
def select_option(prompt, options):
    """CLI selection helper"""
    print(f"\n{prompt}")
    for idx,opt in enumerate(options, 1):
        print(f"{idx}. {opt}")
    while True:
        choice = input("Enter number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice)-1]
        print("Invalid input, try again.")


# Main CLI(Command Line Interface)
def main():
    print("=> eCourts CLI Interactive Tool <=")
    print("1. To Check Case Status by CNR")
    print("2. To Download Cause List PDFs")
    action = input("Select option (1 or 2): ").strip()
    if action=="1":
        cnr_number = input("Enter CNR Number: ").strip()
        soup, session = fetch_case_html(cnr_number)
        if not soup:
            print("Failed to fetch case info.")
            return
        listing_info = parse_case_listing(soup)
        if listing_info["is_listed"]:
            print(f" Case listed on {listing_info['listing_date']}")
            print(f"Serial Number: {listing_info['serial_number']}")
            print(f"Court Name: {listing_info['court_name']}")
            download_pdf = input("Download case PDF? (y/n): ").strip().lower()
            if download_pdf =="y":
                pdf_file= download_case_pdf(soup, session, cnr_number)
                if pdf_file:
                    print(f"PDF downloaded: {pdf_file}")
                else:
                    print("=> No PDF available for this case.")
        else:
            print("=> Case is not listed today or tomorrow.")

    elif action=="2":
        # To Fetch states
        states = fetch_states()
        state_map = {s["name"]: s["code"] for s in states}
        state_name = select_option("Select State:", list(state_map.keys()))
        state_code = state_map[state_name]

        # To Fetch districts
        districts=fetch_districts(state_code)
        district_map={d["name"]: d["code"] for d in districts}
        district_name=select_option("Select District:", list(district_map.keys()))
        district_code=district_map[district_name]

        # To Fetch complexes
        complexes=fetch_complexes(state_code, district_code)
        complex_map={c["name"]: c["code"] for c in complexes}
        complex_name=select_option("Select Court Complex:", list(complex_map.keys()))
        complex_code=complex_map[complex_name]

        # To Fetch courts
        courts=fetch_courts(state_code, district_code, complex_code)
        court_map={c["name"]: c["code"] for c in courts}

        all_courts=input("Download for all courts in complex? (y/n): ").strip().lower()
        if all_courts=="y":
            selected_courts=list(court_map.values())
        else:
            court_name=select_option("Select Court:", list(court_map.keys()))
            selected_courts=[court_map[court_name]]

        # Date input
        input_date=input(f"Enter date (DD-MM-YYYY) [default today {date.today().strftime('%d-%m-%Y')}]: ").strip()
        if not input_date:
            input_date=date.today().strftime("%d-%m-%Y")

        # For Downloading PDFs
        downloaded_files=[]
        for court_code in selected_courts:
            pdf_file=download_cause_list_pdf(state_code, district_code, court_code, input_date)
            if pdf_file:
                downloaded_files.append(pdf_file)

        if downloaded_files:
            print(f"\nDownloaded {len(downloaded_files)} PDFs:")
            for f in downloaded_files:
                print(f"- {f}")
            summary = {
                "state": state_name,
                "district": district_name,
                "complex": complex_name,
                "date": input_date,
                "files": [str(f) for f in downloaded_files]
            }
            summary_file = OUTPUT_DIR / "cause_list_summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=4)
            print(f"\nSummary JSON saved: {summary_file}")
        else:
            print("No PDFs downloaded.")
    else:
        print(" Invalid option selected.")

if __name__ == "__main__":
    main()
