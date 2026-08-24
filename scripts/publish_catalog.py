from __future__ import annotations

import argparse
import os

from europe_visa_jobs.catalog import publish_catalog
from europe_visa_jobs.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish the durable global Career Radar catalog")
    parser.add_argument("--output", default="data/catalog")
    parser.add_argument("--version", default=os.environ.get("GITHUB_RUN_ID", "local"))
    args = parser.parse_args()
    with SessionLocal() as session:
        manifest = publish_catalog(session, args.output, dataset_version=str(args.version))
    print(f"published {manifest.payload} sha256={manifest.sha256} jobs dataset={manifest.job_dataset_version}")


if __name__ == "__main__":
    main()
