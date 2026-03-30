import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pandas as pd

from detectors import DETECTORS
from utils import parse_html_features


TIMEOUT = httpx.Timeout(20.0, connect=10.0)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TechDetector/1.0; +https://example.com/bot)"
}


def normalize_domain(raw: str) -> str:
    raw = raw.strip()
    raw = raw.replace("https://", "").replace("http://", "")
    raw = raw.strip("/")
    return raw


def load_domains(path: str) -> List[str]:
    p = Path(path)

    if p.suffix.lower() == ".parquet":
        df = pd.read_parquet(p)
        if "root_domain" in df.columns:
            return [normalize_domain(x) for x in df["root_domain"].dropna().astype(str).tolist()]
        return [normalize_domain(x) for x in df.iloc[:, 0].dropna().astype(str).tolist()]

    if p.suffix.lower() in {".csv"}:
        df = pd.read_csv(p)
        if "root_domain" in df.columns:
            return [normalize_domain(x) for x in df["root_domain"].dropna().astype(str).tolist()]
        return [normalize_domain(x) for x in df.iloc[:, 0].dropna().astype(str).tolist()]

    with open(p, "r", encoding="utf-8") as f:
        return [normalize_domain(line) for line in f if line.strip()]


async def fetch_one(client: httpx.AsyncClient, domain: str) -> Dict[str, Any]:
    urls = [f"https://{domain}", f"http://{domain}"]

    last_error = None
    for url in urls:
        try:
            r = await client.get(url, follow_redirects=True)
            html = r.text[:2_000_000]

            cookies = {}
            for cookie in client.cookies.jar:
                if domain in cookie.domain or cookie.domain in domain:
                    cookies[cookie.name] = cookie.value

            parsed = parse_html_features(html)

            return {
                "domain": domain,
                "requested_url": url,
                "final_url": str(r.url),
                "status_code": r.status_code,
                "headers": dict(r.headers),
                "cookies": cookies,
                "html": html,
                "script_urls": parsed["script_urls"],
                "link_urls": parsed["link_urls"],
                "meta": parsed["meta"],
                "title": parsed["title"],
                "error": None,
            }
        except Exception as e:
            last_error = str(e)

    return {
        "domain": domain,
        "requested_url": None,
        "final_url": None,
        "status_code": None,
        "headers": {},
        "cookies": {},
        "html": "",
        "script_urls": [],
        "link_urls": [],
        "meta": {},
        "title": "",
        "error": last_error,
    }


def dedupe_technologies(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best = {}
    for item in items:
        key = item["technology"].lower()
        if key not in best or item["confidence"] > best[key]["confidence"]:
            best[key] = item
    return sorted(best.values(), key=lambda x: (-x["confidence"], x["technology"].lower()))


def detect_technologies(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    all_hits = []
    for detector in DETECTORS:
        try:
            all_hits.extend(detector(ctx))
        except Exception as e:
            all_hits.append({
                "technology": f"detector_error:{detector.__name__}",
                "category": "internal",
                "confidence": 0.0,
                "proof": [str(e)],
            })
    return dedupe_technologies(all_hits)


async def run(domains: List[str]) -> List[Dict[str, Any]]:
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS, limits=limits, verify=True, http2=True) as client:
        sem = asyncio.Semaphore(25)

        async def worker(domain: str):
            async with sem:
                ctx = await fetch_one(client, domain)
                techs = detect_technologies(ctx)
                return {
                    "domain": domain,
                    "final_url": ctx["final_url"],
                    "status_code": ctx["status_code"],
                    "error": ctx["error"],
                    "technologies": techs,
                }

        return await asyncio.gather(*(worker(d) for d in domains))


def main():
    if len(sys.argv) < 2:
        print("Usage: python detect.py domains.parquet")
        sys.exit(1)

    path = sys.argv[1]
    domains = load_domains(path)
    domains = list(dict.fromkeys(domains))

    print(f"Loaded {len(domains)} domains")

    results = asyncio.run(run(domains))

    Path("output").mkdir(exist_ok=True)
    with open("output/technologies.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("Wrote output/technologies.json")

    total_hits = sum(len(r["technologies"]) for r in results)
    unique_tech = sorted({
        tech["technology"]
        for row in results
        for tech in row["technologies"]
    })

    print(f"Total detections: {total_hits}")
    print(f"Unique technologies: {len(unique_tech)}")


if __name__ == "__main__":
    main()