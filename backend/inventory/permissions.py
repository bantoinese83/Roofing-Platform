from rest_framework.permissions import BasePermission


class IsOwnerOrManager(BasePermission):
    """
    Custom permission to only allow owners and managers to access inventory.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.role in ['owner', 'manager', 'admin']


class IsTechnicianOrHigher(BasePermission):
    """
    Custom permission to allow technicians and higher roles to view inventory.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Read-only access for technicians
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user.role in ['owner', 'manager', 'admin', 'technician']

        # Write access only for managers and above
        return request.user.role in ['owner', 'manager', 'admin']


class CanManageSuppliers(BasePermission):
    """
    Permission to manage suppliers - only managers and owners.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.role in ['owner', 'manager', 'admin']


class CanManagePurchaseOrders(BasePermission):
    """
    Permission to manage purchase orders - only managers and owners.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.role in ['owner', 'manager', 'admin']
