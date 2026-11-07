#!/usr/bin/env python3
"""Check static SEO source and optionally source-identical browser responses."""

import argparse
import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

ORIGIN = "https://tmoxie.app"
APP_STORE_URL = "https://apps.apple.com/us/app/tmoxie/id6767995101?uo=4"
PAGES = {
    "/": "index.html",
    "/tutorials/": "tutorials/index.html",
    "/docs/": "docs/index.html",
    "/privacy/": "privacy/index.html",
    "/terms/": "terms/index.html",
    "/support/": "support/index.html",
}


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.canonicals = []
        self.links = []
        self.ids = []
        self.titles = []
        self.headings = []
        self.schemas = []
        self.capture = None
        self.buffer = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            name = attrs.get("name", attrs.get("property", ""))
            self.meta.setdefault(name, []).append(attrs.get("content", ""))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for attribute in ("href", "src", "poster"):
            if attribute in attrs:
                self.links.append(attrs[attribute])
        if tag in ("title", "h1") or (tag == "script" and attrs.get("type") == "application/ld+json"):
            self.capture = tag
            self.buffer = []

    def handle_data(self, data):
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if self.capture == tag:
            value = "".join(self.buffer).strip()
            {"title": self.titles, "h1": self.headings, "script": self.schemas}[tag].append(value)
            self.capture = None


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(root):
    files = set(PAGES.values()) | {"404.html"}
    require({str(p.relative_to(root)) for p in root.rglob("*.html")} == files, "HTML page tree differs from the public page registry")
    pages = {path: Page((root / file).read_text()) for path, file in PAGES.items()}
    titles, descriptions, resources = set(), set(), set()
    for path, page in pages.items():
        url = ORIGIN + path
        require(len(page.titles) == 1 and page.titles[0], f"{path}: requires one title")
        title = page.titles[0]
        require(title not in titles, f"{path}: duplicate title")
        titles.add(title)
        require(len(page.headings) == 1 and page.headings[0], f"{path}: requires one nonempty H1")
        require(len(page.ids) == len(set(page.ids)), f"{path}: duplicate HTML IDs")
        require(page.canonicals == [url], f"{path}: canonical must be {url}")
        for name in ("description", "robots", "og:type", "og:site_name", "og:title", "og:description", "og:url", "og:image", "og:image:alt", "og:image:width", "og:image:height", "twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:image:alt"):
            require(len(page.meta.get(name, [])) == 1 and page.meta[name][0], f"{path}: missing or duplicate {name}")
        meta = {key: values[0] for key, values in page.meta.items()}
        require(meta["robots"] == "index, follow", f"{path}: indexable page has restricted robots")
        require(meta["description"] not in descriptions, f"{path}: duplicate description")
        descriptions.add(meta["description"])
        require(meta["og:title"] == meta["twitter:title"] == title, f"{path}: inconsistent social titles")
        require(meta["og:description"] == meta["twitter:description"] == meta["description"], f"{path}: inconsistent social descriptions")
        require(meta["og:url"] == url, f"{path}: wrong social URL")
        require(meta["og:image"] == meta["twitter:image"] == ORIGIN + "/assets/og-image.jpg", f"{path}: wrong social image")
        require((meta["og:image:width"], meta["og:image:height"], meta["twitter:card"]) == ("1200", "630", "summary_large_image"), f"{path}: wrong social image dimensions or card")
        require(len(page.schemas) == 1, f"{path}: requires one JSON-LD graph")
        schema = json.loads(page.schemas[0])
        require(schema["@context"] == "https://schema.org", f"{path}: wrong schema context")
        nodes = schema["@graph"]
        by_type = {node["@type"]: node for node in nodes}
        expected = {"WebSite", "SoftwareApplication", "WebPage"} if path == "/" else {"WebPage", "BreadcrumbList"}
        require(set(by_type) == expected and len(nodes) == len(expected), f"{path}: unexpected schema graph")
        webpage = by_type["WebPage"]
        require(webpage["url"] == url and webpage["@id"] == url + "#webpage", f"{path}: wrong WebPage identity")
        require(webpage["name"] == title and webpage["description"] == meta["description"], f"{path}: schema and visible metadata disagree")
        require(webpage["isPartOf"] == {"@id": ORIGIN + "/#website"} and webpage["about"] == {"@id": ORIGIN + "/#app"}, f"{path}: wrong site or app entity")
        if path == "/":
            require(by_type["WebSite"]["@id"] == ORIGIN + "/#website", "Wrong WebSite identity")
            app = by_type["SoftwareApplication"]
            require(app["@id"] == ORIGIN + "/#app" and app["url"] == url and app["operatingSystem"] == "iOS 17 or later", "Wrong application identity or platform")
            require(app.get("downloadUrl") == APP_STORE_URL and APP_STORE_URL in page.links, "Homepage must link to the released App Store app")
            require(not ({"installUrl", "aggregateRating", "review", "offers"} & set(app)), "App schema must not invent install URLs, ratings, or prices")
        else:
            breadcrumb = by_type["BreadcrumbList"]
            require(webpage["breadcrumb"] == {"@id": url + "#breadcrumb"} and breadcrumb["@id"] == url + "#breadcrumb", f"{path}: breadcrumb identity mismatch")
            require([item["item"] for item in breadcrumb["itemListElement"]] == [ORIGIN + "/", url], f"{path}: wrong breadcrumb hierarchy")
            require([item["position"] for item in breadcrumb["itemListElement"]] == [1, 2], f"{path}: wrong breadcrumb order")
        resources.add(urlsplit(meta["og:image"]).path)
        for link in page.links:
            resolved = urlsplit(urljoin(url, link))
            if resolved.scheme not in ("http", "https"):
                continue
            if resolved.netloc != "tmoxie.app":
                require("voidsteed.github.io/tmoxie-site" not in link, f"{path}: old site URL")
                continue
            require(resolved.scheme == "https", f"{path}: insecure internal link")
            target = unquote(resolved.path)
            require(not target.endswith("index.html"), f"{path}: internal page link must use its canonical path")
            if target in pages:
                if resolved.fragment:
                    require(unquote(resolved.fragment) in pages[target].ids, f"{path}: broken fragment {link}")
            else:
                require((root / target.lstrip("/")).is_file(), f"{path}: missing internal resource {link}")
                resources.add(target)
    not_found = Page((root / "404.html").read_text())
    require(not_found.meta.get("robots") == ["noindex"] and len(not_found.headings) == 1, "404 page must remain noindex with one H1")
    require((root / "CNAME").read_text().strip() == "tmoxie.app", "CNAME changed")
    robots = (root / "robots.txt").read_text()
    require(robots.strip() == "User-agent: *\nAllow: /\n\nSitemap: https://tmoxie.app/sitemap.xml", "Unexpected crawler directives")
    sitemap = ET.parse(root / "sitemap.xml").getroot()
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    entries = sitemap.findall("s:url", namespace)
    locations = [entry.findtext("s:loc", namespaces=namespace) for entry in entries]
    require(len(locations) == len(PAGES) and set(locations) == {ORIGIN + path for path in PAGES}, "Sitemap must list exactly the canonical indexable pages")
    for entry in entries:
        date = datetime.date.fromisoformat(entry.findtext("s:lastmod", namespaces=namespace))
        require(date <= datetime.date.today(), "Sitemap lastmod is in the future")
    llms = (root / "llms.txt").read_text()
    for path in PAGES:
        require(ORIGIN + path in llms, f"llms.txt omits {path}")
    require("available on the App Store" in llms and APP_STORE_URL in llms, "llms.txt must name the released App Store download")
    return pages, resources


