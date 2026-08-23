from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.role import PortalPermission, PortalRole, RolePermission
from app.models.user import Role, User


@dataclass(frozen=True)
class PermissionDefinition:
    key: str
    label: str
    group: str
    description: str = ""


PERMISSIONS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition("dashboard.view", "View Dashboard", "Dashboard"),
    PermissionDefinition("applications.view", "View Applications", "Applications"),
    PermissionDefinition("applications.launch", "Launch Applications", "Applications"),
    PermissionDefinition("profile.manage", "Manage Own Profile", "Profile"),
    PermissionDefinition("users.view", "View Users", "Users"),
    PermissionDefinition("users.create", "Add Users", "Users"),
    PermissionDefinition("users.edit", "Edit Users", "Users"),
    PermissionDefinition("users.delete", "Delete Users", "Users"),
    PermissionDefinition("applications_admin.view", "View Application Administration", "Applications"),
    PermissionDefinition("applications_admin.create", "Add Applications", "Applications"),
    PermissionDefinition("applications_admin.edit", "Edit Applications", "Applications"),
    PermissionDefinition("applications_admin.delete", "Delete Applications", "Applications"),
    PermissionDefinition("audit.view", "View Audit Log", "Audit"),
    PermissionDefinition("settings.view", "View Settings", "Settings"),
    PermissionDefinition("settings.edit", "Modify Settings", "Settings"),
    PermissionDefinition("roles.view", "View Roles", "Settings"),
    PermissionDefinition("roles.edit", "Manage Roles", "Settings"),
    PermissionDefinition("email_settings.view", "View Email Settings", "Email"),
    PermissionDefinition("email_settings.edit", "Manage Email Settings", "Email"),
    PermissionDefinition("email_settings.test", "Send Test Email", "Email"),
)

PERMISSION_KEYS = {permission.key for permission in PERMISSIONS}
CRITICAL_ADMIN_PERMISSIONS = {"settings.view", "roles.edit", "users.view", "users.edit"}

DEFAULT_ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.ADMINISTRATOR.value: set(PERMISSION_KEYS),
    Role.USER.value: {
        "dashboard.view",
        "applications.view",
        "applications.launch",
        "profile.manage",
    },
}

ROLE_LABELS = {
    Role.ADMINISTRATOR.value: ("Admin", "Full portal administration access."),
    Role.USER.value: ("User", "Standard portal user with assigned application access."),
}


def ensure_permission_catalog(db: Session) -> None:
    for item in PERMISSIONS:
        permission = db.get(PortalPermission, item.key)
        if permission:
            permission.label = item.label
            permission.group = item.group
            permission.description = item.description
        else:
            db.add(PortalPermission(key=item.key, label=item.label, group=item.group, description=item.description))

    for role_key, grants in DEFAULT_ROLE_PERMISSIONS.items():
        name, description = ROLE_LABELS[role_key]
        role = db.scalar(select(PortalRole).where(PortalRole.key == role_key))
        if not role:
            role = PortalRole(key=role_key, name=name, description=description, system=True)
            db.add(role)
            db.flush()
            for permission_key in sorted(grants):
                db.add(RolePermission(role_id=role.id, permission_key=permission_key))
        else:
            role.name = name
            role.description = role.description or description
            role.system = True
    db.commit()


def get_user_permission_keys(db: Session, user: User) -> set[str]:
    role_key = user.role.value if hasattr(user.role, "value") else str(user.role)
    keys = set(
        db.scalars(
            select(RolePermission.permission_key)
            .join(PortalRole, PortalRole.id == RolePermission.role_id)
            .where(PortalRole.key == role_key)
        ).all()
    )
    return keys or set(DEFAULT_ROLE_PERMISSIONS.get(role_key, set()))


def user_has_permission(db: Session, user: User, permission_key: str) -> bool:
    return permission_key in get_user_permission_keys(db, user)


def replace_role_permissions(db: Session, role: PortalRole, permission_keys: set[str]) -> None:
    unknown = permission_keys - PERMISSION_KEYS
    if unknown:
        raise ValueError("Unknown permission keys: " + ", ".join(sorted(unknown)))
    db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    for permission_key in sorted(permission_keys):
        db.add(RolePermission(role_id=role.id, permission_key=permission_key))
