import requests
import urllib.parse

def test_croma_api(query):
    encoded_q = urllib.parse.quote(query)
    api_url = f"https://api.croma.com/searchforproducts/v1/search?query={encoded_q}&size=20&currentPage=0&fields=FULL"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://www.croma.com",
        "Referer": "https://www.croma.com/"
    }
    print(f"[*] Testing Croma API for: {query}")
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        print(f"[*] Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            print(f"[*] Found {len(products)} products.")
            for p in products[:3]:
                print(f"  - {p.get('name')}")
        else:
            print(f"[*] Error Body: {response.text[:200]}")
    except Exception as e:
        print(f"[*] Exception: {e}")

if __name__ == "__main__":
    test_croma_api("Samsung S25 Ultra")
    test_croma_api("iPhone 16 Pro")
