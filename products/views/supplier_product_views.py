from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from ..models import SupplierProduct, Supplier, Products, Company

@extend_schema(
    responses={200: inline_serializer(
        name='SupplierProductsResponse',
        fields={
            'id': serializers.IntegerField(),
            'product_id': serializers.IntegerField(),
            'product_name': serializers.CharField(),
            'product_price': serializers.FloatField(),
            'supplier_price': serializers.FloatField(allow_null=True),
            'is_active': serializers.BooleanField(),
        },
        many=True
    )}
)
@api_view(['GET'])
def get_supplier_products(request, supplier_id):
    try:
        supplier = Supplier.objects.get(supplierid=supplier_id)
        # Fetch all supplier IDs associated with this supplier (by GST or name or supplierid)
        matching_supplier_ids = [supplier.supplierid]
        if supplier.suppliergst:
            matching_ids = list(Supplier.objects.filter(suppliergst=supplier.suppliergst).values_list('supplierid', flat=True))
            matching_supplier_ids.extend(matching_ids)
        if supplier.suppliername:
            matching_ids_name = list(Supplier.objects.filter(suppliername=supplier.suppliername).values_list('supplierid', flat=True))
            matching_supplier_ids.extend(matching_ids_name)
        
        matching_supplier_ids = list(set(matching_supplier_ids))

        # Fetch active products assigned to this supplier or its connected records
        queryset = SupplierProduct.objects.filter(supplier_id__in=matching_supplier_ids, is_active=True).select_related('product')
        
        company_id = request.GET.get('companyid')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
            
        data = []
        for sp in queryset:
            data.append({
                'id': sp.id,
                'product_id': sp.product.productid,
                'product_name': sp.product.productname,
                'product_price': float(sp.product.productprice or 0),
                'supplier_price': float(sp.supplier_price) if sp.supplier_price is not None else float(sp.product.productprice or 0),
                'is_active': sp.is_active,
            })
        return Response(data, status=status.HTTP_200_OK)
    except Supplier.DoesNotExist:
        return Response({'error': 'Supplier not found.'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    request=inline_serializer(
        name='ManageSupplierProductsRequest',
        fields={
            'product_ids': serializers.ListField(child=serializers.IntegerField()),
        }
    )
)
@api_view(['POST'])
def manage_supplier_products(request, supplier_id):
    try:
        supplier = Supplier.objects.get(supplierid=supplier_id)
        company = supplier.companyid
        product_ids = request.data.get('product_ids', [])
        
        with transaction.atomic():
            # First, deactivate all existing
            SupplierProduct.objects.filter(supplier=supplier).update(is_active=False)
            
            # Then, activate or create the requested ones
            for pid in product_ids:
                try:
                    product = Products.objects.get(productid=pid, companyid=company)
                    sp, created = SupplierProduct.objects.get_or_create(
                        supplier=supplier,
                        product=product,
                        company=company,
                        defaults={'is_active': True}
                    )
                    if not created:
                        sp.is_active = True
                        sp.save()
                except Products.DoesNotExist:
                    pass
                    
        return Response({'success': True, 'message': 'Supplier products updated successfully'}, status=status.HTTP_200_OK)
    except Supplier.DoesNotExist:
        return Response({'error': 'Supplier not found.'}, status=status.HTTP_404_NOT_FOUND)
