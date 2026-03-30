import re
from typing import Any, Dict, List

DetectorResult = Dict[str, Any]


def _match_regex(text: str, pattern: str, flags: int = re.I):
    if not text:
        return None
    return re.search(pattern, text, flags)


def detect_shopify(ctx: Dict[str, Any]) -> List[DetectorResult]:
    out = []
    html = ctx["html"]
    headers = ctx["headers"]
    scripts = "\n".join(ctx["script_urls"])
    cookies = ctx["cookies"]
    meta = ctx["meta"]

    candidates = [
        ("cdn.shopify.com", "script/link URL contains cdn.shopify.com"),
        ("shopify.com/s/", "URL contains shopify assets path"),
        ("Shopify.theme", "inline/page source contains Shopify.theme"),
        ("X-ShopId", "response header contains X-ShopId"),
        ("_shopify_y", "cookie _shopify_y exists"),
        ("_shopify_s", "cookie _shopify_s exists"),
        ("myshopify.com", "page references myshopify.com"),
        ("shopify-digital-wallet", "page contains shopify-digital-wallet"),
    ]

    combined = "\n".join([
        html,
        scripts,
        "\n".join(f"{k}: {v}" for k, v in headers.items()),
        "\n".join(f"{k}={v}" for k, v in cookies.items()),
        "\n".join(f"{k}={v}" for k, v in meta.items()),
    ])

    proofs = []
    for needle, proof in candidates:
        if needle.lower() in combined.lower():
            proofs.append(proof)

    if proofs:
        out.append({
            "technology": "Shopify",
            "category": "ecommerce",
            "confidence": 0.98,
            "proof": proofs[:5],
        })

    return out


