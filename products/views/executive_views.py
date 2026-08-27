import math

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import (
    Company, Supplier, Supplieruser, SupplierBill,
    SupplierExecutive, SupplierManager, ExecutiveAllocation,
    SupplierOrder, SupplierOrderItem, Products, Users,
)
from django.db.models import Q
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes, inline_serializer
from rest_framework import serializers


# ─── GPS helpers ─────────────────────────────────────────────────────────────

def calculate_distance_meters(lat1, lon1, lat2, lon2):
    try:
        R = 6371000  # Earth's radius in meters
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dLon / 2) * math.sin(dLon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return None


def parse_lat_lng(location_str):
    if not location_str:
        return None, None
    try:
        parts = str(location_str).split(',')
        if len(parts) >= 2:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            return lat, lng
    except Exception:
        pass
    return None, None


# ─── Supplier Executive Endpoints ─────────────────────────────────────────────

@api_view(['POST'])
def register_supplier_executive(request):
    data = request.data
    manager_id = data.get('manager_id')
    name = data.get('executive_name')
    username = data.get('executive_username')
    password = data.get('executive_password')
    phone = data.get('executive_phone')

    try:
        manager = SupplierManager.objects.get(manager_id=manager_id)

        if SupplierExecutive.objects.filter(executive_username__iexact=username).exists():
            return Response({'error': 'Username already taken.'}, status=status.HTTP_400_BAD_REQUEST)

        exec_obj = SupplierExecutive.objects.create(
            manager=manager,
            supplier_user=manager.supplier_user,
            executive_name=name,
            executive_username=username,
            executive_password=password,
            executive_phone=phone
        )
        return Response({'message': 'Executive registered successfully', 'executive_id': exec_obj.executiveid}, status=status.HTTP_201_CREATED)
    except SupplierManager.DoesNotExist:
        return Response({'error': 'Manager not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login_supplier_executive(request):
    data = request.data
    username = data.get('username')
    password = data.get('password')

    try:
        executive = SupplierExecutive.objects.select_related('manager', 'manager__supplier_user').get(executive_username__iexact=username)
        if executive.executive_password == password:
            return Response({
                'message': 'Login successful',
                'executive_id': executive.executiveid,
                'executive_name': executive.executive_name,
                'manager_id': executive.manager_id,
                'manager_name': executive.manager.manager_name,
                'supplier_user_id': executive.manager.supplier_user_id,
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except SupplierExecutive.DoesNotExist:
        return Response({'error': 'Username not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_supplier_executives(request, manager_id):
    try:
        executives = SupplierExecutive.objects.filter(manager_id=manager_id).order_by('-created_at')
        result = []
        for ex in executives:
            alloc_count = ExecutiveAllocation.objects.filter(executive=ex).count()
            result.append({
                'executive_id': ex.executiveid,
                'name': ex.executive_name,
                'username': ex.executive_username,
                'phone': ex.executive_phone,
                'allocated_companies': alloc_count,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def allocate_company_to_executive(request):
    data = request.data
    executive_id = data.get('executive_id')
    company_ids = data.get('company_ids', [])

    try:
        executive = SupplierExecutive.objects.get(executiveid=executive_id)
        ExecutiveAllocation.objects.filter(executive=executive).delete()
        for cid in company_ids:
            company = Company.objects.get(companyid=cid)
            ExecutiveAllocation.objects.create(executive=executive, company=company)

        return Response({'message': 'Companies allocated successfully'}, status=status.HTTP_200_OK)
    except SupplierExecutive.DoesNotExist:
        return Response({'error': 'Executive not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Company.DoesNotExist:
        return Response({'error': 'One or more companies not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_allocated_companies(request, executive_id):
    try:
        allocations = ExecutiveAllocation.objects.filter(executive_id=executive_id).select_related('company')
        result = []
        for alloc in allocations:
            c = alloc.company
            result.append({
                'company_id': c.companyid,
                'company_name': c.companyname,
                'company_phone': c.companyphonenumber,
                'address': c.companyaddress,
                'allocated_at': alloc.allocated_at,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def place_executive_order(request):
    data = request.data
    executive_id = data.get('executive_id')
    company_id = data.get('company_id')
    supplier_id = data.get('supplier_id')
    items = data.get('items', [])
    lat = data.get('latitude')
    lng = data.get('longitude')

    try:
        executive = SupplierExecutive.objects.get(executiveid=executive_id)
        company = Company.objects.get(companyid=company_id)

        supplier = None
        if executive.manager and executive.manager.supplier_user:
            supplier = Supplier.objects.filter(supplierphonenumber=executive.manager.supplier_user.supplieruserphone).first()

        if not supplier:
            supplier = Supplier.objects.first()

        total_amount = sum(float(item.get('price', 0)) * int(item.get('quantity', 0)) for item in items)

        order = SupplierOrder.objects.create(
            company=company,
            supplier=supplier,
            executive=executive,
            total_amount=total_amount,
            gps_latitude=lat,
            gps_longitude=lng
        )

        for item in items:
            product_id = item.get('product_id')
            product = Products.objects.get(productid=product_id)
            SupplierOrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.get('quantity', 1),
                price_at_order=item.get('price', 0)
            )

        return Response({'message': 'Order placed successfully', 'order_id': order.order_id}, status=status.HTTP_201_CREATED)
    except Exception as e:
        print("ERROR in place_executive_order:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_supplier_manager_orders(request, manager_id):
    try:
        orders = SupplierOrder.objects.filter(executive__manager_id=manager_id).select_related('company', 'executive').order_by('-created_at')
        result = []
        for o in orders:
            items = SupplierOrderItem.objects.filter(order=o).select_related('product')
            item_list = []
            for item in items:
                item_list.append({
                    'product_name': item.product.productname,
                    'quantity': item.quantity,
                    'price': float(item.price_at_order),
                })

            exec_lat = float(o.gps_latitude) if o.gps_latitude is not None else None
            exec_lng = float(o.gps_longitude) if o.gps_longitude is not None else None

            comp_lat, comp_lng = parse_lat_lng(o.company.companylocation)

            is_verified = False
            distance_meters = None

            if exec_lat is not None and exec_lng is not None:
                if comp_lat is not None and comp_lng is not None:
                    dist = calculate_distance_meters(exec_lat, exec_lng, comp_lat, comp_lng)
                    if dist is not None:
                        distance_meters = round(dist, 1)
                        is_verified = bool(dist <= 500.0)
                else:
                    is_verified = True

            result.append({
                'order_id': o.order_id,
                'company_name': o.company.companyname,
                'executive_name': o.executive.executive_name if o.executive else 'N/A',
                'total_amount': float(o.total_amount),
                'status': o.status,
                'gps_latitude': exec_lat,
                'gps_longitude': exec_lng,
                'company_latitude': comp_lat,
                'company_longitude': comp_lng,
                'distance_meters': distance_meters,
                'is_location_verified': is_verified,
                'created_at': o.created_at,
                'items': item_list,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_connected_companies_for_manager(request, manager_id):
    try:
        mgr = SupplierManager.objects.get(manager_id=manager_id)
        supplier_user = mgr.supplier_user
        suppliers_q = Q()
        if supplier_user.supplierid_id:
            suppliers_q |= Q(supplierid=supplier_user.supplierid_id)
        if supplier_user.supplieruserphone:
            suppliers_q |= Q(supplierphonenumber=supplier_user.supplieruserphone)
        if supplier_user.supplierusergstnumber:
            suppliers_q |= Q(suppliergst=supplier_user.supplierusergstnumber)

        suppliers = Supplier.objects.select_related('companyid').filter(suppliers_q).distinct() if suppliers_q else Supplier.objects.none()

        result = []
        seen_ids = set()
        for s in suppliers:
            c = s.companyid
            if c and c.companyid not in seen_ids:
                seen_ids.add(c.companyid)
                result.append({
                    'companyid': c.companyid,
                    'companyname': c.companyname,
                    'companyphonenumber': c.companyphonenumber,
                    'companylocation': c.companylocation,
                    'companyaddress': c.companyaddress,
                })

        if not result:
            all_comps = Company.objects.all()
            for c in all_comps:
                result.append({
                    'companyid': c.companyid,
                    'companyname': c.companyname,
                    'companyphonenumber': c.companyphonenumber,
                    'companylocation': c.companylocation,
                    'companyaddress': c.companyaddress,
                })

        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_executive_orders(request, executive_id):
    try:
        orders = SupplierOrder.objects.filter(executive_id=executive_id).select_related('company').order_by('-created_at')
        result = []
        for o in orders:
            items = SupplierOrderItem.objects.filter(order=o).select_related('product')
            item_list = []
            for item in items:
                item_list.append({
                    'product_name': item.product.productname,
                    'quantity': item.quantity,
                    'price': float(item.price_at_order),
                })

            exec_lat = float(o.gps_latitude) if o.gps_latitude is not None else None
            exec_lng = float(o.gps_longitude) if o.gps_longitude is not None else None

            comp_lat, comp_lng = parse_lat_lng(o.company.companylocation)
            is_verified = False
            distance_meters = None
            if exec_lat is not None and exec_lng is not None:
                if comp_lat is not None and comp_lng is not None:
                    dist = calculate_distance_meters(exec_lat, exec_lng, comp_lat, comp_lng)
                    if dist is not None:
                        distance_meters = round(dist, 1)
                        is_verified = bool(dist <= 500.0)
                else:
                    is_verified = True

            result.append({
                'order_id': o.order_id,
                'company_name': o.company.companyname,
                'total_amount': float(o.total_amount),
                'status': o.status,
                'gps_latitude': exec_lat,
                'gps_longitude': exec_lng,
                'distance_meters': distance_meters,
                'is_location_verified': is_verified,
                'created_at': o.created_at,
                'items': item_list,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
