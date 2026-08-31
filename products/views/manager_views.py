from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import (
    SupplierManager,
    SupplierExecutive,
    SupplierOrder,
    SupplierOrderItem,
    ExecutiveAllocation,
    Supplieruser,
)


# ---------------------------------------------------------------------------
# SUPPLIER MANAGER ENDPOINTS
# ---------------------------------------------------------------------------

@api_view(['POST'])
def register_supplier_manager(request):
    """Register a new Supplier Manager under a Supplier Head (SupplierUser)."""
    data = request.data
    supplier_user_id = data.get('supplier_user_id')
    name = data.get('manager_name')
    username = data.get('manager_username')
    password = data.get('manager_password')
    phone = data.get('manager_phone', '')
    area = data.get('manager_area', '')

    if not all([supplier_user_id, name, username, password]):
        return Response({'error': 'supplier_user_id, manager_name, manager_username, and manager_password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        supplier_user = Supplieruser.objects.get(supplieruserid=supplier_user_id)
    except Supplieruser.DoesNotExist:
        return Response({'error': 'Supplier Head not found.'}, status=status.HTTP_404_NOT_FOUND)

    if SupplierManager.objects.filter(manager_username__iexact=username).exists():
        return Response({'error': 'Username already taken.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mgr = SupplierManager.objects.create(
            supplier_user=supplier_user,
            manager_name=name,
            manager_username=username,
            manager_password=password,
            manager_phone=phone,
            manager_area=area,
        )
        return Response({
            'message': 'Manager registered successfully',
            'manager_id': mgr.manager_id,
            'manager_name': mgr.manager_name,
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login_supplier_manager(request):
    """Supplier Manager login endpoint."""
    data = request.data
    username = data.get('username') or data.get('manager_username')
    password = data.get('password') or data.get('manager_password')

    if not username or not password:
        return Response({'error': 'username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        manager = SupplierManager.objects.select_related('supplier_user').get(
            manager_username__iexact=username
        )
        if manager.manager_password == password:
            return Response({
                'message': 'Login successful',
                'manager_id': manager.manager_id,
                'manager_name': manager.manager_name,
                'manager_phone': manager.manager_phone or '',
                'manager_area': manager.manager_area or '',
                'supplier_user_id': manager.supplier_user_id,
                'supplier_name': manager.supplier_user.suppliername or '',
                'role': 'manager',
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except SupplierManager.DoesNotExist:
        return Response({'error': 'Username not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_supplier_managers(request, supplier_user_id):
    """Get all managers under a Supplier Head."""
    try:
        managers = SupplierManager.objects.filter(supplier_user_id=supplier_user_id).order_by('manager_name')
        result = []
        for mgr in managers:
            exec_count = SupplierExecutive.objects.filter(manager=mgr).count()
            order_count = SupplierOrder.objects.filter(
                executive__manager=mgr
            ).count()
            result.append({
                'manager_id': mgr.manager_id,
                'manager_name': mgr.manager_name,
                'manager_username': mgr.manager_username,
                'manager_phone': mgr.manager_phone or '',
                'manager_area': mgr.manager_area or '',
                'executive_count': exec_count,
                'order_count': order_count,
                'created_at': mgr.created_at,
            })
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_manager_dashboard(request, manager_id):
    """Get full dashboard data for a Supplier Manager: executives, orders with items, stats."""
    try:
        manager = SupplierManager.objects.select_related('supplier_user').get(manager_id=manager_id)
        executives = SupplierExecutive.objects.filter(manager=manager)
        exec_ids = list(executives.values_list('executiveid', flat=True))

        orders = SupplierOrder.objects.filter(executive_id__in=exec_ids).select_related('company', 'executive').order_by('-created_at')

        total_orders = orders.count()
        total_amount = sum(float(o.total_amount) for o in orders)

        exec_list = []
        for ex in executives:
            alloc_count = ExecutiveAllocation.objects.filter(executive=ex).count()
            exec_orders = orders.filter(executive=ex).count()
            exec_list.append({
                'executive_id': ex.executiveid,
                'name': ex.executive_name,
                'username': ex.executive_username,
                'phone': ex.executive_phone or '',
                'allocated_companies': alloc_count,
                'orders_taken': exec_orders,
            })

        recent_orders = []
        for o in orders[:50]:
            items = SupplierOrderItem.objects.filter(order=o).select_related('product')
            item_list = []
            for item in items:
                item_list.append({
                    'product_name': item.product.productname if item.product else 'Product',
                    'quantity': item.quantity,
                    'price': float(item.price_at_order),
                })
            recent_orders.append({
                'order_id': o.order_id,
                'company_name': o.company.companyname if o.company else 'N/A',
                'executive_name': o.executive.executive_name if o.executive else 'N/A',
                'total_amount': float(o.total_amount),
                'created_at': o.created_at,
                'items': item_list,
            })

        return Response({
            'manager_id': manager.manager_id,
            'manager_name': manager.manager_name,
            'manager_area': manager.manager_area or '',
            'supplier_name': manager.supplier_user.suppliername or '',
            'stats': {
                'total_executives': executives.count(),
                'total_orders': total_orders,
                'total_amount': total_amount,
            },
            'executives': exec_list,
            'recent_orders': recent_orders,
        }, status=status.HTTP_200_OK)
    except SupplierManager.DoesNotExist:
        return Response({'error': 'Manager not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_supplier_manager(request, manager_id):
    """Delete a Supplier Manager (and cascade their executives)."""
    try:
        manager = SupplierManager.objects.get(manager_id=manager_id)
        manager.delete()
        return Response({'message': 'Manager deleted successfully.'}, status=status.HTTP_200_OK)
    except SupplierManager.DoesNotExist:
        return Response({'error': 'Manager not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
