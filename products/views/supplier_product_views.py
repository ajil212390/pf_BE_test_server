from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from ..models import (
    SupplierProduct, Supplier, Products, Company,
    Supplieruser, SupplierManager, SupplierExecutive,
)

@extend_schema(
    responses={200: inline_serializer(
        name='SupplierProductsResponse',
        fields={
            'id': serializers.IntegerField(),
            'supplier_product_id': serializers.IntegerField(),
            'product_id': serializers.IntegerField(),
            'supplier_id': serializers.IntegerField(),
            'company_id': serializers.IntegerField(),
            'product_name': serializers.CharField(),
            'product_price': serializers.FloatField(),
            'supplier_price': serializers.FloatField(allow_null=True),
            'is_active': serializers.BooleanField(),
            'category_name': serializers.CharField(required=False),
            'unit': serializers.CharField(required=False),
        },
        many=True
    )}
)
@api_view(['GET'])
def get_supplier_products(request, supplier_id):
    try:
        company_id = request.GET.get('companyid') or request.GET.get('company_id')
        executive_id = request.GET.get('executive_id')
        manager_id = request.GET.get('manager_id')

        # 1. Resolve Supplieruser context from executive_id, manager_id, or supplier_id
        supp_user = None
        if executive_id:
            exe = SupplierExecutive.objects.select_related('manager', 'supplier_user').filter(executiveid=executive_id).first()
            if exe:
                supp_user = exe.supplier_user or (exe.manager.supplier_user if exe.manager else None)
        
        if not supp_user and manager_id:
            mgr = SupplierManager.objects.select_related('supplier_user').filter(manager_id=manager_id).first()
            if mgr:
                supp_user = mgr.supplier_user

        if not supp_user and supplier_id:
            supp_user = Supplieruser.objects.filter(supplieruserid=supplier_id).first()
            if not supp_user:
                mgr = SupplierManager.objects.select_related('supplier_user').filter(manager_id=supplier_id).first()
                if mgr:
                    supp_user = mgr.supplier_user
            if not supp_user:
                exe = SupplierExecutive.objects.select_related('manager', 'supplier_user').filter(executiveid=supplier_id).first()
                if exe:
                    supp_user = exe.supplier_user or (exe.manager.supplier_user if exe.manager else None)

        # 2. Resolve Supplier record
        supplier = None
        if company_id:
            # If we know the supplier_user, find the supplier record for THIS company
            if supp_user:
                supp_q = Q(companyid=company_id)
                filter_q = Q(supplierphonenumber=supp_user.supplieruserphone)
                if getattr(supp_user, 'supplierusergst', None):
                    filter_q |= Q(suppliergst=supp_user.supplierusergst)
                if getattr(supp_user, 'supplierusergstnumber', None):
                    filter_q |= Q(suppliergst=supp_user.supplierusergstnumber)
                if supp_user.supplierusername:
                    filter_q |= Q(suppliername__iexact=supp_user.supplierusername)
                
                supplier = Supplier.objects.filter(supp_q & filter_q).first()

            # If not found via supp_user, check if supplier_id matches a Supplier in this company
            if not supplier and supplier_id:
                supplier = Supplier.objects.filter(supplierid=supplier_id, companyid=company_id).first()

            # If supplier_id matches a Supplier from ANOTHER company, resolve counterpart in this company
            if not supplier and supplier_id:
                other_supp = Supplier.objects.filter(supplierid=supplier_id).first()
                if other_supp:
                    supp_q = Q(companyid=company_id)
                    filter_q = Q(supplierphonenumber=other_supp.supplierphonenumber)
                    if other_supp.suppliergst:
                        filter_q |= Q(suppliergst=other_supp.suppliergst)
                    if other_supp.suppliername:
                        filter_q |= Q(suppliername__iexact=other_supp.suppliername)
                    supplier = Supplier.objects.filter(supp_q & filter_q).first()

        # Fallback if no company_id provided or company-specific lookup didn't find one
        if not supplier and supplier_id:
            supplier = Supplier.objects.filter(supplierid=supplier_id).first()
        if not supplier and supp_user:
            supplier = Supplier.objects.filter(supplierphonenumber=supp_user.supplieruserphone).first()

        if not supplier:
            return Response({'error': 'Supplier not found'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Fetch all supplier IDs belonging to this supplier identity
        matching_supplier_ids = [supplier.supplierid]
        if supp_user:
            matching_ids = list(Supplier.objects.filter(supplierphonenumber=supp_user.supplieruserphone).values_list('supplierid', flat=True))
            matching_supplier_ids.extend(matching_ids)
        if supplier.supplierphonenumber:
            matching_ids = list(Supplier.objects.filter(supplierphonenumber=supplier.supplierphonenumber).values_list('supplierid', flat=True))
            matching_supplier_ids.extend(matching_ids)
        if supplier.suppliergst:
            matching_ids = list(Supplier.objects.filter(suppliergst=supplier.suppliergst).values_list('supplierid', flat=True))
            matching_supplier_ids.extend(matching_ids)
        if supplier.suppliername:
            matching_ids_name = list(Supplier.objects.filter(suppliername=supplier.suppliername).values_list('supplierid', flat=True))
            matching_supplier_ids.extend(matching_ids_name)

        matching_supplier_ids = list(set(matching_supplier_ids))

        # Fetch active products assigned to this supplier or its connected records
        queryset = SupplierProduct.objects.filter(
            supplier_id__in=matching_supplier_ids,
            is_active=True
        ).select_related('product', 'product__productcategoryid', 'product__productunitid')

        if company_id:
            queryset = queryset.filter(company_id=company_id)

        data = []
        for sp in queryset:
            cat_name = ''
            if hasattr(sp.product, 'productcategoryid') and sp.product.productcategoryid:
                cat_name = getattr(sp.product.productcategoryid, 'categoryname', '') or ''
            unit_name = ''
            if hasattr(sp.product, 'productunitid') and sp.product.productunitid:
                unit_name = getattr(sp.product.productunitid, 'unitname', '') or ''

            data.append({
                'id': sp.id,
                'supplier_product_id': sp.id,
                'supplierproductid': sp.id,
                'product_id': sp.product.productid,
                'productid': sp.product.productid,
                'supplier_id': sp.supplier_id,
                'supplierid': sp.supplier_id,
                'company_id': sp.company_id,
                'companyid': sp.company_id,
                'product_name': sp.product.productname,
                'product_price': float(sp.product.productprice or 0),
                'supplier_price': float(sp.supplier_price) if sp.supplier_price is not None else float(sp.product.productprice or 0),
                'is_active': sp.is_active,
                'category_name': cat_name,
                'unit': unit_name,
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
