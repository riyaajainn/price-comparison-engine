import requests
import urllib.parse

def test_reliance():
    q = "Samsung S25 Ultra"
    encoded_q = urllib.parse.quote(q)
    api_url = f"https://www.reliancedigital.in/rcom/search/v2/productlist?q={encoded_q}&size=24&suggestions=true"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.reliancedigital.in/"
    }
    
    print(f"[*] Fetching: {api_url}")
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        print(f"[*] Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            products = data.get("data", {}).get("results", [])
            print(f"[*] Found {len(products)} products.")
            for p in products:
                print(f"  - {p.get('name')}")
        else:
            print(f"[*] Error Body: {response.text[:200]}")
    except Exception as e:
        print(f"[*] Exception: {e}")

if __name__ == "__main__":
    test_reliance()
