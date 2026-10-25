#!/usr/bin/env python3
"""
Default Market Offer — Eight Years of Prices in Real Terms (2019-20 to 2026-27)

Produces:
  1. CSV datasets (cleaned, analysis-ready)
  2. Summary statistics and YoY change tables
  3. JSON output for the HTML report
"""

import json
import csv
from pathlib import Path
# Report date fixed to the determination period to avoid git churn on re-runs

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "docs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Load data ────────────────────────────────────────────────────────────────────────
with open(DATA_DIR / "dmo_prices.json") as f:
    raw = json.load(f)

zones = ["Ausgrid", "Endeavour Energy", "Essential Energy", "Energex", "SA Power Networks"]
res_years = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26", "2026-27"]
sb_years = ["2022-23", "2023-24", "2024-25", "2025-26", "2026-27"]
states = {
    "Ausgrid": "NSW", "Endeavour Energy": "NSW", "Essential Energy": "NSW",
    "Energex": "SE QLD", "SA Power Networks": "SA"
}

# ── CPI deflators (ABS 6401.0, Jun quarter, base Jun 2019 = 100) ─────────
cpi = raw["metadata"]["cpi_deflators"]["by_dmo_year"]
CPI_BASE = cpi["2019-20"]  # 100.00

def real_price(nominal, year):
    """Deflate a nominal price to 2019-20 dollars."""
    return round(nominal * CPI_BASE / cpi[year])

# ── Approximate DNSP customer counts (for weighted averages) ────────────
approx_customers = {z: raw["metadata"]["approximate_customers"][z] for z in zones}
total_customers = sum(approx_customers.values())

# ── 1. Flat CSV export ──────────────────────────────────────────────────────────
# DMO 5 (2023-24) used a 366-day year, adjusting all usage assumptions
dmo5_usage = raw["metadata"]["dmo5_usage_assumptions_kwh"]

rows = []
for zone in zones:
    for year in res_years:
        price = raw["residential"].get(zone, {}).get(year)
        if price is not None:
            usage = (dmo5_usage[zone]["residential"] if year == "2023-24"
                     else raw["metadata"]["usage_assumptions_kwh"][zone]["residential"])
            rows.append({
                "year": year,
                "distribution_zone": zone,
                "state": states[zone],
                "customer_type": "residential",
                "annual_dmo_price_aud": price,
                "real_price_2019_20_aud": real_price(price, year),
                "assumed_usage_kwh": usage
            })
    for year in sb_years:
        price = raw["small_business"].get(zone, {}).get(year)
        if price is not None:
            usage = (dmo5_usage[zone]["small_business"] if year == "2023-24"
                     else raw["metadata"]["usage_assumptions_kwh"][zone]["small_business"])
            rows.append({
                "year": year,
                "distribution_zone": zone,
                "state": states[zone],
                "customer_type": "small_business",
                "annual_dmo_price_aud": price,
                "real_price_2019_20_aud": real_price(price, year),
                "assumed_usage_kwh": usage
            })