def browser_check(root, browser, base_url, resources):
    base_url = base_url.rstrip("/")
    require(urlsplit(base_url).scheme in ("http", "https"), "Browser check needs an HTTP origin")
    paths = sorted(set(PAGES) | resources | {"/robots.txt", "/sitemap.xml", "/llms.txt", "/404.html"})
    expected = {}
    for path in paths:
        file = PAGES.get(path, path.lstrip("/"))
        expected[path] = hashlib.sha256((root / file).read_bytes()).hexdigest()
    subprocess.run([browser, "goto", base_url + "/"], check=True, capture_output=True, text=True, timeout=40)
    expression = """return await (async () => {
      const paths = PATHS;
      const records = await Promise.all(paths.map(async path => {
        const response = await fetch(path, {cache: 'no-store'});
        const bytes = await response.arrayBuffer();
        const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
        const text = path.endsWith('/') || path === '/404.html' ? new TextDecoder().decode(bytes) : '';
        const document = new DOMParser().parseFromString(text, 'text/html');
        return {path, status: response.status, url: response.url, sha256: digest, contentType: response.headers.get('content-type'), robotsHeader: response.headers.get('x-robots-tag'), robotsMeta: document.querySelector('meta[name=robots]')?.content || null};
      }));
      const redirects = await Promise.all(['/docs', '/tutorials', '/support', '/privacy', '/terms'].map(async path => {
        const response = await fetch(path, {cache: 'no-store'});
        return {path, status: response.status, url: response.url};
      }));
      const missing = await fetch('/seo-validation-missing-page', {cache: 'no-store'});
      return JSON.stringify({origin: location.origin, records, redirects, missingStatus: missing.status});
    })()""".replace("PATHS", json.dumps(paths))
    result = subprocess.run([browser, "js", expression], check=True, capture_output=True, text=True, timeout=90)
    data = json.loads(result.stdout)
    require(data["origin"] == base_url, "Browser landed on an unexpected origin")
    for record in data["records"]:
        path = record["path"]
        require(record["status"] == 200 and record["url"] == base_url + path, f"{path}: unexpected response status or URL")
        require(record["sha256"] == expected[path], f"{path}: served bytes differ from source")
        if path in PAGES:
            require("text/html" in (record["contentType"] or ""), f"{path}: wrong content type")
            require(record["robotsMeta"] == "index, follow", f"{path}: unexpected served robots metadata")
            require(not any(value in (record["robotsHeader"] or "").lower() for value in ("noindex", "none")), f"{path}: server forbids indexing")
    for redirect in data["redirects"]:
        require(redirect["status"] == 200 and redirect["url"] == base_url + redirect["path"] + "/", f"{redirect['path']}: slash redirect failed")
    require(data["missingStatus"] == 404, "Missing URL is a soft 404")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--browser", help="Path to an isolated gstack browse CLI or wrapper")
    parser.add_argument("--base-url", help="Local or published HTTP origin to compare with this source")
    args = parser.parse_args()
    require(bool(args.browser) == bool(args.base_url), "Use --browser and --base-url together")
    pages, resources = validate(args.root)
    report = {"result": "pass", "sourcePages": list(pages), "linkedResources": len(resources), "browser": None}
    if args.browser:
        report["browser"] = browser_check(args.root, args.browser, args.base_url, resources)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, ET.ParseError, OSError, subprocess.SubprocessError) as error:
        print(f"SEO validation failed: {error}", file=sys.stderr)
        sys.exit(1)
