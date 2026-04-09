#!/usr/bin/env python3
"""
app.py – Prospect Generator  (Streamlit GUI)
Run with:  streamlit run app.py
"""
from __future__ import annotations

import io
import math
import re
import time
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import pandas as pd
import requests
import streamlit as st

try:
    import phonenumbers
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False

try:
    import overpy
    HAS_OVERPY = True
except ImportError:
    HAS_OVERPY = False

# ──────────────────────────────────────────────────────────────────────────────
# Page config  (MUST be first Streamlit call)
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Prospect Generator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header   { visibility: hidden; }

    /* ── Background ── */
    .stApp { background: #f1f5f9; }

    /* ── Hero ── */
    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e40af 55%, #3b82f6 100%);
        border-radius: 18px;
        padding: 38px 44px 30px;
        margin-bottom: 30px;
        color: white;
        box-shadow: 0 10px 40px rgba(30,64,175,0.25);
    }
    .hero h1 { font-size: 2.2rem; font-weight: 800; margin: 0 0 6px; letter-spacing: -0.02em; }
    .hero p  { font-size: 1.05rem; opacity: 0.80; margin: 0; }

    /* ── Section label ── */
    .section-label {
        font-size: 0.72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.1em;
        color: #94a3b8; margin: 24px 0 12px;
    }

    /* ── Field cards (visual indicator only – checkbox is native) ── */
    .fcard {
        border-radius: 14px;
        padding: 20px 16px 14px;
        text-align: center;
        border: 2.5px solid;
        transition: box-shadow .15s;
    }
    .fcard:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.09); }
    .fcard-icon  { font-size: 2.2rem; line-height: 1; margin-bottom: 10px; }
    .fcard-title { font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-bottom: 5px; }
    .fcard-desc  { font-size: 0.74rem; color: #64748b; line-height: 1.5; margin-bottom: 12px; }
    .fcard-badge {
        display: inline-block;
        border-radius: 999px;
        padding: 4px 14px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 2px;
    }

    /* ── Checkbox override: bigger + colored ── */
    [data-testid="stCheckbox"] {
        justify-content: center;
        margin-top: 2px !important;
    }
    [data-testid="stCheckbox"] input[type="checkbox"] {
        width: 20px !important;
        height: 20px !important;
        accent-color: #2563eb;
        cursor: pointer;
        flex-shrink: 0;
    }
    [data-testid="stCheckbox"] label {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #334155 !important;
        cursor: pointer;
    }
    [data-testid="stCheckbox"] label p {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #334155 !important;
    }

    /* ── Stat pills ── */
    .stats-row { display:flex; gap:12px; flex-wrap:wrap; margin-top:8px; }
    .stat-pill  {
        border-radius:999px; padding:6px 16px;
        font-size:0.85rem; font-weight:700;
        background:#eff6ff; border:1.5px solid #bfdbfe; color:#1d4ed8;
    }
    .stat-pill.green  { background:#f0fdf4; border-color:#86efac; color:#15803d; }
    .stat-pill.purple { background:#faf5ff; border-color:#d8b4fe; color:#7c3aed; }
    .stat-pill.orange { background:#fff7ed; border-color:#fed7aa; color:#c2410c; }

    /* ── Card wrapper (results section) ── */
    .rcard {
        background:white; border-radius:14px; padding:20px 24px 16px;
        border:1px solid #e2e8f0; box-shadow:0 2px 8px rgba(0,0,0,0.04);
        margin-bottom:16px;
    }
    .rcard-title {
        font-size:0.72rem; font-weight:700; text-transform:uppercase;
        letter-spacing:.1em; color:#94a3b8; margin-bottom:12px;
    }

    /* ── Buttons ── */
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #2563eb, #1e40af);
        color: white; border: none; border-radius: 10px;
        padding: 0.65rem 2rem; font-size: 1rem; font-weight: 700;
        box-shadow: 0 4px 16px rgba(37,99,235,0.35);
        transition: transform .1s, box-shadow .1s;
    }
    div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 24px rgba(37,99,235,0.42);
    }
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #059669, #047857) !important;
        color: white !important; border: none !important;
        border-radius: 10px !important; font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(5,150,105,0.3) !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] { background: #0f172a !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] .stMarkdown hr { border-color: #334155; }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] select,
    [data-testid="stSidebar"] textarea {
        background: #1e293b !important;
        color: #f1f5f9 !important;
        border-color: #334155 !important;
    }

    /* ── Status / expander panel ── */
    /* Theme config.toml handles base text color.
       These rules only add background styling. */
    [data-testid="stStatusWidget"] > div,
    [data-testid="stExpander"] > details {
        background: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 10px !important;
    }
    /* Belt-and-suspenders: force text dark inside status */
    [data-testid="stStatusWidget"] p,
    [data-testid="stStatusWidget"] span,
    [data-testid="stStatusWidget"] li,
    [data-testid="stStatusWidget"] div { color: #1e293b !important; }

    /* ── Info box ── */
    .info-box {
        background: #f0fdf4; border: 1.5px solid #86efac;
        border-radius: 10px; padding: 12px 18px;
        font-size: 0.85rem; color: #166534; margin-top: 12px; font-weight: 500;
    }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# OSM DATA
# ──────────────────────────────────────────────────────────────────────────────
OSM_CATEGORY_KEYS = [
    "shop","office","amenity","craft","tourism",
    "leisure","healthcare","service","rental","sport","club",
]

CATEGORIES_EN: Dict[str, str] = {
    "bakery":"Bakery","butcher":"Butcher","supermarket":"Supermarket",
    "convenience":"Convenience Store","greengrocer":"Greengrocer",
    "fishmonger":"Fishmonger","deli":"Deli","confectionery":"Confectionery",
    "pastry":"Pastry Shop","beverages":"Beverages","wine":"Wine Shop",
    "alcohol":"Alcohol Store","tea":"Tea Shop","coffee":"Coffee Shop",
    "chocolate":"Chocolate Shop","cheese":"Cheese Shop","health_food":"Health Food",
    "organic":"Organic Store","farm":"Farm Shop","restaurant":"Restaurant",
    "cafe":"Café","bar":"Bar","pub":"Pub","fast_food":"Fast Food",
    "ice_cream":"Ice Cream Shop","biergarten":"Beer Garden","nightclub":"Nightclub",
    "hairdresser":"Hair Salon","beauty":"Beauty Salon","cosmetics":"Cosmetics",
    "nail_salon":"Nail Salon","tattoo":"Tattoo & Piercing","massage":"Massage / Spa",
    "tanning_salon":"Tanning Salon","sauna":"Sauna","spa":"Spa",
    "clothes":"Clothing Store","shoes":"Shoe Store","jewelry":"Jewelry Store",
    "optician":"Optician","florist":"Florist","accessories":"Accessories",
    "bag":"Bags & Luggage","fabric":"Fabric & Textiles",
    "furniture":"Furniture Store","hardware":"Hardware Store","garden":"Garden Center",
    "kitchen":"Kitchen Store","bathroom":"Bathroom","tiles":"Tiles & Flooring",
    "carpet":"Carpet & Rugs","curtain":"Curtains & Blinds","lighting":"Lighting",
    "paint":"Paint Store","heating":"Heating & Energy",
    "electronics":"Electronics","mobile_phone":"Mobile Phone Store",
    "computer":"Computer Store","video_games":"Video Games","appliance":"Appliances",
    "books":"Bookstore","stationery":"Stationery","newsagent":"Newsagent",
    "music":"Music Store","musical_instrument":"Musical Instruments",
    "art":"Art Gallery","hobby":"Hobby Shop","toys":"Toy Store",
    "gift":"Gift Shop","antiques":"Antiques","second_hand":"Thrift Store",
    "cinema":"Cinema","theatre":"Theatre","arts_centre":"Arts Centre",
    "library":"Library","casino":"Casino","escape_game":"Escape Room",
    "bowling_alley":"Bowling","miniature_golf":"Mini Golf",
    "golf_course":"Golf Course","climbing":"Climbing Gym","ice_rink":"Ice Rink",
    "fitness_centre":"Fitness Center / Gym","sports_centre":"Sports Center",
    "sports":"Sports Store","outdoor":"Outdoor Store",
    "dance":"Dance Studio","yoga":"Yoga / Pilates","swimming_pool":"Swimming Pool",
    "car":"Car Dealership","car_repair":"Auto Repair","tyres":"Tire Shop",
    "motorcycle":"Motorcycle","bicycle":"Bicycle Shop",
    "car_wash":"Car Wash","fuel":"Gas Station","car_rental":"Car Rental",
    "laundry":"Laundromat","dry_cleaning":"Dry Cleaning","tailor":"Tailor",
    "copyshop":"Copy / Print Shop","travel_agency":"Travel Agency",
    "photo":"Photography Studio","photographer":"Photographer",
    "driving_school":"Driving School","language_school":"Language School",
    "childcare":"Childcare / Daycare","kindergarten":"Kindergarten",
    "locksmith":"Locksmith","post_office":"Post Office",
    "accountant":"Accountant","lawyer":"Law Firm","notary":"Notary",
    "tax_advisor":"Tax Advisor","insurance":"Insurance Agency",
    "financial":"Financial Advisor","real_estate":"Real Estate Agency",
    "architect":"Architecture Firm","advertising_agency":"Ad Agency",
    "graphic_design":"Design Studio","company":"Company","it":"IT Company",
    "consulting":"Consulting","logistics":"Logistics",
    "employment_agency":"Recruitment Agency",
    "electrician":"Electrician","plumber":"Plumber","carpenter":"Carpenter",
    "painter":"Painter","roofer":"Roofer","mason":"Mason","tiler":"Tiler",
    "glazier":"Glazier","shoemaker":"Cobbler","jeweller":"Jeweller",
    "blacksmith":"Blacksmith","brewery":"Brewery","winery":"Winery",
    "distillery":"Distillery","printer":"Printing Shop",
    "dentist":"Dentist","doctors":"General Practitioner",
    "pharmacy":"Pharmacy","chemist":"Chemist / Drugstore",
    "veterinary":"Veterinary Clinic","physiotherapist":"Physiotherapist",
    "optometrist":"Optometrist","psychotherapist":"Therapist",
    "chiropractor":"Chiropractor","acupuncturist":"Acupuncturist",
    "hospital":"Hospital","clinic":"Clinic","laboratory":"Medical Lab",
    "nursing_home":"Nursing Home",
    "hotel":"Hotel","hostel":"Hostel","guest_house":"Guest House / B&B",
    "motel":"Motel","apartment":"Holiday Apartments","camp_site":"Campsite",
    "attraction":"Tourist Attraction","museum":"Museum","gallery":"Gallery",
    "zoo":"Zoo","aquarium":"Aquarium",
    "bank":"Bank","bureau_de_change":"Currency Exchange",
    "pet":"Pet Store","pet_grooming":"Pet Grooming",
    "trade":"Trade Supplier","wholesale":"Wholesale",
}

KEYWORDS_TO_OSM: Dict[str, List[str]] = {
    "restaurant":["restaurant"],"hairdresser":["hairdresser"],"hair":["hairdresser"],
    "bakery":["bakery"],"butcher":["butcher"],"tattoo":["tattoo"],
    "garage":["car_repair"],"mechanic":["car_repair"],"dentist":["dentist"],
    "pharmacy":["pharmacy","chemist"],"bar":["bar","pub","nightclub"],
    "cafe":["cafe"],"coffee":["cafe","coffee"],
    "hotel":["hotel","guest_house","hostel","motel"],
    "architect":["architect"],"lawyer":["lawyer","notary"],
    "accountant":["accountant","tax_advisor"],"florist":["florist"],
    "optician":["optician","optometrist"],"vet":["veterinary"],
    "doctor":["doctors","clinic"],"gym":["fitness_centre","sports_centre"],
    "yoga":["yoga"],"dance":["dance"],"realtor":["real_estate"],
    "insurance":["insurance"],"laundry":["laundry","dry_cleaning"],
    "locksmith":["locksmith"],"plumber":["plumber"],"electrician":["electrician"],
    "grocery":["convenience","greengrocer"],"nail":["nail_salon"],
    "spa":["spa","massage","sauna"],"photographer":["photographer","photo"],
    "printer":["copyshop","printer"],"travel":["travel_agency"],
    "car":["car","car_repair","car_rental","car_wash"],"bike":["bicycle"],
    "brewery":["brewery"],"winery":["winery"],"cinema":["cinema"],
    "museum":["museum"],"tailor":["tailor"],"therapist":["psychotherapist","physiotherapist"],
    "childcare":["childcare","kindergarten"],"consulting":["consulting","company"],
}

# ──────────────────────────────────────────────────────────────────────────────
# Core logic
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Prospect:
    name:       Optional[str]
    category:   Optional[str]
    address:    Optional[str]
    phone:      Optional[str]
    email:      Optional[str]
    _uid:       str
    _phone_set: FrozenSet[str]


def geocode_place(place: str) -> Tuple[float, float]:
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": place, "format": "json", "limit": 1},
        headers={"User-Agent": "prospect-app/9.0"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f"Place not found: {place}")
    return float(data[0]["lat"]), float(data[0]["lon"])


def bbox_from_center(lat, lon, radius_m):
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * math.cos(math.radians(lat)))
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon


def _normalise_phone(part: str, country: str) -> Optional[str]:
    part = part.strip()
    if not part:
        return None
    if HAS_PHONENUMBERS:
        try:
            num = phonenumbers.parse(part, country.upper())
            if phonenumbers.is_possible_number(num) or phonenumbers.is_valid_number(num):
                return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            pass
        return None
    digits = re.sub(r"\D", "", part)
    if len(digits) < 7 or len(digits) > 15:
        return None
    if digits.startswith("00"):
        return "+" + digits[2:]
    return "+" + digits


def format_phone(raw: Optional[str], country: str) -> Tuple[Optional[str], FrozenSet[str]]:
    if not raw:
        return None, frozenset()
    parts = re.split(r"[;,/]|\n|\s{2,}", raw)
    normed = [_normalise_phone(p, country) for p in parts if p.strip()]
    normed = [n for n in normed if n]
    return ("\n".join(normed), frozenset(normed)) if normed else (None, frozenset())


def format_email(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.strip().lower()
    return raw if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw) else None


def detect_category(tags: Dict) -> Optional[str]:
    for k in OSM_CATEGORY_KEYS:
        v = tags.get(k)
        if v:
            return CATEGORIES_EN.get(v, v.replace("_", " ").title())
    return None


def fmt_addr(tags: Dict) -> Optional[str]:
    """Return a formatted address only if it contains at least a street name.
    Rejects entries that only have a postcode or city — those are not usable addresses."""
    street = tags.get("addr:street")
    if not street:
        # No street = not a real address (just a postcode/city is useless for prospecting)
        return None
    parts = [
        tags.get("addr:housenumber"),
        street,
        tags.get("addr:city"),
        tags.get("addr:postcode"),
        tags.get("addr:state"),
        tags.get("addr:country"),
    ]
    return ", ".join(p for p in parts if p)


def build_overpass_query(bbox, no_website: bool, osm_filter: Optional[Set[str]]) -> str:
    s, w, n, e = bbox
    sf = "[!'website'][!'contact:website'][!'url'][!'contact:url']" if no_website else ""
    parts = []
    keys = OSM_CATEGORY_KEYS
    if osm_filter:
        for k in keys:
            for v in osm_filter:
                parts.append(f"  node['{k}'='{v}']{sf}({s},{w},{n},{e});")
                parts.append(f"  way['{k}'='{v}']{sf}({s},{w},{n},{e});")
    else:
        for k in keys:
            parts.append(f"  node['{k}']{sf}({s},{w},{n},{e});")
            parts.append(f"  way['{k}']{sf}({s},{w},{n},{e});")
    return f"[out:json][timeout:60];\n(\n" + "\n".join(parts) + "\n);\nout center;"


def run_query(
    bbox, *, no_website, require_phone, require_addr, require_email,
    osm_filter, country, seen_uids, seen_phones, max_retries=5,
) -> List[Prospect]:
    api = overpy.Overpass()
    query = build_overpass_query(bbox, no_website, osm_filter)
    res = None
    for attempt in range(1, max_retries + 1):
        try:
            res = api.query(query)
            break
        except Exception as exc:
            wait = 2 ** attempt
            time.sleep(wait)
            if attempt == max_retries:
                return []

    out: List[Prospect] = []
    for el in [*res.nodes, *res.ways]:
        tags = el.tags
        uid = f"osm:{'node' if isinstance(el, overpy.Node) else 'way'}/{el.id}"
        if uid in seen_uids:
            continue
        name             = tags.get("name") or None
        phone_str, pset  = format_phone(tags.get("phone") or tags.get("contact:phone") or tags.get("tel"), country)
        email            = format_email(tags.get("email") or tags.get("contact:email"))
        address          = fmt_addr(tags)
        category         = detect_category(tags)

        if require_phone   and not phone_str: continue
        if require_addr    and not address:   continue
        if require_email   and not email:     continue
        if not name:                          continue  # always require name
        if pset & seen_phones:                continue

        seen_uids.add(uid)
        seen_phones.update(pset)
        out.append(Prospect(name=name, category=category, address=address,
                            phone=phone_str, email=email, _uid=uid, _phone_set=pset))
    return out


def parse_categories(raw: str) -> Optional[Set[str]]:
    if not raw.strip():
        return None
    vals: Set[str] = set()
    for kw in re.split(r"[,;\s]+", raw.strip().lower()):
        kw = kw.strip()
        if kw in KEYWORDS_TO_OSM:
            vals.update(KEYWORDS_TO_OSM[kw])
        elif kw:
            vals.add(kw)
    return vals or None


def collect_leads(
    lat: float, lon: float,
    sample: int, dist_km: float, max_dist_km: float,
    country: str, no_website: bool,
    require_phone: bool, require_addr: bool, require_email: bool,
    osm_filter: Optional[Set[str]],
    log_fn,          # callable(str) for status updates
) -> List[Prospect]:
    seen_uids:   Set[str] = set()
    seen_phones: Set[str] = set()
    results:     List[Prospect] = []
    radius = dist_km

    while radius <= max_dist_km:
        bbox = bbox_from_center(lat, lon, radius * 1000)
        log_fn(f"📡 Querying Overpass — radius **{radius:.0f} km**…")
        batch = run_query(
            bbox, no_website=no_website, require_phone=require_phone,
            require_addr=require_addr, require_email=require_email,
            osm_filter=osm_filter, country=country,
            seen_uids=seen_uids, seen_phones=seen_phones,
        )
        results.extend(batch)
        log_fn(f"   → **{len(results)}** valid leads at {radius:.0f} km")

        if len(results) >= sample:
            log_fn(f"✅ Quota reached ({len(results)}) at {radius:.0f} km")
            break
        if radius < max_dist_km:
            radius = min(radius + 10, max_dist_km)
            time.sleep(1.2)
        else:
            log_fn(f"⚠️ Target not reached after {max_dist_km:.0f} km — returning {len(results)} leads")
            break

    return results[:sample]


# ──────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────────────────────

# Session state init
for key, default in [
    ("results_df", None),
    ("running", False),
    ("log_lines", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🔍 Prospect Generator</h1>
    <p>Find local businesses without a website — worldwide, powered by OpenStreetMap</p>
</div>
""", unsafe_allow_html=True)

# ── Dependency warning ────────────────────────────────────────────────────────
if not HAS_OVERPY:
    st.error("❌ **overpy** is not installed. Run `pip install overpy` then restart.")
    st.stop()
if not HAS_PHONENUMBERS:
    st.warning("⚠️ **phonenumbers** not installed — phone normalization is degraded. Run `pip install phonenumbers`")

# ── Layout: sidebar + main ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")

    place = st.text_input("📍 City / Region / Country", placeholder="e.g. Austin, Texas")

    col1, col2 = st.columns(2)
    with col1:
        sample = st.number_input("🎯 Leads target", min_value=1, max_value=2000, value=100, step=10)
    with col2:
        country = st.selectbox("🌍 Country code",
            ["FR","US","IN","GB","DE","ES","IT","CA","AU","BR","MX","JP","KR","NG","ZA"],
            index=1,
        )

    col3, col4 = st.columns(2)
    with col3:
        dist_km = st.number_input("Start radius (km)", min_value=1, max_value=500, value=5)
    with col4:
        max_dist_km = st.number_input("Max radius (km)", min_value=1, max_value=1000, value=100)

    categories_raw = st.text_input(
        "🏷️ Category filter (optional)",
        placeholder="restaurant, gym, bakery…",
    )
    st.caption("Leave blank to search all business types")

    st.markdown("---")
    output_dir = st.text_input("📂 Output folder", value="prospects_found")

# ── Field selector ────────────────────────────────────────────────────────────
# ── Session state init for field cards ───────────────────────────────────────
_field_defaults = {
    "want_phone":   True,
    "want_email":   False,
    "want_address": True,
    "no_website":   True,
}
for _k, _v in _field_defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Section header ────────────────────────────────────────────────────────────
st.markdown('''
<div class="section-label">📋 Fields to collect &amp; filters</div>
<p style="font-size:.84rem;color:#475569;margin:-4px 0 16px;line-height:1.6">
  Check a field to <strong>require it</strong> in every lead and include it as a column in the CSV.<br>
  Uncheck it to make it optional and <strong>remove its column</strong> from the export.
</p>
''', unsafe_allow_html=True)

# Card config: (key, icon, accent_color, light_bg, title, description)
_FIELDS = [
    ("want_phone",   "📞", "#2563eb", "#eff6ff",
     "Phone Number",
     "Only leads that have a phone number listed in OSM.<br>"
     "Adds a <b>Phone</b> column to the CSV."),
    ("want_email",   "📧", "#7c3aed", "#faf5ff",
     "Email Address",
     "Only leads that have an email address listed in OSM.<br>"
     "Adds an <b>Email</b> column to the CSV."),
    ("want_address", "📍", "#0891b2", "#ecfeff",
     "Postal Address",
     "Only leads that have a full postal address.<br>"
     "Adds an <b>Address</b> column to the CSV."),
    ("no_website",   "🚫", "#dc2626", "#fef2f2",
     "No Website Filter",
     "Skip any business that already has a website<br>"
     "listed in OpenStreetMap — prospects only."),
]

_cols = st.columns(4, gap="medium")
for _col, (_key, _icon, _color, _bg, _title, _desc) in zip(_cols, _FIELDS):
    with _col:
        _on = st.session_state[_key]
        _border  = _color  if _on else "#cbd5e1"
        _card_bg = _bg     if _on else "#ffffff"
        _badge_bg    = _color if _on else "#e2e8f0"
        _badge_color = "white" if _on else "#64748b"
        _badge_text  = "✅  ON — in CSV" if _on else "⬜  OFF — hidden"

        st.markdown(f'''
<div class="fcard" style="border-color:{_border};background:{_card_bg}">
  <div class="fcard-icon">{_icon}</div>
  <div class="fcard-title">{_title}</div>
  <div class="fcard-desc">{_desc}</div>
  <span class="fcard-badge" style="background:{_badge_bg};color:{_badge_color}">{_badge_text}</span>
</div>
''', unsafe_allow_html=True)

        # Native checkbox — no empty label, no toggle
        st.checkbox(
            _title,
            value=_on,
            key=_key,
            label_visibility="collapsed",
        )

# Read final values (session_state updated by checkboxes above)
want_phone   = st.session_state["want_phone"]
want_email   = st.session_state["want_email"]
want_address = st.session_state["want_address"]
no_website   = st.session_state["no_website"]

# ── Generate button ───────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

btn_col, clear_col = st.columns([4, 1])
with btn_col:
    run_btn = st.button("🚀 Generate Leads", use_container_width=True)
with clear_col:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.results_df = None
        st.rerun()

# ── Collection ────────────────────────────────────────────────────────────────
if run_btn:
    if not place.strip():
        st.error("⚠️ Please enter a city or region name in the sidebar first.")
        st.stop()

    st.session_state.results_df = None

    with st.status("⏳ Collecting leads — please wait…", expanded=True) as status:
        try:
            st.write(f"🔍 Geocoding **{place.strip()}**…")
            lat, lon = geocode_place(place.strip())
            st.write(f"📍 Center found: `{lat:.5f}, {lon:.5f}`")

            osm_filter = parse_categories(categories_raw) if categories_raw.strip() else None
            if osm_filter:
                st.write(f"🏷️ Category filter: `{', '.join(sorted(osm_filter))}`")
            else:
                st.write("🏷️ Searching all business categories")

            def log(msg: str):
                st.write(msg)

            prospects = collect_leads(
                lat=lat, lon=lon,
                sample=int(sample),
                dist_km=float(dist_km),
                max_dist_km=float(max_dist_km),
                country=country,
                no_website=no_website,
                require_phone=want_phone,
                require_addr=want_address,
                require_email=want_email,
                osm_filter=osm_filter,
                log_fn=log,
            )

            if not prospects:
                status.update(label="⚠️ No leads found — try relaxing your filters.", state="error")
                st.stop()

            rows = []
            for p in prospects:
                row: Dict = {"Name": p.name, "Category": p.category}
                if want_address: row["Address"] = p.address
                if want_phone:   row["Phone"]   = p.phone
                if want_email:   row["Email"]   = p.email
                rows.append(row)

            df = pd.DataFrame(rows)
            st.session_state.results_df = df

            from pathlib import Path
            folder = Path(output_dir)
            folder.mkdir(parents=True, exist_ok=True)
            i = 1
            while (folder / f"prospect{i}.csv").exists():
                i += 1
            out_path_final = folder / f"prospect{i}.csv"
            df.to_csv(out_path_final, index=False, encoding="utf-8-sig")
            st.write(f"💾 Saved → `{out_path_final}`")

            status.update(
                label=f"✅ Done! {len(prospects)} leads collected.",
                state="complete",
                expanded=False,
            )

        except Exception as exc:
            status.update(label=f"❌ Error: {exc}", state="error")
            st.exception(exc)

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.results_df is not None:
    df: pd.DataFrame = st.session_state.results_df
    n = len(df)

    st.markdown("<br>", unsafe_allow_html=True)

    pills = [f'<span class="stat-pill">🏢 {n} leads</span>']
    if "Phone" in df.columns:
        np_ = df["Phone"].notna().sum()
        pills.append(f'<span class="stat-pill green">📞 {np_}/{n} with phone</span>')
    if "Email" in df.columns:
        ne = df["Email"].notna().sum()
        pills.append(f'<span class="stat-pill purple">📧 {ne}/{n} with email</span>')
    if "Address" in df.columns:
        na = df["Address"].notna().sum()
        pills.append(f'<span class="stat-pill orange">📍 {na}/{n} with address</span>')

    st.markdown(
        f'<div class="card"><div class="card-title">📊 Results</div>'
        f'<div class="stats-row">{"".join(pills)}</div></div>',
        unsafe_allow_html=True,
    )

    st.dataframe(df, use_container_width=True, height=440)

    dl_col, _ = st.columns([2, 3])
    with dl_col:
        csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="⬇️  Download CSV",
            data=csv_bytes,
            file_name="prospects.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown(
        f'<div class="info-box">✅ File also auto-saved in <b>{output_dir}/</b></div>',
        unsafe_allow_html=True,
    )
