# Python eCourts CLI Tool

**A Python command-line tool to fetch case listings and cause lists from [eCourts](https://services.ecourts.gov.in/ecourtindia_v6/).**

## Features

- Check **case status by CNR number**.
- Shows **serial number**, **court name**, and **listing date** if the case is listed today or tomorrow.
- Optionally download **case PDF** if available.
- Download **entire cause list PDFs** for a state, district, court complex, and date.
- Outputs results as **JSON and PDF files**.
- CLI-based tool, no GUI required.

## Requirements

- Python 3.10 or above
- Install dependencies:

```bash
pip install requests beautifulsoup4 lxml
