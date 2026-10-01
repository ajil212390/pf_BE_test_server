import uuid
from datetime import datetime, date

from django.db.models import Q
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response

from ..models import Products, Productcategory, Productunit, Users
from ..serializers import ProductSerializer, ProductCategorySerializer, ProductUnitSerializer


class ProductOwnerPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return getattr(request.user, 'role', None) in {'admin', 'company'}

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.user.role == 'admin':
            return True
        return request.user.role == 'company' and obj.companyid_id == request.user.company_id


class ReadOnlyOrAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or getattr(request.user, 'role', None) == 'admin'


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [ProductOwnerPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        role = getattr(self.request.user, 'role', None)
        if role == 'company':
            if not self.request.user.company_id:
                return queryset.none()
            requested_company_id = self.request.query_params.get('companyid')
            requested_user_id = self.request.query_params.get('userid')
            if requested_company_id and requested_company_id != str(self.request.user.company_id):
                return queryset.none()
            if requested_user_id and requested_user_id != str(self.request.user.user_id):
                return queryset.none()
            return queryset.filter(companyid_id=self.request.user.company_id)
        if role == 'enduser':
            company_id = self.request.query_params.get('companyid') or self.request.query_params.get('company_id')
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                return queryset.none()
            return queryset.filter(companyid_id=company_id)
        if role != 'admin':
            return queryset.none()
        company_id = self.request.query_params.get('companyid')
        user_id = self.request.query_params.get('userid')
        if company_id:
            queryset = queryset.filter(companyid=company_id)
        elif user_id:
            try:
                user_obj = Users.objects.get(userid=user_id)
                if user_obj.companyid:
                    queryset = queryset.filter(Q(companyid=user_obj.companyid) | Q(userid=user_obj))
                else:
                    queryset = queryset.filter(userid=user_obj)
            except Users.DoesNotExist:
                queryset = queryset.filter(userid=user_id)
        return queryset

    def get_serializer_context(self):
        return {'request': self.request}

    def _handle_image_uploads(self, request, existing_images_str=''):
        files = request.FILES.getlist('productphotopath')
        retained_images = request.data.get('retained_images', '')

        saved_paths = []
        if retained_images:
            saved_paths.extend([img.strip() for img in retained_images.split(',') if img.strip()])

        for f in files:
            # Generate a unique filename to avoid overwrites
            filename = f"scaled_{uuid.uuid4().hex}_{f.name}"
            # Save file to media root
            file_name = default_storage.save(filename, f)
            saved_paths.append(file_name)

        return ','.join(saved_paths)

    def create(self, request, *args, **kwargs):
        if request.user.role == 'company' and not request.user.company_id:
            return Response({'error': 'Company account has no company.'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
        if 'productphotopath' in request.FILES:
            data['productphotopath'] = self._handle_image_uploads(request)
        data['addtype'] = 'Single'   # mark as single add

        if request.user.role == 'company':
            data['userid'] = request.user.user_id
            data['companyid'] = request.user.company_id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

        if 'productphotopath' in request.FILES or 'retained_images' in request.data:
            data['productphotopath'] = self._handle_image_uploads(request, str(instance.productphotopath or ''))

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = Productcategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [ReadOnlyOrAdminPermission]


class ProductUnitViewSet(viewsets.ModelViewSet):
    queryset = Productunit.objects.all()
    serializer_class = ProductUnitSerializer
    permission_classes = [ReadOnlyOrAdminPermission]
