import time
import urllib.parse


def search_flipkart(page, query: str, raw_title: str = "") -> list:
    # Always prioritize the clean Search DNA query for reliable store search
    base_query = query if query else raw_title
    search_url = (
        f"https://www.flipkart.com/search?q={urllib.parse.quote(base_query)}"
        f"&otracker=search&marketplace=FLIPKART&category=tyy%2C4io%2Cbe"
    )
    results = []

    print(f"[*] Querying Flipkart: {search_url}")
    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=35000)

        # CAPTCHA handling
        for _ in range(3):
            content = page.content().lower()
            if "verify you are human" in content or "press and hold" in content:
                print("[⚠️] FLIPKART CAPTCHA — please solve in browser then press ENTER...")
                input()
            else:
                break

        # Scroll to load more results
        for _ in range(3):
            page.mouse.wheel(0, 1200)
            time.sleep(1.2)

        anchors = page.locator('a[href*="/p/itm"]').all()
        print(f"[*] Flipkart anchors found: {len(anchors)}")

        if not anchors:
            html = page.content().lower()
            if "no results" in html or "didn't match" in html:
                print("[-] Flipkart: no results for query")

        seen_pids = set()
        for a in anchors:
            try:
                href = a.get_attribute("href") or ""
                if not href:
                    continue

                # Try multiple methods to get the title
                title = a.get_attribute("title") or ""
                if not title:
                    # Current Flipkart list-view title class
                    t_el = a.locator("div.KzDlHZ, div._4rR01T, div.w1YgeL").first
                    if t_el.count():
                        title = t_el.inner_text().strip()
                
                if not title:
                    raw = a.inner_text().strip()
                    lines = [l.strip() for l in raw.split("\n") if len(l.strip()) > 15]
                    title = lines[0] if lines else ""

                if not title or len(title) < 10:
                    continue

                # Skip ads / compare links
                if a.get_attribute("data-ad-type") == "ad":
                    continue
                if "compare" in title.lower():
                    continue

                full_url = href if href.startswith("http") else "https://www.flipkart.com" + href
                full_url = _clean_flipkart_url(full_url)

                pid = full_url.split("pid=")[1].split("&")[0] if "pid=" in full_url else full_url
                if pid in seen_pids:
                    continue
                seen_pids.add(pid)

                results.append({"title": title, "url": full_url})
            except Exception:
                continue
            if len(results) >= 25:
                break

    except Exception as e:
        print(f"[-] Flipkart search error: {e}")

    return results


def _clean_flipkart_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    new_qs = {}
    for key in ("pid", "lid", "marketplace"):
        if key in qs:
            new_qs[key] = qs[key]
    new_query = urllib.parse.urlencode(new_qs, doseq=True)
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, "")
    )
