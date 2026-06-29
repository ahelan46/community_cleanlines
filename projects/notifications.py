from django.contrib.auth.models import User
from django.db.models import Q

from .models import Notification


ROLE_VARIANTS = {
    "admin": {"admin"},
    "project_manager": {"project_manager", "project-manager", "project manager", "projectmanager"},
    "team_leader": {"team_leader", "team-leader", "team leader", "teamleader"},
    "team_member": {"team_member", "team-member", "team member", "teammember"},
    "client": {"client"},
}


def normalize_role(role):
    if not role:
        return ""
    normalized = "_".join(str(role).strip().lower().replace("-", " ").split())
    role_aliases = {
        "projectmanager": "project_manager",
        "teamleader": "team_leader",
        "teammember": "team_member",
    }
    return role_aliases.get(normalized, normalized)


def user_has_role(user, roles):
    if not user:
        return False

    normalized_roles = {normalize_role(role) for role in roles if role}
    if "admin" in normalized_roles and user.is_superuser:
        return True

    profile = getattr(user, "profile", None)
    user_role = normalize_role(getattr(profile, "role", ""))
    return user_role in normalized_roles


def users_with_roles(roles, include_superusers=False):
    normalized_roles = {normalize_role(role) for role in roles if role}
    if not normalized_roles:
        return User.objects.none()

    role_filter = Q()
    for role in normalized_roles:
        for variant in ROLE_VARIANTS.get(role, {role}):
            role_filter |= Q(profile__role__iexact=variant)

    queryset = User.objects.filter(role_filter)
    if include_superusers:
        queryset = queryset | User.objects.filter(is_superuser=True)
    return queryset.distinct()


def create_notification(user, message):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return Notification.objects.create(user=user, message=message)


def create_notifications_for_users(users, message, exclude_user_ids=None, allowed_roles=None):
    exclude_user_ids = set(exclude_user_ids or [])
    sent_user_ids = set()
    created_notifications = []
    normalized_allowed_roles = {normalize_role(role) for role in (allowed_roles or []) if role}

    for user in users:
        if not user:
            continue
        if user.id in exclude_user_ids or user.id in sent_user_ids:
            continue
        if normalized_allowed_roles and not user_has_role(user, normalized_allowed_roles):
            continue
        notification = create_notification(user, message)
        if notification:
            created_notifications.append(notification)
            sent_user_ids.add(user.id)

    return created_notifications


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            "header_notifications": [],
            "header_notifications_unread_count": 0,
        }

    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    return {
        "header_notifications": notifications[:5],
        "header_notifications_unread_count": notifications.filter(is_read=False).count(),
    }
