import requests

from weaviate_schema.schema import SCHEMA_COLLECTIONS

BASE = "http://localhost:8081/v1/schema"


def main() -> None:
    current = requests.get(BASE, timeout=10)
    current.raise_for_status()
    existing = {c["class"] for c in current.json().get("classes", [])}

    for collection in SCHEMA_COLLECTIONS:
        if collection["class"] in existing:
            continue
        resp = requests.post(BASE, json=collection, timeout=10)
        resp.raise_for_status()


if __name__ == "__main__":
    main()
