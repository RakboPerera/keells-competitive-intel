"""
Meta Ad Library Scraper
========================
Scrapes exact brand pages from the Meta Ad Library using page IDs.

Usage:
  python ad_scraper.py                  # Scrape all brands
  python ad_scraper.py --headed         # Watch the browser
  python ad_scraper.py --brand Keells   # Single brand
"""

import json, argparse, time, re, os
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    os.system("pip install playwright")
    os.system("python -m playwright install chromium")
    from playwright.sync_api import sync_playwright

BRANDS = {
    "Keells Super": {
        "page_id": "108836225822670",
        "url": "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=LK&is_targeted_country=false&media_type=all&search_type=page&sort_data[direction]=desc&sort_data[mode]=total_impressions&view_all_page_id=108836225822670",
    },
    "Cargills Food City": {
        "page_id": "155866468723",
        "url": "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=LK&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&view_all_page_id=155866468723",
    },
    "Softlogic Glomark": {
        "page_id": "354233975342508",
        "url": "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=LK&is_targeted_country=false&media_type=all&search_type=page&sort_data[direction]=desc&sort_data[mode]=total_impressions&view_all_page_id=354233975342508",
    },
    "SPAR Sri Lanka": {
        "page_id": "290159608091322",
        "url": "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=LK&is_targeted_country=false&media_type=all&search_type=page&sort_data[direction]=desc&sort_data[mode]=total_impressions&view_all_page_id=290159608091322",
    },
}

OUTPUT_DIR = Path("data")


def scrape_brand(brand_name, url, headed=False, max_scroll=30):
    print(f"  -> Loading: {brand_name}")
    ads = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = ctx.new_page()

        print(f"    URL: {url[:90]}...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            try:
                page.goto(url, wait_until="commit", timeout=60000)
            except Exception as e2:
                print(f"    Failed to load: {str(e2)[:80]}")
                browser.close()
                return ads
        time.sleep(5)

        # Dismiss popups
        for btn_text in ["Allow all cookies", "Allow essential and optional cookies",
                          "Accept all", "Accept", "Allow", "Close", "Not now", "Decline optional cookies"]:
            try:
                btn = page.locator(f'button:has-text("{btn_text}")').first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    time.sleep(1)
                    break
            except Exception:
                pass

        # Click page body to ensure focus for keyboard scrolling
        try:
            page.locator("body").click(position={"x": 640, "y": 400})
        except Exception:
            pass
        time.sleep(1)

        # Scroll to load all ads
        prev_height = 0
        stale = 0
        for i in range(max_scroll):
            # Method 1: Standard window scroll
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except Exception:
                pass
            time.sleep(1)

            # Method 2: Keyboard End key (most reliable for Facebook)
            try:
                page.keyboard.press("End")
            except Exception:
                pass
            time.sleep(1)

            # Method 3: Page Down multiple times
            for _ in range(3):
                try:
                    page.keyboard.press("PageDown")
                except Exception:
                    pass
                time.sleep(0.5)

            # Method 4: Mouse wheel
            try:
                page.mouse.wheel(0, 5000)
            except Exception:
                pass
            time.sleep(2)

            # Click "See more" buttons
            for txt in ["See more results", "See more", "Show more"]:
                try:
                    btn = page.locator(f'div[role="button"]:has-text("{txt}"), span:has-text("{txt}")')
                    if btn.count() > 0 and btn.first.is_visible(timeout=1500):
                        btn.first.click()
                        time.sleep(4)
                        break
                except Exception:
                    pass

            # Check page height
            try:
                h = page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)") or 0
            except Exception:
                h = 0
            print(f"    Scroll {i+1}/{max_scroll} (height: {h})")
            if h == prev_height:
                stale += 1
                if stale >= 5:
                    break
            else:
                stale = 0
            prev_height = h

        # Try to find and scroll the actual ad container (Facebook uses nested scrollable divs)
        try:
            scroll_container = page.evaluate("""() => {
                const divs = document.querySelectorAll('div');
                let best = null;
                let bestH = 0;
                for (const d of divs) {
                    if (d.scrollHeight > d.clientHeight + 100 && d.scrollHeight > bestH) {
                        bestH = d.scrollHeight;
                        best = d;
                    }
                }
                if (best) {
                    best.setAttribute('data-scroll-target', 'true');
                    return {found: true, height: best.scrollHeight, client: best.clientHeight};
                }
                return {found: false};
            }""")
            if scroll_container.get("found"):
                print(f"    Found scroll container (h:{scroll_container['height']}, visible:{scroll_container['client']})")
                # Scroll inside the container
                for j in range(20):
                    page.evaluate("""() => {
                        const el = document.querySelector('[data-scroll-target]');
                        if (el) el.scrollTop = el.scrollHeight;
                    }""")
                    time.sleep(2)
                    new_h = page.evaluate("""() => {
                        const el = document.querySelector('[data-scroll-target]');
                        return el ? el.scrollHeight : 0;
                    }""") or 0
                    print(f"    Container scroll {j+1}/20 (height: {new_h})")
                    if new_h == scroll_container.get("height", 0):
                        break
                    scroll_container["height"] = new_h
        except Exception as e:
            print(f"    Container scroll failed: {str(e)[:60]}")

        # Extract using ALL methods, merge results
        print(f"    Extracting...")
        all_ads = []

        try:
            body = page.locator("body").inner_text(timeout=15000)
            text_ads = extract_from_text(body, brand_name)
            print(f"    Text extraction: {len(text_ads)} ads")
            all_ads.extend(text_ads)
        except Exception as e:
            print(f"    Text extraction failed: {str(e)[:60]}")

        try:
            link_ads = extract_from_links(page, brand_name)
            print(f"    Link extraction: {len(link_ads)} ads")
            all_ads.extend(link_ads)
        except Exception as e:
            print(f"    Link extraction failed: {str(e)[:60]}")

        try:
            html_ads = extract_from_html(page.content(), brand_name)
            print(f"    HTML extraction: {len(html_ads)} ads")
            all_ads.extend(html_ads)
        except Exception as e:
            print(f"    HTML extraction failed: {str(e)[:60]}")

        # Deduplicate across all methods
        seen = set()
        ads = []
        for ad in all_ads:
            aid = ad.get("id", "")
            if aid and aid not in seen and not aid.startswith("ad_"):
                seen.add(aid)
                ads.append(ad)
        # Add hash-based ones that didn't have real IDs
        for ad in all_ads:
            aid = ad.get("id", "")
            if aid.startswith("ad_") and ad.get("text_preview") and ad["text_preview"] not in [a.get("text_preview") for a in ads]:
                ads.append(ad)

        print(f"    Total unique: {len(ads)} ads")
        browser.close()
    return ads


