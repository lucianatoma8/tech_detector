# Website Technology Detector

A signature-based tool that identifies technologies used by websites, built for sales intelligence — specifically to find ecommerce stores using competing products.

## Approach

I implemented a **signature-based detector**. For each domain, the tool:

1. Fetches the homepage via HTTPS (falls back to HTTP), follows redirects
2. Extracts signals: HTML, response headers, cookies, script URLs, link URLs, meta tags
3. Runs a catalog of detector functions against those signals
4. Returns all matched technologies with **explicit proof** for each detection

I chose this approach because the task explicitly requires justification for every detection. A signature-based system is fast, deterministic, and produces human-readable proof — a salesperson can read "cf-ray header present" and immediately understand why Cloudflare was detected. A black-box classifier cannot provide that.

## Results

| Metric | Value |
|---|---|
| Domains processed | 200 |
| Total detections | 471 |
| Unique technologies detected | 13 |

The challenge brief reports **477 occurrences** on the same dataset. The current detector set captures **471**, which corresponds to most of the signal available in static HTML alone.

## Output

Results are written to `output/technologies.json`.
{
  "domain": "yourfamilylines.com",
  "final_url": "http://yourfamilylines.com",
  "status_code": 200,
  "error": null,
  "technologies": [
    {
      "technology": "jQuery",
      "category": "javascript library",
      "confidence": 0.9,
      "proof": ["script src: js/jquery.js"]
    }
  ]
}

## Project Structure
├── detect.py # Entry point — fetch, extract, detect, output
├── detectors.py # All detector functions + DETECTORS registry
├── utils.py # HTML feature extraction (BeautifulSoup)
├── requirements.txt
└── output/
└── technologies.json

## Debate Topics

### 1. Main issues and how I would tackle them

**Homepage-only analysis.**
The tool only fetches the homepage. Many technologies only appear on `/cart`, `/checkout`, or `/products`. I would crawl 3–5 high-value paths per domain to improve recall without building a full spider.

**No JavaScript execution.**
Technologies loaded client-side after render are invisible to a raw HTTP fetch. I would add a Playwright fallback for domains where initial HTML is sparse or detection confidence is low.

**Limited signature coverage.**
The tool only detects what I explicitly defined. I would expand the catalog continuously and add confidence weighting per signal source (header signals score higher than HTML substring matches).

**Bot protection.**
Some domains block crawlers or return degraded HTML. I would add retry logic, realistic User-Agent rotation, SSL fallback, and smarter error classification.

### 2. Scaling to millions of domains in 1–2 months

The key is to **decouple crawling from detection**:
[Domain Queue] → [Fetch Workers] → [Raw Storage (S3/GCS)] → [Detection Engine] → [Results DB]

- Fetch workers are stateless and horizontally scalable — each pulls a domain from the queue, stores raw HTML + headers, and moves on
- Detection runs as a separate batch job against stored snapshots — no recrawling needed when detectors are updated
- Domain-aware rate limiting prevents hammering a single host across workers
- At 500 domains/second across 100 workers, 10 million domains complete in under 6 hours

Storing raw snapshots first is the most important design decision: it makes detection cheap, reproducible, and independent of network conditions.

### 3. Discovering new technologies in the future

Three complementary methods:

**Frequency mining** — across large crawls, cluster unknown script domains, cookie names, JavaScript globals, and meta generator values by frequency. Patterns appearing on hundreds of unrelated sites typically represent reusable products.

**Manual signal inspection** — periodically review unmatched third-party script URLs and headers that appear in raw crawl data but don't map to known detectors.

**Feedback loop from misses** — whenever a site is manually identified as using a technology the system missed, convert that evidence into a new detector rule. Over time this builds a self-growing signature knowledge base.

## Why This Is Useful for the Shopify Use Case

The tool directly identifies:
- Stores running **competing ecommerce platforms** (WooCommerce, Magento, BigCommerce, PrestaShop)
- Stores using **Shopify-adjacent tools** (Klaviyo, Gorgias, Recharge, Judge.me, Yotpo) that indicate an active ecommerce operation
- Proof per detection that a salesperson or analyst can verify and act on
