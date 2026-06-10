import requests
import json

TOKEN = "polar_oat_BmxzRaFYpFdVig6cQeksDI3FYzAVNnaaMIOaK4JUbQS"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def get_organization():
    print("Fetching Organization...")
    url = "https://api.polar.sh/v1/organizations/"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        if data.get('items'):
            org = data['items'][0]
            print(f"\n✅ FOUND ORGANIZATION ID: {org['id']}")
            return org['id']
    else:
        print(f"Error fetching organization: {response.text}")
        return None

def get_products(org_id):
    if not org_id:
        return
    print(f"\nFetching Products for Org {org_id}...")
    url = f"https://api.polar.sh/v1/products?organization_id={org_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        items = data.get('items', [])
        found = False
        for item in items:
            print(f"Product: {item['name']} - ID: {item['id']} - Price: {item.get('prices', [{}])[0].get('amount_type')}")
            if "OddsMind" in item['name'] or "Pro" in item['name']:
                print(f"\n✅ FOUND PRODUCT ID: {item['id']}")
                found = True
        
        if not found and items:
             print(f"\n⚠️ Did not find 'OddsMind Pro' specifically, but found {items[0]['name']}: {items[0]['id']}")

    else:
        print(f"Error fetching products: {response.text}")

if __name__ == "__main__":
    org_id = get_organization()
    get_products(org_id)