with open(OUTPUT_DIR / "dmo_prices_flat.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

# ── 2. Year-on-year changes ──────────────────────────────────────────────────────
yoy_rows = []
for zone in zones:
    # Residential
    prices = raw["residential"][zone]
    for i in range(1, len(res_years)):
        prev_year, curr_year = res_years[i - 1], res_years[i]
        prev_price = prices.get(prev_year)
        curr_price = prices.get(curr_year)
        if prev_price and curr_price:
            change = curr_price - prev_price
            pct = (change / prev_price) * 100
            prev_real = real_price(prev_price, prev_year)
            curr_real = real_price(curr_price, curr_year)
            real_change = curr_real - prev_real
            real_pct = (real_change / prev_real) * 100
            yoy_rows.append({
                "year": curr_year,
                "distribution_zone": zone,
                "state": states[zone],
                "customer_type": "residential",
                "previous_price": prev_price,
                "current_price": curr_price,
                "change_aud": round(change, 2),
                "change_pct": round(pct, 1),
                "previous_real_price_2019_20_aud": prev_real,
                "current_real_price_2019_20_aud": curr_real,
                "real_change_aud": round(real_change, 2),
                "real_change_pct": round(real_pct, 1)
            })
    # Small business (starts at DMO 4)
    sb_prices = raw["small_business"][zone]
    for i in range(1, len(sb_years)):
        prev_year, curr_year = sb_years[i - 1], sb_years[i]
        prev_price = sb_prices.get(prev_year)
        curr_price = sb_prices.get(curr_year)
        if prev_price and curr_price:
            change = curr_price - prev_price
            pct = (change / prev_price) * 100
            prev_real = real_price(prev_price, prev_year)
            curr_real = real_price(curr_price, curr_year)
            real_change = curr_real - prev_real
            real_pct = (real_change / prev_real) * 100
            yoy_rows.append({
                "year": curr_year,
                "distribution_zone": zone,
                "state": states[zone],
                "customer_type": "small_business",
                "previous_price": prev_price,
                "current_price": curr_price,
                "change_aud": round(change, 2),
                "change_pct": round(pct, 1),
                "previous_real_price_2019_20_aud": prev_real,
                "current_real_price_2019_20_aud": curr_real,
                "real_change_aud": round(real_change, 2),
                "real_change_pct": round(real_pct, 1)
            })

with open(OUTPUT_DIR / "dmo_yoy_changes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=yoy_rows[0].keys())
    w.writeheader()
    w.writerows(yoy_rows)

# ── 3. Cost component analysis ─────────────────────────────────────────────────
comp_rows = []
for year in raw["cost_components"]:
    if year == "description":
        continue
    c = raw["cost_components"][year]
    for comp_name in ["wholesale", "network", "environmental", "retail"]:
        comp_rows.append({
            "year": year,
            "component": comp_name,
            "min_share_pct": round(c[comp_name]["min"] * 100, 1),
            "max_share_pct": round(c[comp_name]["max"] * 100, 1)
        })

with open(OUTPUT_DIR / "dmo_cost_components.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=comp_rows[0].keys())
    w.writeheader()
    w.writerows(comp_rows)

# ── 4. Standing offer customer trends ─────────────────────────────────────────
so_rows = []
so_data = raw["standing_offer_customers"]
for cust_type in ["residential", "small_business"]:
    for year, vals in so_data[cust_type].items():
        so_rows.append({
            "year": year,
            "customer_type": cust_type,
            "customer_count": vals["count"],
            "share_of_customers_pct": round(vals["share"] * 100, 1)
        })

with open(OUTPUT_DIR / "standing_offer_customers.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=so_rows[0].keys())
    w.writeheader()
    w.writerows(so_rows)

# ── 5. Summary statistics ──────────────────────────────────────────────────────
summary = {
    "generated": "2026-10",  # Fixed to determination period; update when data changes
    "title": "Default Market Offer — Eight Years of Prices in Real Terms",
    "period": "DMO 1 (2019-20) to DMO 8 (2026-27)",
    "key_findings": []
}

_NUM_WORDS = {0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five'}
def _num_word(n):
    return _NUM_WORDS.get(n, str(n))

# Compute values used across multiple findings
latest_yoy = [r for r in yoy_rows if r["year"] == "2026-27" and r["customer_type"] == "residential"]
sb_latest = [r for r in yoy_rows if r["year"] == "2026-27" and r["customer_type"] == "small_business"]
so_res_keys = list(so_data["residential"].keys())

# ── Customer-weighted averages ────────────────────────────────────────────────
def weighted_avg_pct(yoy_list):
    """Customer-weighted average of year-on-year percentage changes."""
    num = sum(r["change_pct"] * approx_customers[r["distribution_zone"]] for r in yoy_list)
    den = sum(approx_customers[r["distribution_zone"]] for r in yoy_list)
    return num / den

weighted_res_drop = weighted_avg_pct(latest_yoy)
weighted_sb_drop = weighted_avg_pct(sb_latest)
avg_res_drop = sum(r["change_pct"] for r in latest_yoy) / len(latest_yoy)
avg_sb_drop = sum(r["change_pct"] for r in sb_latest) / len(sb_latest)

# ── Finding 1: Standing offer decline (the DMO protects a shrinking group) ─
res_so_first = so_data["residential"][so_res_keys[0]]
res_so_latest = so_data["residential"][so_res_keys[-1]]
res_so_prev = so_data["residential"][so_res_keys[-2]]
sb_so_first = so_data["small_business"][so_res_keys[0]]
sb_so_latest = so_data["small_business"][so_res_keys[-1]]
decline_pct = (res_so_first["count"] - res_so_latest["count"]) / res_so_first["count"] * 100
sb_decline_pct = (sb_so_first["count"] - sb_so_latest["count"]) / sb_so_first["count"] * 100
reg_res = so_data["regional_residential_latest"]
nsw_pct = (reg_res["NSW"]["DMO 8"] - reg_res["NSW"]["DMO 7"]) / reg_res["NSW"]["DMO 7"] * 100
seqld_pct = (reg_res["SE Queensland"]["DMO 8"] - reg_res["SE Queensland"]["DMO 7"]) / reg_res["SE Queensland"]["DMO 7"] * 100
sa_pct = (reg_res["SA"]["DMO 8"] - reg_res["SA"]["DMO 7"]) / reg_res["SA"]["DMO 7"] * 100
summary["key_findings"].append({
    "finding": "The DMO protects a steadily shrinking group of customers",
    "detail": f"Residential standing offer customers fell from {res_so_first['count']:,} ({res_so_first['share']*100:.1f}%) "
              f"at {so_res_keys[0]} to {res_so_latest['count']:,} ({res_so_latest['share']*100:.1f}%) at {so_res_keys[-1]} — "
              f"an {decline_pct:.1f}% reduction (source: {so_res_keys[0]} from DMO 7 Table 3.1, "
              f"{so_res_keys[-1]} from DMO 8 Table 3.1). "
              f"Small business standing offer customers fell {sb_decline_pct:.1f}% over the same period "
              f"({sb_so_first['count']:,} to {sb_so_latest['count']:,}), "
              f"with the share dropping from {sb_so_first['share']*100:.1f}% to {sb_so_latest['share']*100:.1f}%. "
              f"Numbers were essentially flat between {so_res_keys[-2]} ({res_so_prev['count']:,}, {res_so_prev['share']*100:.1f}%) "
              f"and {so_res_keys[-1]} ({res_so_latest['count']:,}, {res_so_latest['share']*100:.1f}%). "
              f"Regionally, residential NSW fell {abs(nsw_pct):.1f}% "
              f"({reg_res['NSW']['DMO 7']:,} to {reg_res['NSW']['DMO 8']:,}) "
              f"while SE Queensland rose {seqld_pct:.1f}% "
              f"({reg_res['SE Queensland']['DMO 7']:,} to {reg_res['SE Queensland']['DMO 8']:,}; approximate — "
              f"extrapolated by excluding Ergon Energy, per Table 3.1 notes) "
              f"and SA rose {sa_pct:.1f}% "
              f"({reg_res['SA']['DMO 7']:,} to {reg_res['SA']['DMO 8']:,})."
})

# ── Finding 2: Price trajectory — nominal and real ──────────────────────────
aug_res = raw["residential"]["Ausgrid"]
first_price = aug_res["2019-20"]
peak_price = aug_res["2025-26"]
latest_price = aug_res["2026-27"]
total_increase = ((peak_price - first_price) / first_price) * 100
latest_change = ((latest_price - peak_price) / peak_price) * 100

# Real (CPI-adjusted) trajectory for Ausgrid
real_first = real_price(first_price, "2019-20")
real_peak = real_price(peak_price, "2025-26")
real_latest = real_price(latest_price, "2026-27")
real_total = ((real_peak - real_first) / real_first) * 100
real_latest_change = ((real_latest - real_peak) / real_peak) * 100
nominal_full_change = ((latest_price - first_price) / first_price) * 100
real_full_change = ((real_latest - real_first) / real_first) * 100
real_2122 = real_price(aug_res["2021-22"], "2021-22")
real_2223 = real_price(aug_res["2022-23"], "2022-23")

dmo8_res_changes = []
for zone in zones:
    p7 = raw["residential"][zone]["2025-26"]
    p8 = raw["residential"][zone]["2026-27"]
    dmo8_res_changes.append(((p8 - p7) / p7) * 100)

zones_down = sum(1 for c in dmo8_res_changes if c < 0)

# NOTE: The dip years (2021-22, 2022-23) and peak year (2025-26) are fixed text.
# If data changes, verify these statements still hold.
summary["key_findings"].append({
    "finding": "In real terms the DMO has gone nowhere in eight years",
    "detail": f"Ausgrid residential nominal prices are up {nominal_full_change:.1f}% from DMO 1 to DMO 8 "
              f"(${first_price:,} to ${latest_price:,}), but in real terms (2019–20 dollars) "
              f"the increase is just {real_full_change:.1f}% (${real_first:,} to ${real_latest:,}). "
              f"The real series dipped below its starting point in 2021–22 and 2022–23 "
              f"(${real_2122:,} and ${real_2223:,}), spiked with the 2023–24 increase driven by wholesale costs (DMO 5 determination, s 1.2), "
              f"and has now returned to roughly where it began. "
              f"DMO 8 itself pulls back residential prices in {_num_word(zones_down)} of five zones — "
              f"the {abs(latest_change):.1f}% nominal fall is a {abs(real_latest_change):.1f}% real fall "
              f"once inflation is stripped out. "
              f"The AER attributes lower wholesale costs to falling contract prices "
              f"for 2026–27 amid low spot price volatility (s 1.2)."
})

# ── Finding 3: Regional variation ──────────────────────────────────────────────
biggest_drop = min(latest_yoy, key=lambda x: x["change_pct"])
only_rise = [r for r in latest_yoy if r["change_pct"] > 0]
# NOTE: Fixed text — SA Power Networks and FCAS reference assume SA is the only
# zone with a price increase. If data changes, verify.
summary["key_findings"].append({
    "finding": "Regional divergence in DMO 8",
    "detail": f"{biggest_drop['distribution_zone']} ({states[biggest_drop['distribution_zone']]}) sees the largest residential flat rate decrease at –{abs(biggest_drop['change_pct']):.1f}%. "
              f"{only_rise[0]['distribution_zone']} is the only zone with a flat rate price increase "
              f"(+{only_rise[0]['change_pct']:.1f}% for residential). "
              f"The AER says South Australian wholesale costs fell less than in other regions "
              f"because of high-priced FCAS events in July and August 2025 (s 1.2). "
              f"Network charges also mostly increased."
              if only_rise else "All zones show decreases."
})

# ── Finding 4: Small business relief (with weighted averages) ────────────
res_rises = [r for r in latest_yoy if r["change_pct"] > 0]
res_qualifier = (
    f", where {res_rises[0]['distribution_zone']} rose {res_rises[0]['change_pct']:.1f}%"
    if res_rises else ""
)
summary["key_findings"].append({
    "finding": "Small business customers see larger price relief",
    "detail": f"Small business DMO flat rate prices fall by an unweighted average of {abs(avg_sb_drop):.1f}% across all five zones in DMO 8 "
              f"({abs(weighted_sb_drop):.1f}% weighted by approximate customer numbers), "
              f"compared with an unweighted average decrease of {abs(avg_res_drop):.1f}% for residential "
              f"({abs(weighted_res_drop):.1f}% weighted){res_qualifier}."
})

# ── Finding 5: Cost component breakdown (using ranges, not midpoints) ──
cc = raw["cost_components"]["2026-27"]
summary["key_findings"].append({
    "finding": "Network and wholesale charges are the two largest DMO components",
    "detail": f"In DMO 8, network costs account for {cc['network']['min']*100:.0f}–{cc['network']['max']*100:.0f}% of the price "
              f"across zones, and wholesale costs represent {cc['wholesale']['min']*100:.0f}–{cc['wholesale']['max']*100:.0f}%. "
              f"Environmental schemes account for {cc['environmental']['min']*100:.0f}–{cc['environmental']['max']*100:.0f}%, "
              f"and retail costs {cc['retail']['min']*100:.0f}–{cc['retail']['max']*100:.0f}%."
})

# ── 6. Build chart data for HTML report ───────────────────────────────────────
chart_data = {
    "summary": summary,
    "prices": raw["residential"],
    "prices_sb": raw["small_business"],
    "prices_real": {zone: {y: real_price(raw["residential"][zone][y], y) for y in res_years} for zone in zones},
    "prices_sb_real": {zone: {y: real_price(raw["small_business"][zone][y], y) for y in sb_years} for zone in zones},
    "yoy": {},
    "cost_components": raw["cost_components"],
    "standing_offer": raw["standing_offer_customers"],
    "zones": zones,
    "res_years": res_years,
    "sb_years": sb_years,
    "states": states,
    "usage_assumptions": raw["metadata"]["usage_assumptions_kwh"],
    "cpi_deflators": raw["metadata"]["cpi_deflators"]
}

# Organise YoY by zone for easy charting
for zone in zones:
    chart_data["yoy"][zone] = {
        "residential": {},
        "small_business": {}
    }
    for r in yoy_rows:
        if r["distribution_zone"] == zone:
            chart_data["yoy"][zone][r["customer_type"]][r["year"]] = {
                "change_aud": r["change_aud"],
                "change_pct": r["change_pct"]
            }

with open(OUTPUT_DIR / "chart_data.json", "w") as f:
    json.dump(chart_data, f, indent=2)

with open(OUTPUT_DIR / "summary.json", "w") as f:
    json.dump(summary, f, indent=2)

# ── 7. Generate HTML report ─────────────────────────────────────────────────
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

def build_data_object():
    """Build the JavaScript DATA object from computed values."""
    zone_short = ["Ausgrid", "Endeavour", "Essential", "Energex", "SA Power"]

    # Residential prices as arrays (ordered by res_years)
    res_arrays = {}
    for zone in zones:
        res_arrays[zone] = [raw["residential"][zone][y] for y in res_years]

    # Small business prices as arrays (ordered by sb_years)
    sb_arrays = {}
    for zone in zones:
        sb_arrays[zone] = [raw["small_business"][zone][y] for y in sb_years]

    # Real (CPI-adjusted) prices as arrays
    res_real_arrays = {}
    for zone in zones:
        res_real_arrays[zone] = [real_price(raw["residential"][zone][y], y) for y in res_years]

    sb_real_arrays = {}
    for zone in zones:
        sb_real_arrays[zone] = [real_price(raw["small_business"][zone][y], y) for y in sb_years]

    # Cost component ranges (percentages)
    cc = raw["cost_components"]["2026-27"]
    cost_ranges = {
        "2026-27": {
            "wholesale": {"min": round(cc["wholesale"]["min"] * 100), "max": round(cc["wholesale"]["max"] * 100)},
            "network": {"min": round(cc["network"]["min"] * 100), "max": round(cc["network"]["max"] * 100)},
            "environmental": {"min": round(cc["environmental"]["min"] * 100), "max": round(cc["environmental"]["max"] * 100)},
            "retail": {"min": round(cc["retail"]["min"] * 100), "max": round(cc["retail"]["max"] * 100)},
        }
    }

    # Standing offer data
    so = raw["standing_offer_customers"]
    so_years_list = list(so["residential"].keys())
    so_res_counts = [so["residential"][y]["count"] for y in so_years_list]
    so_res_shares = [round(so["residential"][y]["share"] * 100, 1) for y in so_years_list]
    so_sb_counts = [so["small_business"][y]["count"] for y in so_years_list]
    so_sb_shares = [round(so["small_business"][y]["share"] * 100, 1) for y in so_years_list]

    # Findings - map from computed summary
    findings_js = [{"title": f["finding"], "detail": f["detail"]}
                   for f in summary["key_findings"]]

    data = {
        "zones": zones,
        "zoneShort": zone_short,
        "resYears": res_years,
        "sbYears": sb_years,
        "states": states,
        "colors": [],
        "residential": res_arrays,
        "small_business": sb_arrays,
        "residentialReal": res_real_arrays,
        "smallBusinessReal": sb_real_arrays,
        "costRanges": cost_ranges,
        "standingOffer": {
            "years": so_years_list,
            "residential": {"counts": so_res_counts, "shares": so_res_shares},
            "small_business": {"counts": so_sb_counts, "shares": so_sb_shares},
        },
        "findings": findings_js,
    }
    return json.dumps(data, indent=2)


def build_notes_section():
    """Build the data and methodology notes section from the source data."""
    so = raw["standing_offer_customers"]

    # Check for Ergon caveat in the description
    ergon_note = ""
    if "description" in so and "Ergon" in so.get("description", ""):
        ergon_note = (
            "<li>SE Queensland standing offer figures are approximate — extrapolated "
            "from all of Queensland by excluding Ergon Energy customers "
            "(per Table 3.1 notes in the AER determinations)</li>"
        )

    # Build Sources list from data_sources to stay in sync with the data file
    ds = raw['metadata']['data_sources']
    seen = set()
    source_items = []
    # Price sources by year — deduplicate res/SB that cite the same document
    fy_order = ['2019-20','2020-21','2021-22','2022-23','2023-24','2024-25','2025-26','2026-27']
    for fy in fy_order:
        res_key = f'residential_{fy}'
        sb_key = f'small_business_{fy}'
        res_src = ds.get(res_key, '')
        sb_src = ds.get(sb_key, '')
        if res_src and res_src not in seen:
            label = f'{fy.replace(chr(45), chr(8211))} residential prices'
            if sb_src == res_src:
                label = f'{fy.replace(chr(45), chr(8211))} residential and small business prices'
            source_items.append(f'<li>{res_src} — {label}</li>')
            seen.add(res_src)
        if sb_src and sb_src not in seen:
            source_items.append(f'<li>{sb_src} — {fy.replace(chr(45), chr(8211))} small business prices</li>')
            seen.add(sb_src)
    # Standing offer sources — deduplicate
    so_sources = {}
    for k, v in ds.items():
        if k.startswith('standing_offer_'):
            dmo = k.replace('standing_offer_', '')
            so_sources.setdefault(v, []).append(dmo.replace('_', ' '))
    for src, dmos in so_sources.items():
        dmo_list = ', '.join(dmos)
        source_items.append(f'<li>{src} — standing offer customers ({dmo_list})</li>')
    # Special entries
    for special_key, label in [
        ('small_business_usage_change', 'change in small business usage from 20,000 to 10,000 kWh'),
        ('cost_component_ranges_2026-27', 'cost component ranges'),
        ('sa_wholesale_costs', 'wholesale cost analysis, including SA'),
        ('network_tariff_blending', 'network tariff blending'),
    ]:
        if special_key in ds:
            val = ds[special_key]
            # Trim explanatory text after em dash for the source list
            if ' – ' in val:
                val = val.split(' – ')[0]
            source_items.append(f'<li>{val} — {label}</li>')
    # CPI source
    source_items.append('<li>ABS Consumer Price Index, Australia (cat. 6401.0) — CPI deflators for real-price series</li>')
    sources_li = '\n'.join(f'        {item}' for item in source_items)

    # Build CPI deflator table for notes
    cpi_meta = raw["metadata"]["cpi_deflators"]
    cpi_vals = cpi_meta["by_dmo_year"]

    notes_html = f"""    <div class="notes-box">
      <h3>Sources</h3>
      <ul>
{sources_li}
      </ul>
      <h3>Notes</h3>
      <ul>
        <li>All prices are nominal annual reference prices for the flat rate (anytime) tariff, inclusive of GST</li>
        <li>Real (CPI-adjusted) prices are deflated to 2019–20 dollars using the ABS Consumer Price Index (cat. 6401.0), All Groups Weighted Average of Eight Capital Cities. The June quarter CPI at the start of each DMO financial year is used as the deflator, with Jun 2019 = 100</li>
        <li>Customer-weighted averages use approximate DNSP customer counts sourced from regulatory proposals, annual reports and AER jurisdictional snapshots (2023–25 vintage). These are total customer numbers, not split by tariff type, and are used as weights for both residential and small business averages</li>
        <li>Usage assumptions are zone-specific and set by the AER for a representative customer; current assumptions shown — DMO 5 (2023–24) used a 366-day year, giving slightly higher usage figures across all zones (e.g. 3,911 kWh for Ausgrid residential vs the standard 3,900 kWh; 10,027 kWh for small business vs 10,000 kWh)</li>
        <li>Small business usage assumption changed from 20,000 kWh to 10,000 kWh at DMO 4 (2022–23); earlier SB prices are excluded as not comparable</li>
        <li>Cost component shares are AER-published ranges that depend on the region, not point estimates; the AER does not break them down by zone. Because each component’s range spans different regions, the four ranges do not sum to 100%</li>
        <li>Standing offer customer data is drawn from AER determination Table 3.1 (DMO 4 through DMO 8). The determination tables themselves draw on the AER's quarterly retail market performance updates; the DMO 7 table uses the {so["residential"]["DMO 7"]["snapshot"]} update and DMO 8 uses the {so["residential"]["DMO 8"]["snapshot"]} update</li>
        {ergon_note}
        <li>DMO 6 (2024–25) figures reflect the AER’s revised final determination</li>
        <li>DMO 8 applies a network tariff blending method for determining representative network costs (s 1.3.2)</li>
      </ul>
      <h3>Pipeline</h3>
      <ul>
        <li>Source data compiled from public AER determinations into structured JSON</li>
        <li>Python pipeline computes year-on-year changes, CPI-adjusted prices, customer-weighted averages, cost component breakdowns, and summary statistics</li>
        <li>Outputs: flat CSV datasets (analysis-ready), JSON for charting, this HTML report</li>
      </ul>
    </div>"""
    return notes_html


def generate_html_report():
    """Assemble the HTML report from template files and computed data."""
    # Read template components
    chartjs = (TEMPLATE_DIR / "chartjs.min.js").read_text()
    css = (TEMPLATE_DIR / "styles.css").read_text()
    render_js = (TEMPLATE_DIR / "render.js").read_text()

    data_js = build_data_object()
    notes_section = build_notes_section()

    # Build usage assumptions text
    usage = raw["metadata"]["usage_assumptions_kwh"]
    usage_parts = []
    for zone in zones:
        short = zone.replace(" Energy", "").replace(" Power Networks", "")
        usage_parts.append(f"{short} {usage[zone]['residential']:,} kWh")
    usage_text = ", ".join(usage_parts)

    # Get report date
    report_month = "October 2026"  # Fixed to match README; update when data changes

    html = f"""<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Default Market Offer — Eight Years of Prices in Real Terms</title>
<script>{chartjs}</script>
<style>
{css}</style>
</head>
<body>

<div class="header">
  <h1>Default Market Offer — Eight Years of Prices in Real Terms</h1>
  <div class="scope" style="font-size:0.95rem;color:var(--text);margin-bottom:10px;">How electricity price caps moved across five distribution zones &mdash; and what drove the DMO&nbsp;8 price changes</div>
  <div class="scope">DMO 1 (2019–20) through DMO 8 (2026–27) &middot; Residential &amp; small business &middot; NSW, SE Queensland, South Australia</div>
</div>

<div class="container">

  <div class="section">
    <h2>Key findings</h2>
    <p>This analysis draws on publicly available data from the AER’s annual DMO final determinations and published information kits. It covers all five distribution zones where the DMO applies: Ausgrid, Endeavour Energy and Essential Energy in NSW, Energex in South East Queensland, and SA Power Networks in South Australia.</p>
    <div class="findings" id="findings"></div>
  </div>

  <div class="section">
    <h2>Price trends by distribution zone</h2>
    <p>Annual DMO reference prices for a representative customer on the flat rate tariff. Usage assumptions are set by the AER and differ by zone: {usage_text}. Toggle between nominal and real (2019–20 $) to see the effect of inflation.</p>

    <div class="tab-row">
      <button class="tab-btn active" onclick="switchTab('residential')">Residential</button>
      <button class="tab-btn" onclick="switchTab('small_business')">Small business</button>
    </div>

    <div class="tab-row" style="margin-top:6px;">
      <button class="tab-btn active" id="nominalBtn" onclick="switchPriceMode('nominal')">Nominal</button>
      <button class="tab-btn" id="realBtn" onclick="switchPriceMode('real')">Real (2019–20 $)</button>
    </div>

    <div class="chart-box">
      <div class="chart-label" id="priceChartTitle">Residential DMO prices by zone, 2019–20 to 2026–27 ($/year)</div>
      <canvas id="priceChart"></canvas>
      <div class="chart-source" id="priceChartSource">Data: AER DMO Final Determinations, flat rate tariff, nominal prices inclusive of GST.</div>
    </div>

    <h3 id="resTableHeading">Residential prices ($/year)</h3>
    <div class="table-wrapper" id="priceTableRes"></div>

    <h3 id="sbTableHeading" style="display:none">Small business prices ($/year; 10,000 kWh usage, 10,027 kWh in 2023–24)</h3>
    <p id="sbNote" style="display:none;font-size:0.85rem;color:var(--text-light);margin-top:-8px;">Note: Small business usage assumption changed from 20,000 kWh to 10,000 kWh at DMO 4 (2022–23). Earlier SB prices are not comparable and are excluded.</p>
    <div class="table-wrapper" id="priceTableSB" style="display:none"></div>
  </div>

  <div class="section">
    <h2>Year-on-year price changes</h2>
    <p>Annual change in residential DMO prices. Decreases are shown in green in the table, increases in red. Note: DMO 5 (2023–24) used a 366-day year, which inflates 2023–24 year-on-year changes by about 0.2–0.3 percentage points (estimated) and deflates 2024–25 changes by the same amount. DMO 6 (2024–25) year-on-year changes are based on the AER’s revised final determination prices, which are $13 to $15 higher than the prices first announced (depending on customer type and region), except Ausgrid residential.</p>

    <div class="chart-box">
      <div class="chart-label">Year-on-year residential price change by zone (%)</div>
      <canvas id="yoyChart"></canvas>
      <div class="chart-source">Data: AER DMO Final Determinations. Percentage change in nominal annual price.</div>
    </div>

    <h3>Residential year-on-year changes</h3>
    <div class="table-wrapper" id="yoyTable"></div>
  </div>

  <div class="section">
    <h2>Cost component breakdown</h2>
    <p>The DMO price is built from four cost categories: wholesale electricity procurement, network charges (transmission and distribution), environmental scheme costs, and retail costs – the cost to serve customers. The AER publishes these as ranges that depend on the region, not as a single figure for each zone.</p>

    <div class="chart-box">
      <div class="chart-label">DMO 8 (2026–27) cost component share ranges across zones (%)</div>
      <canvas id="costRangeChart"></canvas>
      <div class="chart-source">Data: AER DMO 2026–27 Information Kit. Ranges reflect variation by region.</div>
    </div>

    <h3>DMO 8 component share ranges (%)</h3>
    <div class="table-wrapper" id="costTable"></div>
  </div>

  <div class="section">
    <h2>Standing offer customer trends</h2>
    <p>The DMO caps prices for customers on standing offers — those who have not switched to a market offer.</p>

    <div class="chart-box">
      <div class="chart-label">Standing offer customers and market share</div>
      <canvas id="standingOfferChart"></canvas>
      <div class="chart-source">Data: AER DMO 7 and DMO 8 Final Determinations (Table 3.1). Totals across the three DMO regions (NSW, SE Queensland, SA).</div>
    </div>

    <h3>Standing offer customer numbers</h3>
    <div class="table-wrapper" id="soTable"></div>
  </div>

  <div class="section">
    <h2>Data and methodology</h2>
{notes_section}
  </div>
</div>

<div class="footer">
  {report_month}
</div>

<script>
const DATA = {data_js};

{render_js}
</script>
</body>
</html>
"""
    out_path = OUTPUT_DIR / "index.html"
    out_path.write_text(html)
    return out_path


html_path = generate_html_report()

print("✓ Analysis complete")
print(f"  Files written to {OUTPUT_DIR}:")
for p in sorted(OUTPUT_DIR.iterdir()):
    print(f"    {p.name} ({p.stat().st_size:,} bytes)")
