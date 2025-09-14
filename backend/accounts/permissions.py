from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners and admins to access certain views.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_owner or request.user.is_admin


class IsManagerOrAbove(permissions.BasePermission):
    """
    Custom permission to only allow managers, owners, and admins to access certain views.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_manager or request.user.is_owner or request.user.is_admin


class IsTechnicianOrAbove(permissions.BasePermission):
    """
    Custom permission to only allow technicians, managers, owners, and admins to access certain views.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_technician or request.user.is_manager or request.user.is_owner or request.user.is_admin


class IsOwnerOfObject(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to access it.
    """

    def has_object_permission(self, request, view, obj):
        # For user objects, check if the user is accessing their own profile
        if hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id
        return False


class RoleBasedPermission(permissions.BasePermission):
    """
    Advanced role-based permission system that checks specific roles for different operations.
    """

    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow all roles if no specific roles are defined
        if not self.allowed_roles:
            return True

        return request.user.role in self.allowed_roles

    def has_object_permission(self, request, view, obj):
        # For user objects, allow users to access their own data
        if hasattr(obj, 'id') and hasattr(request.user, 'id'):
            if obj.id == request.user.id:
                return True

        # Apply role-based permissions
        return self.has_permission(request, view)


# Convenience permission classes for common use cases
class AdminOnly(RoleBasedPermission):
    def __init__(self):
        super().__init__(allowed_roles=['admin'])


class OwnerOnly(RoleBasedPermission):
    def __init__(self):
        super().__init__(allowed_roles=['owner'])


class ManagerAndAbove(RoleBasedPermission):
    def __init__(self):
        super().__init__(allowed_roles=['manager', 'owner', 'admin'])


class TechnicianAndAbove(RoleBasedPermission):
    def __init__(self):
        super().__init__(allowed_roles=['technician', 'manager', 'owner', 'admin'])
