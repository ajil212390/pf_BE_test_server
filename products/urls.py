from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, ProductCategoryViewSet, ProductUnitViewSet,
    register_user, login_user,
    admin_overview, admin_companies, admin_users, admin_products,
    admin_user_products, admin_company_products,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', ProductCategoryViewSet)
router.register(r'units', ProductUnitViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', register_user),
    path('login/', login_user),
    path('admin/overview/', admin_overview),
    path('admin/companies/', admin_companies),
    path('admin/users/', admin_users),
    path('admin/products/', admin_products),
    path('admin/user/<int:user_id>/products/', admin_user_products),
    path('admin/company/<int:company_id>/products/', admin_company_products),
]
