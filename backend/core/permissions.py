"""Custom DRF permissions for role-based access control."""
from rest_framework.permissions import BasePermission
from apps.users.models import UserRole


class IsStudent(BasePermission):
    """Allow access only to verified students."""
    message = "این عملیات فقط برای دانشجویان مجاز است."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.STUDENT
        )


class IsEmployer(BasePermission):
    """Allow access only to verified employers."""
    message = "این عملیات فقط برای کارفرمایان مجاز است."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.EMPLOYER
        )


class IsVerifiedEmployer(BasePermission):
    """Employer must be verified by admin to post projects."""
    message = "حساب شما هنوز تأیید نشده است. لطفاً منتظر بمانید."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.EMPLOYER
            and request.user.is_verified
        )


class IsPlatformAdmin(BasePermission):
    """Allow access only to platform admins."""
    message = "این عملیات فقط برای مدیران پلتفرم مجاز است."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.ADMIN
        )


class IsOwnerOrAdmin(BasePermission):
    """Object-level permission: only the owner or admin can access."""
    message = "شما مجاز به دسترسی به این منبع نیستید."

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.ADMIN:
            return True
        # Support both user FK and direct user objects
        owner = getattr(obj, "user", None) or getattr(obj, "employer", None) or getattr(obj, "student", None)
        return owner == request.user
