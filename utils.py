from bs4 import BeautifulSoup


def parse_html_features(html: str):
    soup = BeautifulSoup(html or "", "lxml")

    script_urls = []
    link_urls = []
    meta = {}

    for tag in soup.find_all("script", src=True):
        script_urls.append(tag.get("src", "").strip())

    for tag in soup.find_all("link", href=True):
        link_urls.append(tag.get("href", "").strip())

    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or tag.get("http-equiv") or "").strip().lower()
        content = (tag.get("content") or "").strip()
        if name and content and name not in meta:
            meta[name] = content

    title = soup.title.text.strip() if soup.title and soup.title.text else ""

    return {
        "script_urls": script_urls,
        "link_urls": link_urls,
        "meta": meta,
        "title": title,
    }