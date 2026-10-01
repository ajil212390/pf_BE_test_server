from rest_framework import viewsets
from rest_framework.permissions import BasePermission, SAFE_METHODS

from ..models import Company, Companycategory
from ..serializers import CompanySerializer, CompanyCategorySerializer


class CompanyDirectoryPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or getattr(request.user, 'role', None) == 'admin'


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [CompanyDirectoryPermission]


class CompanyCategoryViewSet(viewsets.ModelViewSet):
    queryset = Companycategory.objects.all()
    serializer_class = CompanyCategorySerializer
    permission_classes = [CompanyDirectoryPermission]
