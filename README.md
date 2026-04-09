# 🔍 prospect.py

> **Worldwide lead generation from OpenStreetMap — no API key, no cost.**

`prospect.py` scrapes [OpenStreetMap](https://www.openstreetmap.org/) via the [Overpass API](https://overpass-api.de/) to collect local businesses **without a website**: restaurants, hair salons, mechanics, dentists, tattoo studios, and hundreds of other categories. Results are exported as a clean CSV file ready to hand to a client.

Works in **France, USA, India, UK, Germany**, and anywhere else OSM has data.

---

## ✨ Features

- 🌍 Worldwide — works with any city, region, or country
- 📞 Phone numbers normalized to international E.164 format (`+1…`, `+33…`, `+91…`)
- 📧 Email addresses captured and validated
- 🏷️ 150+ business categories auto-translated to English
- 🔄 Auto-expands search radius until quota is met
- 🚫 Filters out businesses that already have a website (configurable)
- 🔢 Auto-numbered output files (`prospect1.csv`, `prospect2.csv`…)
- ♻️ Phone-level deduplication (no two rows for the same business)
- ⚡ Retry logic with exponential backoff on Overpass timeouts

---

## 📦 Installation

**Requirements:** Python 3.10+

```bash
# 1. Clone the repo
git clone https://github.com/foudreeeee/prospect-generator.git
cd prospect

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### Dependencies

| Package | Required | Purpose |
|---|---|---|
| `requests` | ✅ | Nominatim geocoding |
| `pandas` | ✅ | CSV export |
| `overpy` | ✅ | Overpass API client |
| `phonenumbers` | ⭐ Recommended | Accurate E.164 phone parsing |
| `tqdm` | ⭐ Recommended | Progress bar |

---

## 🚀 Quick Start

```bash
# 200 leads around Austin, Texas
python prospect.py --place "Austin, Texas" --sample 200 --country US

# 100 leads in Mumbai (no address required)
python prospect.py --place "Mumbai, India" --sample 100 --country IN --allow-no-address

# 150 leads in London, only restaurants and cafés
python prospect.py --place "London, UK" --sample 150 --country GB --categories "restaurant,cafe"

# 50 leads via GPS coordinates
python prospect.py --latlon 48.8566 2.3522 --sample 50 --country FR

# Only leads that have an email address
python prospect.py --place "Berlin, Germany" --sample 80 --country DE --require-email --allow-no-address
```

Output files are saved in `prospects_found/prospect1.csv`, `prospect2.csv`, etc.

---

## ⚙️ All Options

| Flag | Default | Description |
|---|---|---|
| `--place NAME` | — | City / region name (geocoded automatically) |
| `--latlon LAT LON` | — | Explicit GPS center coordinates |
| `--sample N` | *(required)* | Number of leads to collect |
| `--country CODE` | `FR` | ISO country code for phone parsing (`US`, `IN`, `GB`, `DE`…) |
| `--dist-km N` | `5` | Starting search radius in km |
| `--max-dist-km N` | `100` | Maximum search radius in km |
| `--output-dir PATH` | `prospects_found` | Output folder |
| `--categories LIST` | *(all)* | Comma-separated category keywords (see below) |
| `--allow-no-phone` | off | Include businesses without a phone number |
| `--allow-no-name` | off | Include businesses without a name |
| `--allow-no-address` | off | Include businesses without an address |
| `--require-email` | off | Only include businesses with an email |
| `--allow-with-website` | off | Include businesses that already have a website |

---

## 🏷️ Category Keywords

Pass one or more keywords to `--categories` to narrow the search:

```
restaurant, cafe, bar, bakery, butcher, grocery, florist, hairdresser,
nail, tattoo, spa, massage, gym, yoga, dance, cinema, hotel, vet,
dentist, doctor, pharmacy, optician, therapist, lawyer, accountant,
architect, insurance, realtor, driving, tailor, laundry, locksmith,
plumber, electrician, photographer, printer, travel, car, bike,
brewery, winery, museum, childcare, consulting ...
```

Multiple keywords: `--categories "restaurant,bakery,cafe"`

---

## 📄 Output Format

Each run creates a new numbered file in `prospects_found/`:

| Column | Description |
|---|---|
| `Name` | Business name |
| `Category` | Business type (e.g. *Hair Salon*, *Restaurant*) |
| `Address` | Full postal address |
| `Phone` | Phone number(s) in E.164 format |
| `Email` | Email address (if available in OSM) |

Files use **UTF-8 BOM** encoding so they open correctly in Excel and LibreOffice on all platforms without any import settings.

---

## 🌐 Country Codes

Use the standard [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code:

| Country | Code |
|---|---|
| France | `FR` |
| United States | `US` |
| India | `IN` |
| United Kingdom | `GB` |
| Germany | `DE` |
| Spain | `ES` |
| Italy | `IT` |
| Canada | `CA` |
| Australia | `AU` |
| Brazil | `BR` |

---

## ❓ FAQ

**Why are there fewer results than my `--sample` target?**
OSM data density varies by location. Dense cities return quotas quickly; rural areas may return fewer businesses. Try `--allow-no-address` or `--allow-no-phone` to relax filters.

**Can I run it multiple times for the same city?**
Yes. Each run creates a new numbered file (`prospect1.csv`, `prospect2.csv`…). Phone-level deduplication prevents duplicates *within* a single run, but not across runs.

**Is this legal?**
OpenStreetMap data is open under the [ODbL licence](https://opendatacommons.org/licenses/odbl/). Any redistribution of the data must credit OpenStreetMap contributors.

**Does it work without `phonenumbers`?**
Yes, with a basic fallback. Numbers may be less precisely normalized. Install `phonenumbers` for full E.164 accuracy across all countries.

---

## 📁 Project Structure

```
prospect/
├── prospect.py          # Main script
├── requirements.txt     # Dependencies
├── README.md            # This file
└── prospects_found/     # Output folder (auto-created)
    ├── prospect1.csv
    └── prospect2.csv
```

---

## 🗺️ Data Source

All data comes from **[OpenStreetMap](https://www.openstreetmap.org/)** via the **[Overpass API](https://overpass-api.de/)** — both are free, open, and require no API key.

Data quality depends on local OSM contributor activity. Major cities worldwide are well-covered.

---

## 📜 License

MIT License — free for personal and commercial use.
Data is © OpenStreetMap contributors, licensed under [ODbL](https://opendatacommons.org/licenses/odbl/).

---

## 🖥️ GUI (Streamlit)

A graphical interface is available:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

### Interface overview
- **Sidebar** — location, target count, country code, radius, category filter
- **Fields panel** — checkboxes for Phone, Email, Address, Website filter
  - ✅ Checked = field is required + column appears in CSV
  - ☐ Unchecked = field is ignored + column removed from CSV
- **Results table** — live preview with stats
- **Download button** — export CSV directly from the browser
