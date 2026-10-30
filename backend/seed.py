"""Utility script to seed a tenant with the sample corpus."""

import sys
import json
import httpx

def seed(tenant_id: str = "primary-brand"):
    url = f"http://localhost:8000/tenants/{tenant_id}/ingest"
    with open("data/corpus.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Sending {len(data['documents'])} documents to {url}...")
    res = httpx.post(url, json=data, timeout=30.0)
    print("Status:", res.status_code)
    print("Response:", res.json())

if __name__ == "__main__":
    tenant = sys.argv[1] if len(sys.argv) > 1 else "primary-brand"
    seed(tenant)

