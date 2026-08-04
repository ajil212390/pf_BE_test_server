from rest_framework import serializers
from .models import Products, Productcategory, Productunit
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
