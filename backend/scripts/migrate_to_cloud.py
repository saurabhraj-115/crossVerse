"""
migrate_to_cloud.py — Copy all vectors from local Qdrant to Qdrant Cloud.

Usage:
    QDRANT_CLOUD_URL="https://..." QDRANT_CLOUD_API_KEY="..." python scripts/migrate_to_cloud.py

Or set them in .env and pass via --cloud-url / --cloud-key flags.
"""

import argparse
import os
import sys
import time

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType, PointStruct

COLLECTION = "scriptures"
BATCH_SIZE = 100
VECTOR_SIZE = 1536


def migrate(local_url: str, cloud_url: str, cloud_api_key: str):
    print(f"Connecting to local Qdrant at {local_url}...")
    src = QdrantClient(url=local_url, timeout=60, prefer_grpc=False)

    print(f"Connecting to Qdrant Cloud at {cloud_url}...")
    dst = QdrantClient(url=cloud_url, api_key=cloud_api_key, timeout=60, prefer_grpc=False)

    # --- Verify source ---
    src_collections = {c.name for c in src.get_collections().collections}
    if COLLECTION not in src_collections:
        print(f"ERROR: collection '{COLLECTION}' not found in local Qdrant.")
        sys.exit(1)

    total = src.count(COLLECTION).count
    print(f"Source has {total:,} points in '{COLLECTION}'.")

    # --- Create collection on cloud if needed ---
    dst_collections = {c.name for c in dst.get_collections().collections}
    if COLLECTION not in dst_collections:
        print(f"Creating collection '{COLLECTION}' on cloud...")
        dst.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        dst.create_payload_index(COLLECTION, "religion", PayloadSchemaType.KEYWORD)
        dst.create_payload_index(COLLECTION, "book", PayloadSchemaType.KEYWORD)
        print("Collection created.")
    else:
        existing = dst.count(COLLECTION).count
        print(f"Collection already exists on cloud with {existing:,} points.")
        if existing == total:
            print("Counts match — nothing to migrate. Done.")
            return
        print("Counts differ — continuing migration (upsert is safe to re-run).")

    # --- Scroll + upsert in batches ---
    offset = None
    migrated = 0
    start = time.time()

    while True:
        records, offset = src.scroll(
            collection_name=COLLECTION,
            limit=BATCH_SIZE,
            offset=offset,
            with_vectors=True,
            with_payload=True,
        )

        if not records:
            break

        points = [
            PointStruct(id=r.id, vector=r.vector, payload=r.payload)
            for r in records
        ]
        dst.upsert(collection_name=COLLECTION, points=points)
        migrated += len(records)

        elapsed = time.time() - start
        rate = migrated / elapsed if elapsed > 0 else 0
        eta = (total - migrated) / rate if rate > 0 else 0
        print(
            f"  {migrated:,}/{total:,} points "
            f"({100*migrated/total:.1f}%) "
            f"— {rate:.0f} pts/s "
            f"— ETA {eta/60:.1f} min",
            end="\r",
        )

        if offset is None:
            break

    print(f"\nDone. Migrated {migrated:,} points in {(time.time()-start)/60:.1f} min.")

    # --- Verify ---
    cloud_count = dst.count(COLLECTION).count
    print(f"Cloud now has {cloud_count:,} points.")
    if cloud_count == total:
        print("Verification passed.")
    else:
        print(f"WARNING: expected {total:,}, got {cloud_count:,}. Re-run to upsert missing points.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Qdrant data to cloud.")
    parser.add_argument("--local-url", default="http://localhost:6333")
    parser.add_argument("--cloud-url", default=os.getenv("QDRANT_CLOUD_URL", ""))
    parser.add_argument("--cloud-key", default=os.getenv("QDRANT_CLOUD_API_KEY", ""))
    args = parser.parse_args()

    if not args.cloud_url:
        print("ERROR: set QDRANT_CLOUD_URL env var or pass --cloud-url")
        sys.exit(1)
    if not args.cloud_key:
        print("ERROR: set QDRANT_CLOUD_API_KEY env var or pass --cloud-key")
        sys.exit(1)

    migrate(args.local_url, args.cloud_url, args.cloud_key)
