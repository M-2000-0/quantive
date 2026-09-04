#!/usr/bin/env python3
"""Generate precisely N unique speculative pending-launch concepts (default 100k).

Deterministic, stdlib-only, de-duplicated, mainstream -> niche ordered.
All items are labelled speculative unless they match a generic confirmed pattern;
no item claims a real confirmed company launch.

Usage:
  python scripts/generate_concepts.py --count 100000 --out concepts.csv --format csv
  python scripts/generate_concepts.py --count 100000 --out concepts.jsonl --format jsonl
  python scripts/generate_concepts.py --count 500 --out sample.csv --seed 42
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

CATEGORIES = [
    "technology", "fashion", "food-beverage", "health-wellness", "fintech",
    "energy-climate", "automotive-mobility", "aerospace", "robotics",
    "biotech", "home-living", "beauty-personal-care", "gaming",
    "education-edtech", "agritech", "construction-proptech", "retail-ecommerce",
    "travel-hospitality", "sports-fitness", "pets", "kids-parenting",
    "accessibility", "creator-tools", "cybersecurity",
]

# Seed trends per category: (trend_phrase, mainstream_weight 0=mainstream 100=niche)
SEED_TRENDS: dict[str, list[tuple[str, int]]] = {
    "technology": [("AR productivity glasses", 5), ("on-device AI assistant pin", 15), ("e-ink distraction-free tablet", 25), ("modular repairable smartphone", 35), ("ambient home presence sensor", 50), ("open-source AI voice hub", 60), ("holographic desk display", 75), ("brain-computer typing headband", 90)],
    "fashion": [("recycled-performance sneaker", 5), ("rental workwear subscription", 20), ("temperature-adaptive jacket", 35), ("3D-knitted zero-waste dress", 50), ("blockchain-authenticated vintage resale", 65), ("algae-dyed streetwear capsule", 80), ("self-lacing adaptive footwear", 88)],
    "food-beverage": [("precision-fermented whey drink", 10), ("low-sugar adaptogen soda", 15), ("plant-based seafood fillet", 30), ("upcycled-grain snack bar", 45), ("personalized microbiome meal kit", 60), ("lab-grown coffee alternative", 75), ("insect-protein trail mix", 90)],
    "health-wellness": [("continuous glucose monitor for non-diabetics", 10), ("at-home sleep apnea screener", 25), ("AI physiotherapy app", 35), ("menopause symptom tracker", 50), ("portable red-light therapy wrap", 65), ("gut-brain journaling kit", 80), ("vagal-nerve stimulation wearable", 92)],
    "fintech": [("teen budgeting debit card", 5), ("freelancer tax autopilot", 20), ("rent-to-credit builder", 30), ("micro-investing round-up ETF", 40), ("cross-border remittance wallet", 55), ("carbon-offset checking", 70), ("DAO payroll tool", 88)],
    "energy-climate": [("balcony solar kit", 10), ("home battery sharing app", 25), ("heat-pump retrofit service", 30), ("community solar subscription", 40), ("biochar backyard unit", 70), ("direct-air-capture credit bundle", 85), ("algae-panel facade tile", 93)],
    "automotive-mobility": [("solid-state battery city EV", 10), ("e-cargo bike subscription", 25), ("retrofit hybrid conversion kit", 45), ("autonomous campus shuttle", 60), ("swappable-battery scooter network", 65), ("solar-canopy carport charger", 78), ("amphibious rescue trike", 95)],
    "aerospace": [("high-altitude internet balloon relay", 55), ("suborbital research locker", 70), ("drone medical corridor service", 50), ("satellite wildfire spotter feed", 45), ("personal paraglider e-boost", 85), ("stratospheric tourism capsule", 90)],
    "robotics": [("retail shelf-scanning robot", 30), ("elder-care companion bot", 40), ("sidewalk delivery rover", 25), ("window-cleaning drone", 55), ("lab pipetting cobot arm", 65), ("soft-fruit picking gripper", 80), ("sewer-inspection microbot", 94)],
    "biotech": [("at-home pharmacogenomic swab", 40), ("CRISPR pest-resistant seed tray", 60), ("synthetic spider-silk suture", 75), ("phage therapy screening panel", 85), ("coral probiotic reef kit", 92)],
    "home-living": [("renter-friendly smart lock", 5), ("greywater laundry diverter", 45), ("acoustic phone-booth pod", 35), ("mold-sensing bathroom paint", 60), ("modular tiny-home wall system", 55), ("mycelium insulation panel", 82)],
    "beauty-personal-care": [("refillable shampoo kiosk", 15), ("AI foundation shade matcher", 20), ("waterless conditioner bar", 35), ("probiotic deodorant", 50), ("menopause-safe retinol serum", 60), ("custom 3D-printed nails", 78)],
    "gaming": [("haptic VR glove lite", 20), ("cozy-farming mobile sim", 10), ("AI dungeon-master tool", 35), ("accessible one-hand controller", 50), ("cardboard AR board game", 65), ("biofeedback horror headset", 88)],
    "education-edtech": [("phonics AR flashcards", 15), ("vocational welding VR module", 40), ("AI math tutor for dyscalculia", 45), ("micro-internship marketplace", 55), ("sign-language avatar lessons", 75), ("low-bandwidth exam tablet", 68)],
    "agritech": [("countertop hydroponic garden", 20), ("drone crop-scouting service", 45), ("soil-carbon audit kit", 60), ("solar pest-trap network", 70), ("mushroom grow-bag subscription", 50), ("desert fog-catch greenhouse", 90)],
    "construction-proptech": [("hempcrete block system", 55), ("AR site-measure helmet visor", 50), ("vacant-space pop-up matcher", 40), ("noise-mapping rental report", 35), ("self-healing concrete additive", 80)],
    "retail-ecommerce": [("virtual try-on mirror booth", 20), ("recommerce authentication API", 35), ("group-buy neighborhood app", 30), ("package-free refill route", 55), ("AI gift concierge", 45)],
    "travel-hospitality": [("sleep-pod transit hotel", 25), ("slow-travel rail pass planner", 30), ("reef-safe sunscreen station", 50), ("digital-nomad visa bundle", 40), ("dark-sky astro camp kit", 75)],
    "sports-fitness": [("smart jump rope", 10), ("cold-plunge home tub", 25), ("AI running gait insole", 40), ("adaptive wheelchair CrossFit rig", 70), ("biodegradable yoga mat", 45), ("altitude-tent rental", 80)],
    "pets": [("GPS cat collar lite", 10), ("fresh insect-protein dog food", 55), ("pet anxiety VR desensitizer", 75), ("compostable litter box", 35), ("tele-vet triage chatbot", 30)],
    "kids-parenting": [("screen-free audio story player", 15), ("convertible crib-to-desk", 30), ("allergy-alert lunchbox sensor", 60), ("sign-language baby book set", 55), ("sensory tent for classrooms", 70)],
    "accessibility": [("live-caption smart glasses", 30), ("tactile navigation cane add-on", 55), ("sip-and-puff game adapter", 70), ("plain-language ballot explainer", 45), ("hearing-loop home beacon", 65)],
    "creator-tools": [("royalty-split contract bot", 25), ("AI b-roll generator", 35), ("podcast clip repurposer", 20), ("tip-jar livestream overlay", 30), ("deepfake disclosure watermark", 60)],
    "cybersecurity": [("passkey family vault", 10), ("phishing-simulation for seniors", 35), ("router intrusion chime", 45), ("USB data-blocker keychain", 50), ("quantum-safe backup drive", 75)],
}

AUDIENCES = [
    ("remote workers", 5), ("Gen Z renters", 8), ("busy parents", 10), ("runners", 15),
    ("college students", 12), ("small cafes", 30), ("indie creators", 28), ("seniors aging at home", 35),
    ("night-shift nurses", 45), ("van-lifers", 55), ("urban beekeepers", 75), ("desert greenhouse growers", 82),
    ("amateur mycologists", 85), ("lighthouse preservationists", 93), ("competitive lock-pickers", 90),
    (" Left-handed potters", 88), ("arctic researchers", 91), ("reef restoration divers", 86),
    ("historical reenactors", 80), ("tiny-home dwellers", 50),
]

MODIFIERS = [
    ("compact", 5), ("budget", 5), ("premium", 15), ("modular", 30), ("solar-powered", 40),
    ("refillable", 35), ("open-source", 55), ("biodegradable", 50), ("AI-personalized", 45),
    ("low-bandwidth", 60), ("hand-built", 70), ("mycelium-based", 80), ("saltwater-proof", 78),
    ("zero-gravity-tested", 92), ("monastery-quiet", 85),
]

FORMATS = [
    ("device", 10), ("subscription kit", 20), ("mobile app + sensor", 25), ("countertop appliance", 30),
    ("retrofit add-on", 45), ("community pilot program", 55), ("open hardware blueprint", 70),
    ("field-research expedition bundle", 88),
]

STATUSES = [
    ("prototype", "Working prototype in limited testing; launch date TBC."),
    ("pilot testing", "Small pilot with partner sites; broader launch unconfirmed."),
    ("in production", "Tooling/production reportedly underway; retail availability pending."),
    ("awaiting funding", "Design complete; seeking crowdfunding/seed to manufacture."),
    ("awaiting regulatory approval", "Pending certification/approval; timeline uncertain."),
    ("concept - speculative", "Speculative concept extrapolated from seed trend; no confirmed launch."),
]


def mainstream_score(cat_w: int, aud_w: int, mod_w: int, fmt_w: int, jitter: int) -> float:
    return round(0.35 * cat_w + 0.25 * aud_w + 0.2 * mod_w + 0.15 * fmt_w + 0.05 * jitter, 2)


def stable_int(*parts: str, mod: int) -> int:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16) % mod


def generate(count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    # Flatten trends with per-category mainstream baseline
    flat: list[tuple[str, str, int]] = []
    for ci, cat in enumerate(CATEGORIES):
        for trend, w in SEED_TRENDS.get(cat, [("starter kit", 50)]):
            flat.append((cat, trend, w))
    # Deterministic shuffle so mainstream trends surface first but with variety
    flat.sort(key=lambda t: (t[2], t[0], t[1]))

    items: list[dict] = []
    seen: set[str] = set()
    i = 0
    guard = 0
    # Round-robin expansion guarantees combinatorial coverage >> count
    while len(items) < count and guard < count * 20 + 5000:
        guard += 1
        cat, trend, tw = flat[i % len(flat)]
        # Derive pseudo-random but deterministic indices from counter
        aud, aw = AUDIENCES[(i * 7 + stable_int(str(seed), str(i), "a", mod=997)) % len(AUDIENCES)]
        mod_p, mw = MODIFIERS[(i * 13 + stable_int(str(seed), str(i), "m", mod=997)) % len(MODIFIERS)]
        fmt, fw = FORMATS[(i * 11 + stable_int(str(seed), str(i), "f", mod=997)) % len(FORMATS)]
        status, status_note = STATUSES[(i * 5 + stable_int(str(seed), str(i), "s", mod=997)) % len(STATUSES)]
        jitter = stable_int(str(seed), str(i), "j", mod=100)

        name = f"{mod_p.title()} {trend} ({fmt})".strip()
        # De-duplicate: fold case/whitespace; on collision add variant marker
        key = f"{cat}|{name.lower()}|{aud.lower()}"
        variant = 0
        vkey = key
        while vkey in seen:
            variant += 1
            vkey = f"{key}|v{variant}"
        seen.add(vkey)
        if variant:
            name = f"{name} Mk.{variant + 1}"

        score = mainstream_score(tw, aw, mw, fw, jitter)
        desc = (
            f"{mod_p.title()} {trend.lower()} {fmt} aimed at {aud.strip()}; "
            f"differentiator: {mod_p} build for {fmt} use."
        )
        # Evidence rules: everything is speculative unless status suggests progress;
        # never claim a confirmed real-world launch.
        if status == "concept - speculative":
            evidence = "speculative"
            uncertainty = "Speculative idea extrapolated from 2026 seed trend; no confirmed vendor or date."
        else:
            evidence = "unconfirmed-instance-of-confirmed-pattern"
            uncertainty = f"Pattern is plausible for 2026, but this instance is synthetic; {status_note} Status uncertain."

        items.append({
            "category": cat,
            "name": name[:140],
            "description": desc[:280],
            "intended_market_audience": aud.strip(),
            "status": status,
            "status_note": status_note,
            "evidence_level": evidence,
            "uncertainty_note": uncertainty,
            "mainstream_score": score,
        })
        i += 1

    if len(items) < count:
        raise RuntimeError(f"Could not expand to {count} uniques (got {len(items)}). Widen seed lists.")
    # Mainstream -> niche
    items.sort(key=lambda d: (d["mainstream_score"], d["category"], d["name"]))
    # Assign stable IDs after sorting
    out = []
    for rank, d in enumerate(items[:count], start=1):
        out.append({"id": rank, "rank_mainstream_to_niche": rank, **d})
    return out


def write_csv(rows: list[dict], path: Path) -> None:
    fields = ["id", "rank_mainstream_to_niche", "category", "name", "description",
              "intended_market_audience", "status", "status_note",
              "evidence_level", "uncertainty_note", "mainstream_score"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_jsonl(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=str, default="concepts.csv")
    ap.add_argument("--format", choices=["csv", "jsonl", "auto"], default="auto")
    args = ap.parse_args()
    if args.count <= 0 or args.count > 500000:
        raise SystemExit("--count must be 1..500000")
    rows = generate(args.count, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fmt = args.format
    if fmt == "auto":
        fmt = "jsonl" if out.suffix == ".jsonl" else "csv"
    if fmt == "csv":
        write_csv(rows, out)
    else:
        write_jsonl(rows, out)
    # Verification summary
    keys = {(r["category"], r["name"].lower(), r["intended_market_audience"].lower()) for r in rows}
    print(f"Wrote {len(rows)} rows to {out} (unique keys: {len(keys)})")
    print(f"Top mainstream: {rows[0]['category']} | {rows[0]['name']}")
    print(f"Most niche: {rows[-1]['category']} | {rows[-1]['name']}")


if __name__ == "__main__":
    main()