def detect_wordpress(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    headers = ctx["headers"]
    proofs = []

    if "wp-content" in html or "wp-includes" in html:
        proofs.append("HTML contains wp-content/wp-includes")
    if "generator" in ctx["meta"] and "wordpress" in ctx["meta"]["generator"].lower():
        proofs.append("meta generator mentions WordPress")
    if "x-pingback" in {k.lower(): v for k, v in headers.items()}:
        proofs.append("header contains X-Pingback")

    if proofs:
        return [{
            "technology": "WordPress",
            "category": "cms",
            "confidence": 0.97,
            "proof": proofs,
        }]
    return []


def detect_woocommerce(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    cookies = ctx["cookies"]
    proofs = []

    if "woocommerce" in html.lower():
        proofs.append("HTML contains woocommerce")
    if any(k.startswith("woocommerce_") for k in cookies):
        proofs.append("WooCommerce cookie found")
    if "wc-ajax" in html.lower():
        proofs.append("HTML contains wc-ajax")

    if proofs:
        return [{
            "technology": "WooCommerce",
            "category": "ecommerce",
            "confidence": 0.95,
            "proof": proofs,
        }]
    return []


def detect_cloudflare(ctx: Dict[str, Any]) -> List[DetectorResult]:
    headers = {k.lower(): v for k, v in ctx["headers"].items()}
    proofs = []

    if "server" in headers and "cloudflare" in headers["server"].lower():
        proofs.append("server header is Cloudflare")
    if "cf-ray" in headers:
        proofs.append("cf-ray header exists")
    if "__cf_bm" in ctx["cookies"]:
        proofs.append("cookie __cf_bm exists")

    if proofs:
        return [{
            "technology": "Cloudflare",
            "category": "cdn/security",
            "confidence": 0.96,
            "proof": proofs,
        }]
    return []


def detect_google_tag_manager(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    scripts = ctx["script_urls"]
    proofs = []

    if "googletagmanager.com/gtm.js" in html.lower():
        proofs.append("HTML references googletagmanager.com/gtm.js")
    for s in scripts:
        if "googletagmanager.com/gtm.js" in s.lower():
            proofs.append(f"script src: {s}")
            break

    if proofs:
        return [{
            "technology": "Google Tag Manager",
            "category": "analytics",
            "confidence": 0.99,
            "proof": proofs,
        }]
    return []


def detect_google_analytics(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    proofs = []

    patterns = [
        r"googletagmanager\.com/gtag/js",
        r"google-analytics\.com/analytics\.js",
        r"G-[A-Z0-9]+",
        r"UA-\d+-\d+",
    ]

    for p in patterns:
        m = _match_regex(html, p)
        if m:
            proofs.append(f"matched pattern: {m.group(0)}")

    if proofs:
        return [{
            "technology": "Google Analytics",
            "category": "analytics",
            "confidence": 0.97,
            "proof": proofs[:5],
        }]
    return []


def detect_meta_pixel(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    proofs = []

    patterns = [
        r"connect\.facebook\.net/.*/fbevents\.js",
        r"fbq\(",
    ]
    for p in patterns:
        m = _match_regex(html, p)
        if m:
            proofs.append(f"matched pattern: {m.group(0)}")

    if proofs:
        return [{
            "technology": "Meta Pixel",
            "category": "marketing",
            "confidence": 0.97,
            "proof": proofs,
        }]
    return []


def detect_klaviyo(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    scripts = ctx["script_urls"]
    proofs = []

    if "_learnq" in html:
        proofs.append("HTML contains _learnq")
    for s in scripts:
        if "klaviyo" in s.lower():
            proofs.append(f"script src: {s}")
            break

    if proofs:
        return [{
            "technology": "Klaviyo",
            "category": "email marketing",
            "confidence": 0.95,
            "proof": proofs,
        }]
    return []


def detect_hotjar(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    proofs = []

    if "static.hotjar.com" in html.lower():
        proofs.append("HTML references static.hotjar.com")
    if "hj(" in html:
        proofs.append("HTML contains Hotjar init code")

    if proofs:
        return [{
            "technology": "Hotjar",
            "category": "analytics",
            "confidence": 0.94,
            "proof": proofs,
        }]
    return []


def detect_jquery(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    scripts = ctx["script_urls"]
    proofs = []

    for s in scripts:
        if "jquery" in s.lower():
            proofs.append(f"script src: {s}")
            break
    if "jQuery.fn" in html or "$.fn" in html:
        proofs.append("inline/page source contains jQuery symbols")

    if proofs:
        return [{
            "technology": "jQuery",
            "category": "javascript library",
            "confidence": 0.90,
            "proof": proofs,
        }]
    return []


def detect_react(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    proofs = []

    if "__NEXT_DATA__" in html:
        proofs.append("HTML contains __NEXT_DATA__")
    if "react-root" in html.lower():
        proofs.append("HTML contains react-root")
    if "data-reactroot" in html.lower():
        proofs.append("HTML contains data-reactroot")

    if proofs:
        return [{
            "technology": "React",
            "category": "frontend framework",
            "confidence": 0.86,
            "proof": proofs,
        }]
    return []


def detect_nextjs(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    proofs = []

    if "__NEXT_DATA__" in html:
        proofs.append("HTML contains __NEXT_DATA__")
    if "/_next/" in html:
        proofs.append("HTML references /_next/ assets")

    if proofs:
        return [{
            "technology": "Next.js",
            "category": "frontend framework",
            "confidence": 0.97,
            "proof": proofs,
        }]
    return []


def detect_vue(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    proofs = []

    if "__NUXT__" in html:
        proofs.append("HTML contains __NUXT__")
    if "data-v-" in html:
        proofs.append("HTML contains Vue-scoped attributes")

    if proofs:
        return [{
            "technology": "Vue.js",
            "category": "frontend framework",
            "confidence": 0.85,
            "proof": proofs,
        }]
    return []


def detect_nuxt(ctx: Dict[str, Any]) -> List[DetectorResult]:
    html = ctx["html"]
    proofs = []

    if "__NUXT__" in html:
        proofs.append("HTML contains __NUXT__")
    if "/_nuxt/" in html:
        proofs.append("HTML references /_nuxt/ assets")

    if proofs:
        return [{
            "technology": "Nuxt.js",
            "category": "frontend framework",
            "confidence": 0.97,
            "proof": proofs,
        }]
    return []


DETECTORS = [
    detect_shopify,
    detect_wordpress,
    detect_woocommerce,
    detect_cloudflare,
    detect_google_tag_manager,
    detect_google_analytics,
    detect_meta_pixel,
    detect_klaviyo,
    detect_hotjar,
    detect_jquery,
    detect_react,
    detect_nextjs,
    detect_vue,
    detect_nuxt,
]