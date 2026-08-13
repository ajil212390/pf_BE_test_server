from rest_framework import serializers
from .models import Products, Productcategory, Productunit, Company, Companycategory
from .models import EndUser  # add EndUser to the existing import line

class EndUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EndUser
        fields = '__all__'
class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Productcategory
        fields = '__all__'

class ProductUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Productunit
        fields = '__all__'

class CompanyCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Companycategory
        fields = '__all__'

from drf_spectacular.utils import extend_schema_serializer, OpenApiExample

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Company Example',
            value={
                "companyname": "Acme Corp",
                "companyphonenumber": 9876543210,
                "companylocation": "New York",
                "companyaddress": "123 Business St",
                "categoryid": 1
            }
        )
    ]
)
class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    categoryname = serializers.CharField(source='productcategoryid.productcategoryname', read_only=True)
    unitname = serializers.CharField(source='productunitid.productunitname', read_only=True)
    companyname = serializers.CharField(source='companyid.companyname', read_only=True)
    productphotourl = serializers.SerializerMethodField()
    productphotopath = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Products
        fields = '__all__'

    def get_productphotourl(self, obj):
        request = self.context.get('request')
        if obj.productphotopath:
            from django.conf import settings
            paths = str(obj.productphotopath).split(',')
            urls = []
            for path in paths:
                path = path.strip()
                if not path: continue
                if path.startswith('products/'):
                    path = path.replace('products/', '', 1)
                urls.append(request.build_absolute_uri(f"{settings.MEDIA_URL}{path}"))
            return urls
        return []
