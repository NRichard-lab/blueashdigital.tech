import argparse
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import Role, User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first portal administrator.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    if len(password) < 12:
        raise SystemExit("Use a password with at least 12 characters.")

    username = args.username.strip().lower()
    email = args.email.strip().lower()

    with SessionLocal() as db:
        existing = db.scalar(select(User).where((User.username == username) | (User.email == email)))
        if existing:
            raise SystemExit("A user with that username or email already exists.")
        user = User(
            username=username,
            email=email,
            display_name=args.display_name,
            password_hash=hash_password(password),
            role=Role.ADMINISTRATOR,
            enabled=True,
        )
        db.add(user)
        db.commit()
        print(f"Administrator created: {username}")


if __name__ == "__main__":
    main()

