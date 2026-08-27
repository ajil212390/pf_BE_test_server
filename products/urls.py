from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, ProductCategoryViewSet, ProductUnitViewSet,
    CompanyViewSet, CompanyCategoryViewSet,
    register_user, login_user, update_company, change_password,
    admin_overview, admin_companies, admin_users, admin_products,
    admin_user_products, admin_company_products,
    admin_user_customer_supplier_overview,
    register_enduser, login_enduser, login_supplier,
    search_supplier_globally, search_local_supplier, connect_supplier, supplier_bills, onboard_supplier, supplier_dashboard,
    get_company_conversations, get_enduser_conversations, get_conversation_messages, send_message, send_order_message, delete_message, update_order_status,
    delete_conversations, get_enduser_orders, get_company_orders,
    register_supplier_executive, login_supplier_executive,
    get_supplier_executives, allocate_company_to_executive,
    get_allocated_companies, place_executive_order, get_supplier_manager_orders,
    get_connected_companies_for_manager, get_executive_orders,
    register_supplier_manager, login_supplier_manager,
    get_supplier_managers, get_manager_dashboard, delete_supplier_manager,
    get_supplier_products, manage_supplier_products,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', ProductCategoryViewSet)
router.register(r'units', ProductUnitViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'companycategories', CompanyCategoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', register_user),
    path('login/', login_user),
    path('update-company/', update_company),
    path('change-password/', change_password),
    path('admin/overview/', admin_overview),
    path('admin/companies/', admin_companies),
    path('admin/users/', admin_users),
    path('admin/products/', admin_products),
    path('admin/user/<int:user_id>/products/', admin_user_products),
    path('admin/user/<int:user_id>/customer-supplier-overview/', admin_user_customer_supplier_overview),
    path('admin/company/<int:company_id>/products/', admin_company_products),
    path('register-enduser/', register_enduser),
    path('login-enduser/', login_enduser),
    path('login-supplier/', login_supplier),
    path('supplier/search/', search_supplier_globally),
    path('supplier/search-local/', search_local_supplier),
    path('supplier/connect/', connect_supplier),
    path('supplier/onboard/', onboard_supplier),
    path('supplier/<int:supplier_user_id>/bills/', supplier_bills),
    path('supplier/<int:supplier_user_id>/dashboard/', supplier_dashboard),
    path('supplier/<int:supplier_id>/products/', get_supplier_products),
    path('supplier/<int:supplier_id>/products/manage/', manage_supplier_products),
    
    # Chat Endpoints
    path('chat/conversations/delete/', delete_conversations),
    path('chat/conversations/company/<int:company_id>/', get_company_conversations),
    path('chat/conversations/enduser/<int:enduser_id>/', get_enduser_conversations),
    path('chat/<int:conversation_id>/messages/', get_conversation_messages),
    path('chat/messages/<int:message_id>/delete/', delete_message),
    path('chat/messages/<int:message_id>/status/', update_order_status),
    path('chat/send/', send_message),
    path('chat/send-order/', send_order_message),
    path('chat/orders/enduser/<int:enduser_id>/', get_enduser_orders),
    path('chat/orders/company/<int:company_id>/', get_company_orders),
    
    # Supplier Executive Endpoints
    path('supplier/executives/register/', register_supplier_executive),
    path('supplier/executives/login/', login_supplier_executive),
    path('supplier/manager/<int:manager_id>/executives/', get_supplier_executives),
    path('supplier/executives/allocate/', allocate_company_to_executive),
    path('supplier/executives/<int:executive_id>/companies/', get_allocated_companies),
    path('supplier/executives/order/', place_executive_order),
    path('supplier/manager/<int:manager_id>/orders/', get_supplier_executives),
    path('supplier/manager/<int:manager_id>/orders-list/', get_supplier_manager_orders),
    path('supplier/manager/<int:manager_id>/connected-companies/', get_connected_companies_for_manager),
    path('supplier/executives/<int:executive_id>/orders/', get_executive_orders),

    # Supplier Manager Endpoints
    path('supplier/managers/register/', register_supplier_manager),
    path('supplier/managers/login/', login_supplier_manager),
    path('supplier/head/<int:supplier_user_id>/managers/', get_supplier_managers),
    path('supplier/managers/<int:manager_id>/dashboard/', get_manager_dashboard),
    path('supplier/managers/<int:manager_id>/delete/', delete_supplier_manager),
]