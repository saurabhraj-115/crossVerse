"""Create payload indexes on the scriptures collection for faster filtering."""

from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


def create_indexes():
    settings = get_settings()
    client_q = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, timeout=60)

    indexes = [
        ("book",      PayloadSchemaType.KEYWORD),
        ("reference", PayloadSchemaType.KEYWORD),
        ("chapter",   PayloadSchemaType.INTEGER),
        ("verse",     PayloadSchemaType.INTEGER),
    ]
    # religion is already indexed (detected from the collection schema earlier)

    for field, schema in indexes:
        print(f"Creating index on '{field}'...")
        client_q.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name=field,
            field_schema=schema,
        )
        print(f"  done: {field}")

    print("All indexes created.")


if __name__ == "__main__":
    create_indexes()
