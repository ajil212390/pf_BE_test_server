from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from ..models import (
    SupplierProduct, Supplier, Products, Company,
    Supplieruser, SupplierManager, SupplierExecutive, ExecutiveAllocation,
)

def _get_product_taxonomy(product):
    category = getattr(product, 'productcategoryid', None)
    unit = getattr(product, 'productunitid', None)
    return (
        getattr(category, 'productcategoryname', '') or '',
        getattr(unit, 'productunitname', '') or '',
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
        role = request.user.role

        if role == 'company':
            try:
                requested_company_id = int(company_id)
            except (TypeError, ValueError):
                return Response({'error': 'A company context is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if requested_company_id != request.user.company_id:
                return Response({'error': 'Not authorized for this company.'}, status=status.HTTP_403_FORBIDDEN)
            company_id = request.user.company_id
            local_supplier = Supplier.objects.filter(
                supplierid=supplier_id,
                companyid_id=company_id,
            ).first()
            if not local_supplier:
                return Response({'error': 'Supplier is not connected to this company.'}, status=status.HTTP_404_NOT_FOUND)
            supp_user = Supplieruser.objects.filter(
                Q(supplieruserphone=local_supplier.supplierphonenumber)
                | Q(supplierusergstnumber=local_supplier.suppliergst)
            ).first()
        elif role == 'executive':
            requested_executive_id = request.user.executive_id or getattr(request.user, 'user_id', None)
            if executive_id and requested_executive_id and int(executive_id) != requested_executive_id:
                return Response({'error': 'Not authorized for this executive.'}, status=status.HTTP_403_FORBIDDEN)
            executive_id = requested_executive_id or (int(executive_id) if executive_id else None)
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                return Response({'error': 'A company context is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not ExecutiveAllocation.objects.filter(
                executive_id=executive_id,
                company_id=company_id,
            ).exists():
                return Response({'error': 'Executive is not allocated to this company.'}, status=status.HTTP_403_FORBIDDEN)
            supp_user = None
        elif role == 'manager':
            requested_manager_id = request.user.manager_id or getattr(request.user, 'user_id', None)
            if manager_id and requested_manager_id and int(manager_id) != requested_manager_id:
                return Response({'error': 'Not authorized for this manager.'}, status=status.HTTP_403_FORBIDDEN)
            manager_id = requested_manager_id or (int(manager_id) if manager_id else None)
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                return Response({'error': 'A company context is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not ExecutiveAllocation.objects.filter(
                executive__manager_id=manager_id,
                company_id=company_id,
            ).exists():
                return Response({'error': 'This manager has no executive allocated to the company.'}, status=status.HTTP_403_FORBIDDEN)
            supp_user = None
        elif role == 'supplier':
            if int(supplier_id) not in {request.user.supplier_user_id, request.user.supplier_id}:
                return Response({'error': 'Not authorized for this supplier.'}, status=status.HTTP_403_FORBIDDEN)
            supp_user = Supplieruser.objects.filter(supplieruserid=request.user.supplier_user_id).first()
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                return Response({'error': 'A company context is required.'}, status=status.HTTP_400_BAD_REQUEST)
        elif role == 'admin':
            if not company_id:
                return Response({'error': 'A company context is required.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Not authorized to view supplier products.'}, status=status.HTTP_403_FORBIDDEN)

        # 1. Resolve Supplieruser context from executive_id, manager_id, or supplier_id
        if role == 'executive':
            exe = SupplierExecutive.objects.select_related('manager', 'supplier_user').filter(executiveid=executive_id).first()
            if exe:
                supp_user = exe.supplier_user or (exe.manager.supplier_user if exe.manager else None)
        elif role == 'manager':
            mgr = SupplierManager.objects.select_related('supplier_user').filter(manager_id=manager_id).first()
            if mgr:
                supp_user = mgr.supplier_user

        if role == 'admin' and not supp_user and supplier_id:
            supp_user = Supplieruser.objects.filter(supplieruserid=supplier_id).first()

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
            if role in ('executive', 'manager') and company_id:
                company_products = Products.objects.filter(
                    companyid=company_id
                ).select_related('productcategoryid', 'productunitid')
                data = []
                for p in company_products:
                    cat_name, unit_name = _get_product_taxonomy(p)
                    data.append({
                        'id': None,
                        'supplier_product_id': None,
                        'supplierproductid': None,
                        'product_id': p.productid,
                        'productid': p.productid,
                        'supplier_id': None,
                        'supplierid': None,
                        'company_id': company_id,
                        'companyid': company_id,
                        'product_name': p.productname,
                        'product_price': float(p.productprice or 0),
                        'supplier_price': float(p.productprice or 0),
                        'is_active': True,
                        'category_name': cat_name,
                        'unit': unit_name,
                    })
                return Response(data, status=status.HTTP_200_OK)
            return Response({'error': 'Supplier not found'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Fetch all supplier IDs belonging to this supplier identity
        matching_supplier_ids = [supplier.supplierid]
        if supp_user and role != 'company':
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
            cat_name, unit_name = _get_product_taxonomy(sp.product)

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

        # Fallback: if no SupplierProduct records exist for this supplier+company,
        # return all active company products so executives/managers can still place orders.
        if not data and role in ('executive', 'manager') and company_id:
            company_products = Products.objects.filter(
                companyid=company_id,
                
            ).select_related('productcategoryid', 'productunitid')
            for p in company_products:
                cat_name, unit_name = _get_product_taxonomy(p)
                data.append({
                    'id': None,
                    'supplier_product_id': None,
                    'supplierproductid': None,
                    'product_id': p.productid,
                    'productid': p.productid,
                    'supplier_id': supplier.supplierid,
                    'supplierid': supplier.supplierid,
                    'company_id': company_id,
                    'companyid': company_id,
                    'product_name': p.productname,
                    'product_price': float(p.productprice or 0),
                    'supplier_price': float(p.productprice or 0),
                    'is_active': True,
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
        if request.user.role == 'company':
            supplier = Supplier.objects.filter(
                supplierid=supplier_id,
                companyid_id=request.user.company_id,
            ).first()
            if not supplier:
                return Response({'error': 'Not authorized for this supplier.'}, status=status.HTTP_403_FORBIDDEN)
        elif request.user.role == 'supplier':
            supp_user_obj = Supplieruser.objects.filter(supplieruserid=request.user.supplier_user_id).first()
            if not supp_user_obj:
                return Response({'error': 'Supplier account not found.'}, status=status.HTTP_404_NOT_FOUND)
            supplier = Supplier.objects.filter(supplierid=supplier_id).first()
            if not supplier:
                return Response({'error': 'Supplier not found.'}, status=status.HTTP_404_NOT_FOUND)
            phone_ok = supp_user_obj.supplieruserphone and supplier.supplierphonenumber == supp_user_obj.supplieruserphone
            gst_ok = getattr(supp_user_obj, 'supplierusergst', None) and supplier.suppliergst == supp_user_obj.supplierusergst
            gst_ok2 = getattr(supp_user_obj, 'supplierusergstnumber', None) and supplier.suppliergst == supp_user_obj.supplierusergstnumber
            name_ok = supp_user_obj.supplierusername and supplier.suppliername.lower() == supp_user_obj.supplierusername.lower()
            if not (phone_ok or gst_ok or gst_ok2 or name_ok):
                return Response({'error': 'Not authorized for this supplier.'}, status=status.HTTP_403_FORBIDDEN)
        elif request.user.role == 'admin':
            supplier = Supplier.objects.get(supplierid=supplier_id)
        else:
            return Response({'error': 'Only the owning company or supplier can manage supplier products.'}, status=status.HTTP_403_FORBIDDEN)
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


@api_view(['GET'])
def get_product_suppliers(request, product_id):
    """Return all suppliers associated with / supplying a specific product."""
    try:
        from products.models import SupplierProduct, Supplier
        product = Products.objects.filter(productid=product_id).first()
        if not product:
            return Response({'success': False, 'error': 'Product not found.', 'suppliers': []}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role == 'company':
            if product.companyid_id != request.user.company_id:
                return Response({'error': 'Not authorized for this product.'}, status=status.HTTP_403_FORBIDDEN)
            supplier_products = SupplierProduct.objects.filter(
                product_id=product_id,
                company_id=request.user.company_id,
                is_active=True,
            ).select_related('supplier')
        elif request.user.role == 'admin':
            supplier_products = SupplierProduct.objects.filter(
                product_id=product_id,
                is_active=True,
            ).select_related('supplier')
        else:
            return Response({'error': 'Not authorized to view product suppliers.'}, status=status.HTTP_403_FORBIDDEN)
        suppliers_data = []
        seen_ids = set()
        for sp in supplier_products:
            if sp.supplier and sp.supplier.supplierid not in seen_ids:
                s = sp.supplier
                seen_ids.add(s.supplierid)
                suppliers_data.append({
                    'id': s.supplierid,
                    'name': s.suppliername,
                    'phone': s.supplierphonenumber or '',
                    'address': s.supplieraddress or '',
                    'email': s.supplieremail or '',
                    'gst_number': s.suppliergst or '',
                    'price': float(sp.supplier_price) if sp.supplier_price is not None else None,
                    'is_active': sp.is_active,
                    'is_connected': s.isconnected,
                    'location_coordinates': s.location_coordinates or '',
                })
        return Response({'success': True, 'suppliers': suppliers_data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'success': False, 'error': str(e), 'suppliers': []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
