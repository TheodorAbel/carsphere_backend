from rest_framework import permissions

class IsDealer(permissions.BasePermission):
    """
    Allows access only to users with the DEALER role.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'DEALER')

class IsUser(permissions.BasePermission):
    """
    Allows access only to users with the USER role.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'USER')

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the dealer who owns the car.
        # This assumes the model has a 'dealer' field.
        if hasattr(obj, 'dealer'):
            return obj.dealer == request.user
        # For bookings, it might be 'user'
        if hasattr(obj, 'user'):
            return obj.user == request.user
            
        return False
