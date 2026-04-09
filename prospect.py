#!/usr/bin/env python3
"""prospect.py – v9.0

Lead generation tool – OpenStreetMap / Overpass API
────────────────────────────────────────────────────
Collects businesses without a website from OSM data.
Works worldwide: France, USA, India, UK, Germany, etc.

Usage:
    python prospect.py --place "Austin, Texas" --sample 200 --country US
    python prospect.py --place "Mumbai, India" --sample 100 --country IN --allow-no-address
    python prospect.py --latlon 48.85 2.35 --sample 50 --categories "restaurant,bakery"
    python prospect.py --place "London, UK" --sample 150 --require-email --allow-with-website
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import pandas as pd
import requests

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    import phonenumbers
    HAS_PHONENUMBERS = True
except ImportError:
    phonenumbers = None  # type: ignore
    HAS_PHONENUMBERS = False

try:
    import overpy
    HAS_OVERPY = True
except ImportError:
    overpy = None  # type: ignore
    HAS_OVERPY = False

###############################################################################
# OSM tag keys to search (broad coverage)
###############################################################################

OSM_CATEGORY_KEYS: List[str] = [
    "shop",
    "office",
    "amenity",
    "craft",
    "tourism",
    "leisure",
    "healthcare",
    "service",
    "rental",
    "sport",
    "club",
    "landuse",        # commercial / retail zones sometimes tagged
]

###############################################################################
# English category labels mapped from OSM values
###############################################################################

CATEGORIES_EN: Dict[str, str] = {
    # ── Food & Drink ──────────────────────────────────────────────────────────
    "bakery":           "Bakery",
    "butcher":          "Butcher",
    "supermarket":      "Supermarket",
    "convenience":      "Convenience Store",
    "greengrocer":      "Greengrocer",
    "fishmonger":       "Fishmonger",
    "deli":             "Deli / Delicatessen",
    "confectionery":    "Confectionery",
    "pastry":           "Pastry Shop",
    "beverages":        "Beverages / Off-Licence",
    "wine":             "Wine Shop",
    "alcohol":          "Alcohol Store",
    "tea":              "Tea Shop",
    "coffee":           "Coffee Shop",
    "chocolate":        "Chocolate Shop",
    "cheese":           "Cheese Shop",
    "health_food":      "Health Food Store",
    "organic":          "Organic Store",
    "farm":             "Farm Shop",
    "restaurant":       "Restaurant",
    "cafe":             "Café / Coffee Shop",
    "bar":              "Bar",
    "pub":              "Pub",
    "fast_food":        "Fast Food",
    "food_court":       "Food Court",
    "ice_cream":        "Ice Cream Shop",
    "biergarten":       "Beer Garden",
    "nightclub":        "Nightclub",
    # ── Beauty & Wellness ────────────────────────────────────────────────────
    "hairdresser":      "Hair Salon",
    "beauty":           "Beauty Salon",
    "cosmetics":        "Cosmetics Store",
    "nail_salon":       "Nail Salon",
    "tattoo":           "Tattoo & Piercing Studio",
    "massage":          "Massage / Spa",
    "tanning_salon":    "Tanning Salon",
    "sauna":            "Sauna",
    "spa":              "Spa",
    # ── Fashion & Accessories ────────────────────────────────────────────────
    "clothes":          "Clothing Store",
    "shoes":            "Shoe Store",
    "jewelry":          "Jewelry Store",
    "optician":         "Optician",
    "florist":          "Florist",
    "accessories":      "Accessories",
    "bag":              "Bag / Luggage Store",
    "watches":          "Watch Store",
    "fabric":           "Fabric & Textiles",
    "sewing":           "Sewing & Craft",
    # ── Home & Garden ────────────────────────────────────────────────────────
    "furniture":        "Furniture Store",
    "hardware":         "Hardware Store",
    "garden":           "Garden Center",
    "kitchen":          "Kitchen Store",
    "bathroom":         "Bathroom Store",
    "tiles":            "Tiles & Flooring",
    "carpet":           "Carpet & Rugs",
    "curtain":          "Curtains & Blinds",
    "lighting":         "Lighting Store",
    "doors":            "Doors & Windows",
    "windows":          "Windows Store",
    "paint":            "Paint Store",
    "heating":          "Heating & Energy",
    "agrarian":         "Farm Supply",
    # ── Electronics & Tech ──────────────────────────────────────────────────
    "electronics":      "Electronics Store",
    "mobile_phone":     "Mobile Phone Store",
    "computer":         "Computer Store",
    "video_games":      "Video Game Store",
    "hifi":             "Hi-Fi / Audio Store",
    "appliance":        "Home Appliances",
    # ── Culture & Leisure ───────────────────────────────────────────────────
    "books":            "Bookstore",
    "stationery":       "Stationery Store",
    "newsagent":        "Newsagent / Kiosk",
    "music":            "Music Store",
    "musical_instrument": "Musical Instruments",
    "art":              "Art Gallery / Shop",
    "craft":            "Arts & Crafts Store",
    "hobby":            "Hobby Shop",
    "toys":             "Toy Store",
    "gift":             "Gift Shop",
    "antiques":         "Antiques Shop",
    "second_hand":      "Second-Hand / Thrift Store",
    "collector":        "Collectibles Store",
    "cinema":           "Cinema",
    "theatre":          "Theatre",
    "arts_centre":      "Arts Centre",
    "library":          "Library",
    "casino":           "Casino",
    "escape_game":      "Escape Room",
    "bowling_alley":    "Bowling Alley",
    "miniature_golf":   "Mini Golf",
    "golf_course":      "Golf Course",
    "shooting_range":   "Shooting Range",
    "climbing":         "Climbing Gym",
    "horse_riding":     "Horse Riding",
    "ice_rink":         "Ice Rink",
    "hackerspace":      "Hackerspace / Makerspace",
    "laser_tag":        "Laser Tag",
    # ── Sport & Fitness ─────────────────────────────────────────────────────
    "fitness_centre":   "Fitness Center / Gym",
    "sports_centre":    "Sports Center",
    "sports":           "Sports Store",
    "outdoor":          "Outdoor & Camping Store",
    "dance":            "Dance Studio",
    "yoga":             "Yoga / Pilates Studio",
    "swimming_pool":    "Swimming Pool",
    "sports_hall":      "Sports Hall",
    # ── Automotive ──────────────────────────────────────────────────────────
    "car":              "Car Dealership",
    "car_repair":       "Auto Repair Shop",
    "tyres":            "Tire Shop",
    "motorcycle":       "Motorcycle Dealer",
    "bicycle":          "Bicycle Shop",
    "car_wash":         "Car Wash",
    "fuel":             "Gas Station",
    "car_rental":       "Car Rental",
    "vehicle_inspection": "Vehicle Inspection",
    # ── Services ────────────────────────────────────────────────────────────
    "laundry":          "Laundromat",
    "dry_cleaning":     "Dry Cleaning",
    "tailor":           "Tailor",
    "copyshop":         "Copy / Print Shop",
    "travel_agency":    "Travel Agency",
    "ticket":           "Ticket Office",
    "photo":            "Photography Studio",
    "photographer":     "Photographer",
    "internet_cafe":    "Internet Café",
    "telephone":        "Phone / Communication",
    "pawnbroker":       "Pawnbroker",
    "locksmith":        "Locksmith",
    "key_cutting":      "Key Cutting",
    "post_office":      "Post Office",
    "marketplace":      "Market",
    "driving_school":   "Driving School",
    "language_school":  "Language School",
    "music_school":     "Music School",
    "art_school":       "Art School",
    "dancing_school":   "Dancing School",
    "childcare":        "Childcare / Daycare",
    "kindergarten":     "Kindergarten",
    # ── Professional & Office ────────────────────────────────────────────────
    "accountant":       "Accountant",
    "lawyer":           "Law Firm",
    "notary":           "Notary",
    "tax_advisor":      "Tax Advisor",
    "insurance":        "Insurance Agency",
    "financial":        "Financial Advisor",
    "real_estate":      "Real Estate Agency",
    "architect":        "Architecture Firm",
    "advertising_agency": "Advertising Agency",
    "graphic_design":   "Graphic Design Studio",
    "company":          "Company",
    "it":               "IT Company",
    "consulting":       "Consulting",
    "logistics":        "Logistics / Shipping",
    "employment_agency": "Staffing / Recruitment Agency",
    "telecommunication": "Telecom Company",
    "research":         "Research Institute",
    "association":      "Association / NGO",
    # ── Trades & Crafts ─────────────────────────────────────────────────────
    "electrician":      "Electrician",
    "plumber":          "Plumber",
    "carpenter":        "Carpenter",
    "painter":          "Painter & Decorator",
    "roofer":           "Roofer",
    "mason":            "Mason / Bricklayer",
    "tiler":            "Tiler",
    "glazier":          "Glazier",
    "shoemaker":        "Cobbler / Shoe Repair",
    "jeweller":         "Jeweller",
    "blacksmith":       "Blacksmith",
    "potter":           "Potter / Ceramics",
    "brewery":          "Brewery",
    "winery":           "Winery",
    "distillery":       "Distillery",
    "signmaker":        "Sign Maker",
    "printer":          "Printing Shop",
    "engraver":         "Engraver",
    "clockmaker":       "Clockmaker",
    "watchmaker":       "Watch Repair",
    # ── Health & Medical ────────────────────────────────────────────────────
    "dentist":          "Dentist",
    "doctors":          "General Practitioner",
    "pharmacy":         "Pharmacy",
    "chemist":          "Chemist / Drugstore",
    "veterinary":       "Veterinary Clinic",
    "physiotherapist":  "Physiotherapist",
    "optometrist":      "Optometrist",
    "psychotherapist":  "Psychotherapist / Therapist",
    "speech_therapist": "Speech Therapist",
    "chiropractor":     "Chiropractor",
    "acupuncturist":    "Acupuncturist",
    "podiatrist":       "Podiatrist",
    "nurse":            "Nursing Practice",
    "midwife":          "Midwife",
    "hospital":         "Hospital / Clinic",
    "clinic":           "Clinic",
    "laboratory":       "Medical Laboratory",
    "nursing_home":     "Nursing Home",
    "rehabilitation":   "Rehabilitation Center",
    # ── Hospitality & Tourism ───────────────────────────────────────────────
    "hotel":            "Hotel",
    "hostel":           "Hostel",
    "guest_house":      "Guest House / B&B",
    "motel":            "Motel",
    "apartment":        "Holiday Apartments",
    "chalet":           "Chalet",
    "camp_site":        "Campsite",
    "caravan_site":     "Caravan / RV Park",
    "attraction":       "Tourist Attraction",
    "museum":           "Museum",
    "gallery":          "Gallery",
    "theme_park":       "Theme Park",
    "zoo":              "Zoo",
    "aquarium":         "Aquarium",
    # ── Finance ─────────────────────────────────────────────────────────────
    "bank":             "Bank",
    "bureau_de_change": "Currency Exchange",
    # ── Pets ────────────────────────────────────────────────────────────────
    "pet":              "Pet Store",
    "pet_grooming":     "Pet Grooming",
    # ── Trade / Wholesale ───────────────────────────────────────────────────
    "trade":            "Trade Supplier",
    "wholesale":        "Wholesale",
    "electrical":       "Electrical Supplier",
    "plumbing":         "Plumbing Supplier",
}

# Keywords → OSM values (for --categories)
KEYWORDS_TO_OSM: Dict[str, List[str]] = {
    "restaurant":    ["restaurant"],
    "hairdresser":   ["hairdresser"],
    "hair":          ["hairdresser"],
    "bakery":        ["bakery"],
    "butcher":       ["butcher"],
    "tattoo":        ["tattoo"],
    "garage":        ["car_repair"],
    "mechanic":      ["car_repair"],
    "dentist":       ["dentist"],
    "pharmacy":      ["pharmacy", "chemist"],
    "bar":           ["bar", "pub", "nightclub"],
    "cafe":          ["cafe"],
    "coffee":        ["cafe", "coffee"],
    "hotel":         ["hotel", "guest_house", "hostel", "motel"],
    "architect":     ["architect"],
    "lawyer":        ["lawyer", "notary"],
    "accountant":    ["accountant", "tax_advisor"],
    "florist":       ["florist"],
    "optician":      ["optician", "optometrist"],
    "vet":           ["veterinary"],
    "doctor":        ["doctors", "clinic"],
    "gym":           ["fitness_centre", "sports_centre"],
    "yoga":          ["yoga"],
    "dance":         ["dance", "dancing_school"],
    "realtor":       ["real_estate"],
    "insurance":     ["insurance"],
    "driving":       ["driving_school"],
    "laundry":       ["laundry", "dry_cleaning"],
    "locksmith":     ["locksmith"],
    "plumber":       ["plumber"],
    "electrician":   ["electrician"],
    "grocery":       ["convenience", "greengrocer", "supermarket"],
    "nail":          ["nail_salon"],
    "spa":           ["spa", "massage", "sauna"],
    "tattoo":        ["tattoo"],
    "photographer":  ["photographer", "photo"],
    "printer":       ["copyshop", "printer"],
    "travel":        ["travel_agency"],
    "car":           ["car", "car_repair", "car_rental", "car_wash"],
    "bike":          ["bicycle"],
    "brewery":       ["brewery"],
    "winery":        ["winery"],
    "cinema":        ["cinema"],
    "museum":        ["museum"],
    "tailor":        ["tailor"],
    "therapist":     ["psychotherapist", "physiotherapist"],
    "childcare":     ["childcare", "kindergarten"],
    "consulting":    ["consulting", "company"],
}

###############################################################################
# Data model
###############################################################################

@dataclass
class Prospect:
    name:        Optional[str]
    category:    Optional[str]
    address:     Optional[str]
    phone:       Optional[str]
    email:       Optional[str]
    _uid:        str
    _phone_set:  FrozenSet[str]

    def as_row(self) -> Dict[str, Optional[str]]:
        return {
            "Name":     self.name,
            "Category": self.category,
            "Address":  self.address,
            "Phone":    self.phone,
            "Email":    self.email,
        }

###############################################################################
# Geocoding
###############################################################################

def geocode_place(place: str) -> Tuple[float, float]:
    print(f"🔍 Geocoding '{place}'...")
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": place, "format": "json", "limit": 1},
        headers={"User-Agent": "prospect-tool/9.0"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    if not data:
        sys.exit(f"❌ Place not found: {place}")
    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
    print(f"   → Center: {lat:.5f}, {lon:.5f}")
    return lat, lon


def bbox_from_center(lat: float, lon: float, radius_m: float) -> Tuple[float, float, float, float]:
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * math.cos(math.radians(lat)))
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon

###############################################################################
# Phone normalization (international)
###############################################################################

def _normalise_phone(part: str, country: str) -> Optional[str]:
    """Normalize a single phone number to E.164 for any country."""
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

    # Fallback (no phonenumbers lib): keep only if it looks like a real number
    digits = re.sub(r"\D", "", part)
    if len(digits) < 7 or len(digits) > 15:
        return None
    # Prepend + if starts with country-like digits
    if digits.startswith("00"):
        return "+" + digits[2:]
    return "+" + digits if not digits.startswith("+") else digits


def format_phone(raw: Optional[str], country: str) -> Tuple[Optional[str], FrozenSet[str]]:
    """Handle one or multiple numbers separated by ; , / newline or 2+ spaces."""
    if not raw:
        return None, frozenset()
    parts = re.split(r"[;,/]|\n|\s{2,}", raw)
    normed = [_normalise_phone(p, country) for p in parts if p.strip()]
    normed = [n for n in normed if n]
    if not normed:
        return None, frozenset()
    return "\n".join(normed), frozenset(normed)

###############################################################################
# Email
###############################################################################

def format_email(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.strip().lower()
    return raw if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw) else None

###############################################################################
# Category detection
###############################################################################

def detect_category(tags: Dict[str, str]) -> Optional[str]:
    for k in OSM_CATEGORY_KEYS:
        v = tags.get(k)
        if v:
            label = CATEGORIES_EN.get(v)
            if label:
                return label
            # Unknown value: prettify it
            return v.replace("_", " ").title()
    return None

###############################################################################
# Address formatting
###############################################################################

def fmt_addr(tags: Dict[str, str]) -> Optional[str]:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city"),
        tags.get("addr:postcode"),
        tags.get("addr:state"),
        tags.get("addr:country"),
    ]
    return ", ".join(p for p in parts if p) or None

###############################################################################
# Overpass query builder
###############################################################################

def build_overpass_query(
    bbox: Tuple[float, float, float, float],
    no_website: bool,
    osm_values_filter: Optional[Set[str]],
) -> str:
    s, w, n, e = bbox
    sf = (
        "[!'website'][!'contact:website'][!'url'][!'contact:url']"
        "[!'website:en'][!'website:fr']"
        if no_website else ""
    )

    union_parts: List[str] = []
    if osm_values_filter:
        for k in OSM_CATEGORY_KEYS:
            for v in osm_values_filter:
                union_parts.append(f"  node['{k}'='{v}']{sf}({s},{w},{n},{e});")
                union_parts.append(f"  way['{k}'='{v}']{sf}({s},{w},{n},{e});")
    else:
        for k in OSM_CATEGORY_KEYS:
            union_parts.append(f"  node['{k}']{sf}({s},{w},{n},{e});")
            union_parts.append(f"  way['{k}']{sf}({s},{w},{n},{e});")

    body = "\n".join(union_parts)
    return f"[out:json][timeout:60];\n(\n{body}\n);\nout center;"

###############################################################################
# Overpass query with retry
###############################################################################

def osm_query(
    bbox: Tuple[float, float, float, float],
    *,
    no_website: bool,
    require_phone: bool,
    require_name: bool,
    require_addr: bool,
    require_email: bool,
    osm_values_filter: Optional[Set[str]],
    country: str,
    seen_uids: Set[str],
    seen_phones: Set[str],
    max_retries: int = 5,
) -> List[Prospect]:
    api = overpy.Overpass()
    query = build_overpass_query(bbox, no_website, osm_values_filter)

    res = None
    for attempt in range(1, max_retries + 1):
        try:
            res = api.query(query)
            break
        except Exception as exc:
            wait = 2 ** attempt
            print(f"   ⚠️  Overpass attempt {attempt}/{max_retries} failed ({exc}). Retrying in {wait}s...")
            if attempt == max_retries:
                print("   ❌ Overpass unreachable after all retries.")
                return []
            time.sleep(wait)

    out: List[Prospect] = []
    elements = [*res.nodes, *res.ways]
    iterator = (
        tqdm(elements, desc="   Parsing", unit=" elements", leave=False)
        if HAS_TQDM else elements
    )

    for el in iterator:
        tags: Dict[str, str] = el.tags
        uid = f"osm:{'node' if isinstance(el, overpy.Node) else 'way'}/{el.id}"
        if uid in seen_uids:
            continue

        name             = tags.get("name") or None
        phone_str, pset  = format_phone(
            tags.get("phone") or tags.get("contact:phone") or tags.get("tel"),
            country,
        )
        email            = format_email(
            tags.get("email") or tags.get("contact:email")
        )
        address          = fmt_addr(tags)
        category         = detect_category(tags)

        # Apply filters
        if require_phone and not phone_str:
            continue
        if require_name and not name:
            continue
        if require_addr and not address:
            continue
        if require_email and not email:
            continue

        # Deduplicate by phone number
        if pset & seen_phones:
            continue

        seen_uids.add(uid)
        seen_phones.update(pset)

        out.append(Prospect(
            name=name, category=category, address=address,
            phone=phone_str, email=email,
            _uid=uid, _phone_set=pset,
        ))

    return out

###############################################################################
# Auto-numbered output path
###############################################################################

def next_output_path(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    i = 1
    while (folder / f"prospect{i}.csv").exists():
        i += 1
    return folder / f"prospect{i}.csv"

###############################################################################
# Collection loop with radius expansion
###############################################################################

def collect(
    lat: float,
    lon: float,
    args: argparse.Namespace,
    osm_values_filter: Optional[Set[str]],
) -> List[Prospect]:
    seen_uids:   Set[str] = set()
    seen_phones: Set[str] = set()
    results:     List[Prospect] = []
    radius = args.dist_km

    while radius <= args.max_dist_km:
        bbox = bbox_from_center(lat, lon, radius * 1000)
        print(f"📡 Querying Overpass — radius {radius:.0f} km...")

        batch = osm_query(
            bbox,
            no_website        = not args.allow_with_website,
            require_phone     = not args.allow_no_phone,
            require_name      = not args.allow_no_name,
            require_addr      = not args.allow_no_address,
            require_email     = args.require_email,
            osm_values_filter = osm_values_filter,
            country           = args.country,
            seen_uids         = seen_uids,
            seen_phones       = seen_phones,
        )

        results.extend(batch)
        print(f"   → {len(results)} valid leads so far at {radius:.0f} km")

        if len(results) >= args.sample:
            print(f"✅ Quota reached ({len(results)}) at {radius:.0f} km")
            break

        if radius < args.max_dist_km:
            next_r = min(radius + 10, args.max_dist_km)
            print(f"   Target {args.sample} not reached, expanding to {next_r:.0f} km...")
            radius = next_r
            time.sleep(1.5)
        else:
            print(f"⚠️  Target not reached after {args.max_dist_km:.0f} km.")
            break

    return results

###############################################################################
# Keyword parser for --categories
###############################################################################

def parse_categories(raw: str, mapping: Dict[str, List[str]]) -> Set[str]:
    osm_vals: Set[str] = set()
    for kw in re.split(r"[,;\s]+", raw.strip().lower()):
        kw = kw.strip()
        if not kw:
            continue
        if kw in mapping:
            osm_vals.update(mapping[kw])
        else:
            osm_vals.add(kw)  # pass raw as OSM value
    return osm_vals

###############################################################################
# CLI
###############################################################################

def main() -> None:
    cli = argparse.ArgumentParser(
        description="prospect.py v9.0 – worldwide OSM lead generation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    loc = cli.add_mutually_exclusive_group(required=True)
    loc.add_argument("--place",  metavar="PLACE",
                     help="City / region / country name (geocoded via Nominatim)")
    loc.add_argument("--latlon", nargs=2, type=float, metavar=("LAT", "LON"),
                     help="Explicit GPS center: --latlon 48.85 2.35")

    cli.add_argument("--dist-km",     type=float, default=5,
                     help="Starting search radius in km")
    cli.add_argument("--max-dist-km", type=float, default=100,
                     help="Maximum search radius in km")
    cli.add_argument("--sample",      type=int,   required=True,
                     help="Number of leads to collect")
    cli.add_argument("--country",     default="FR",
                     help="ISO 3166-1 alpha-2 country code for phone parsing (FR, US, IN, GB, DE…)")
    cli.add_argument("--output-dir",  default="prospects_found",
                     help="Output folder (files named prospect1.csv, prospect2.csv…)")

    # Filters
    cli.add_argument("--allow-no-phone",      action="store_true",
                     help="Include leads without a phone number")
    cli.add_argument("--allow-no-name",       action="store_true",
                     help="Include leads without a business name")
    cli.add_argument("--allow-no-address",    action="store_true",
                     help="Include leads without an address")
    cli.add_argument("--require-email",       action="store_true",
                     help="Only include leads that have an email address")
    cli.add_argument("--allow-with-website",  action="store_true",
                     help="Also include businesses that already have a website")
    cli.add_argument("--categories",          metavar="LIST",
                     help='Filter by category keywords: "restaurant,bakery,gym"')

    args = cli.parse_args()

    # Dependency checks
    if not HAS_OVERPY:
        sys.exit("❌ overpy is not installed. Run: pip install overpy")
    if not HAS_PHONENUMBERS:
        print("⚠️  phonenumbers not installed – phone normalization degraded.")
        print("   Run: pip install phonenumbers")
    if not HAS_TQDM:
        print("ℹ️  tqdm not installed – no progress bar. Run: pip install tqdm")

    # Resolve center
    if args.place:
        lat, lon = geocode_place(args.place)
    else:
        lat, lon = float(args.latlon[0]), float(args.latlon[1])

    # Parse category filter
    osm_filter: Optional[Set[str]] = None
    if args.categories:
        osm_filter = parse_categories(args.categories, KEYWORDS_TO_OSM)
        print(f"🏷️  Category filter (OSM values): {sorted(osm_filter)}")

    # Collect
    prospects = collect(lat, lon, args, osm_filter)
    if not prospects:
        print("⚠️  No leads collected.")
        return

    prospects = prospects[: args.sample]

    # Export CSV (utf-8-sig ensures correct display in Excel on all platforms)
    out_path = next_output_path(Path(args.output_dir))
    df = pd.DataFrame(p.as_row() for p in prospects)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    # Summary
    n   = len(df)
    np_ = df["Phone"].notna().sum()
    ne  = df["Email"].notna().sum()
    na  = df["Address"].notna().sum()
    print(f"\n✅  {n} leads saved → {out_path}")
    print(f"   📞 Phone: {np_}/{n}   📧 Email: {ne}/{n}   📍 Address: {na}/{n}")


if __name__ == "__main__":
    main()