def extract_from_text(body, brand_name):
    ads = []
    parts = re.split(r'(?=Started running on)', body)
    for part in parts:
        if "Started running on" not in part:
            continue
        dm = re.search(r'Started running on\s+(.+?)(?:\n|$)', part)
        start_date = dm.group(1).strip() if dm else None
        platforms = [p for p in ["Facebook", "Instagram", "Messenger", "Audience Network"] if p in part]
        im = re.search(r'Library ID:\s*(\d+)', part)
        ad_id = im.group(1) if im else f"ad_{abs(hash(part[:150]))%1000000}"
        text_preview = ""
        skip = ["Started running", "Platform", "Library ID", "Inactive", "Active",
                "Facebook", "Instagram", "Messenger", "Audience Network", "See ad details", "About this ad"]
        for line in part.split("\n"):
            line = line.strip()
            if len(line) > 20 and not any(s in line for s in skip):
                text_preview = line[:300]
                break
        status = "inactive" if "Inactive" in part[:200] else "active"
        ads.append({
            "id": str(ad_id), "brand": brand_name, "page_name": brand_name,
            "start_date": start_date, "platforms": platforms, "text_preview": text_preview,
            "status": status,
            "ad_snapshot_url": f"https://www.facebook.com/ads/library/?id={ad_id}" if im else None,
            "has_real_id": bool(im),
            "scraped_at": datetime.now().isoformat(),
        })
    seen = set()
    return [a for a in ads if a["id"] not in seen and not seen.add(a["id"])]


