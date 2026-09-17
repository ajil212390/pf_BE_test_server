# This package re-exports every symbol that products/urls.py imports,
# so urls.py requires zero changes after the views.py → views/ split.

from .auth_views import (
    register_enduser,
    login_enduser,
    login_supplier,
    register_user,
    login_user,
    update_company,
    change_password,
)

from .admin_views import (
    admin_overview,
    admin_companies,
    admin_users,
    admin_products,
    admin_user_products,
    admin_user_customer_supplier_overview,
    admin_company_products,
)

from .company_views import (
    CompanyViewSet,
    CompanyCategoryViewSet,
)

from .product_views import (
    ProductViewSet,
    ProductCategoryViewSet,
    ProductUnitViewSet,
)

from .supplier_views import (
    search_supplier_globally,
    search_local_supplier,
    connect_supplier,
    supplier_bills,
    supplier_dashboard,
    onboard_supplier,
    get_available_suppliers,
)

from .supplier_product_views import (
    get_supplier_products,
    manage_supplier_products, get_product_suppliers,
)

from .chat_views import (
    get_company_conversations,
    get_company_executive_conversations,
    get_enduser_conversations,
    get_executive_conversations,
    get_conversation_messages, get_conversation_details,
    send_message,
    send_order_message,
    get_or_create_company_buyer_profile,
    delete_message,
    update_order_status,
    delete_conversations,
    get_enduser_orders,
    get_company_orders,
    update_fcm_token,
)

from .executive_views import (
    register_supplier_executive,
    login_supplier_executive,
    get_supplier_executives,
    allocate_company_to_executive,
    get_allocated_companies,
    place_executive_order,
    get_supplier_manager_orders,
    get_connected_companies_for_manager,
    get_executive_orders,
    delete_supplier_executive,
)

from .manager_views import (
    register_supplier_manager,
    login_supplier_manager,
    get_supplier_managers,
    get_manager_dashboard,
    delete_supplier_manager,
)

__all__ = [
    # auth
    'register_enduser', 'login_enduser', 'login_supplier',
    'register_user', 'login_user', 'update_company', 'change_password',
    # admin
    'admin_overview', 'admin_companies', 'admin_users', 'admin_products',
    'admin_user_products', 'admin_user_customer_supplier_overview', 'admin_company_products',
    # company
    'CompanyViewSet', 'CompanyCategoryViewSet',
    # product
    'ProductViewSet', 'ProductCategoryViewSet', 'ProductUnitViewSet',
    # supplier
    'search_supplier_globally', 'search_local_supplier', 'connect_supplier',
    'supplier_bills', 'supplier_dashboard', 'onboard_supplier', 'get_available_suppliers',
    'get_supplier_products', 'manage_supplier_products',
    # chat
    'get_company_conversations', 'get_company_executive_conversations', 'get_enduser_conversations', 'get_executive_conversations', 'get_conversation_messages',
    'send_message', 'send_order_message', 'get_or_create_company_buyer_profile', 'delete_message', 'update_order_status',
    'delete_conversations', 'get_enduser_orders', 'get_company_orders', 'update_fcm_token',
    # executive
    'register_supplier_executive', 'login_supplier_executive', 'get_supplier_executives',
    'allocate_company_to_executive', 'get_allocated_companies', 'place_executive_order',
    'get_supplier_manager_orders', 'get_connected_companies_for_manager', 'get_executive_orders', 'delete_supplier_executive',
    # manager
    'register_supplier_manager', 'login_supplier_manager', 'get_supplier_managers',
    'get_manager_dashboard', 'delete_supplier_manager',
]
