import os

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.user import Role, User


def main() -> None:
    password_hash = os.getenv("BOOTSTRAP_ADMIN_PASSWORD_HASH")
    if not password_hash:
        return

    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin").strip().lower()
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@blueashdigital.tech").strip().lower()
    display_name = os.getenv("BOOTSTRAP_ADMIN_DISPLAY_NAME", "Portal Administrator").strip()

    with SessionLocal() as db:
        existing = db.scalar(select(User).where((User.username == username) | (User.email == email)))
        if existing:
            print(f"Bootstrap administrator already exists: {existing.username}")
            return

        user = User(
            username=username,
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            role=Role.ADMINISTRATOR,
            enabled=True,
        )
        db.add(user)
        db.commit()
        print(f"Bootstrap administrator created: {username}")


if __name__ == "__main__":
    main()