def extract_from_links(page, brand_name):
    ads = []
    seen = set()
    try:
        links = page.locator('a[href*="ads/archive/render_ad"], a[href*="ads/library/?id="]').all()
        for link in links:
            href = link.get_attribute("href") or ""
            m = re.search(r'id=(\d+)', href)
            if not m or m.group(1) in seen:
                continue
            ad_id = m.group(1)
            seen.add(ad_id)
            text = ""
            try:
                text = link.locator("xpath=ancestor::div[5]").inner_text(timeout=2000)
            except Exception:
                pass
            dm = re.search(r'Started running on\s+(.+?)(?:\n|$)', text)
            platforms = [p for p in ["Facebook", "Instagram", "Messenger", "Audience Network"] if p in text]
            preview = ""
            for line in text.split("\n"):
                line = line.strip()
                if len(line) > 20 and "Started running" not in line and "Library ID" not in line:
                    preview = line[:300]
                    break
            ads.append({
                "id": ad_id, "brand": brand_name, "page_name": brand_name,
                "start_date": dm.group(1).strip() if dm else None,
                "platforms": platforms, "text_preview": preview, "status": "active",
                "ad_snapshot_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                "scraped_at": datetime.now().isoformat(),
            })
    except Exception:
        pass
    return ads


def extract_from_html(html, brand_name):
    ids = set()
    for pat in [r'ads/archive/render_ad/\?id=(\d+)', r'ads/library/\?id=(\d+)', r'"ad_archive_id"\s*:\s*"?(\d+)"?']:
        ids.update(re.findall(pat, html))
    dates = re.findall(r'Started running on\s+([A-Za-z]+ \d+,\s*\d{4})', html)
    return [{
        "id": aid, "brand": brand_name, "page_name": brand_name,
        "start_date": dates[i] if i < len(dates) else None,
        "platforms": [], "text_preview": "", "status": "active",
        "ad_snapshot_url": f"https://www.facebook.com/ads/library/?id={aid}",
        "scraped_at": datetime.now().isoformat(),
    } for i, aid in enumerate(ids)]


def run_scraper(brands=None, headed=False, max_scroll=30):
    OUTPUT_DIR.mkdir(exist_ok=True)
    if brands is None:
        brands = BRANDS

    print("\n" + "=" * 50)
    print("  META AD LIBRARY SCRAPER")
    print(f"  Brands: {', '.join(brands.keys())}")
    print("=" * 50 + "\n")

    all_data = {}
    for name, config in brands.items():
        print(f"\n{'='*40}\n  {name} (Page: {config['page_id']})\n{'='*40}")
        try:
            ads = scrape_brand(name, config["url"], headed=headed, max_scroll=max_scroll)
        except Exception as e:
            print(f"  Error: {str(e)[:100]}")
            ads = []
        all_data[name] = {
            "ads": ads, "count": len(ads), "page_id": config["page_id"],
            "source_url": config["url"], "collected_at": datetime.now().isoformat(),
        }
        time.sleep(3)

    out = OUTPUT_DIR / "ad_library_data.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, default=str, ensure_ascii=False)

    total = sum(v["count"] for v in all_data.values())
    print(f"\n{'='*50}")
    print(f"  DONE — {total} total ads")
    for n, d in all_data.items():
        print(f"    {n}: {d['count']}")
    print(f"  Saved: {out}")
    print(f"{'='*50}\n")
    return all_data


def main():
    parser = argparse.ArgumentParser(description="Meta Ad Library Scraper")
    parser.add_argument("--brand", type=str, help="Scrape single brand")
    parser.add_argument("--headed", action="store_true", help="Show browser")
    parser.add_argument("--max-scroll", type=int, default=30, help="Max scrolls")
    args = parser.parse_args()

    if args.brand:
        m = {k: v for k, v in BRANDS.items() if args.brand.lower() in k.lower()}
        if not m:
            print(f"Not found. Available: {', '.join(BRANDS.keys())}")
            return
        run_scraper(m, headed=args.headed, max_scroll=args.max_scroll)
    else:
        run_scraper(headed=args.headed, max_scroll=args.max_scroll)


if __name__ == "__main__":
    main()
