import argparse
import json

from app.database.session import SessionLocal
from app.services.application_auth_service import cleanup_application_auth


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete one bounded batch of expired application authentication records.")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    with SessionLocal() as db:
        result = cleanup_application_auth(db, batch_size=args.batch_size)
        db.commit()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
