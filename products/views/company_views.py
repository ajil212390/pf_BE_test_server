from rest_framework import viewsets

from ..models import Company, Companycategory
from ..serializers import CompanySerializer, CompanyCategorySerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class CompanyCategoryViewSet(viewsets.ModelViewSet):
    queryset = Companycategory.objects.all()
    serializer_class = CompanyCategorySerializer
