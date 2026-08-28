import uuid
from datetime import datetime, date

from django.db.models import Q
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.response import Response

from ..models import Products, Productcategory, Productunit, Users
from ..serializers import ProductSerializer, ProductCategorySerializer, ProductUnitSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
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
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
        if 'productphotopath' in request.FILES:
            data['productphotopath'] = self._handle_image_uploads(request)
        data['addtype'] = 'Single'   # mark as single add

        user_id = data.get('userid')
        if user_id:
            try:
                user_obj = Users.objects.get(userid=user_id)
                if user_obj.companyid:
                    data['companyid'] = user_obj.companyid.companyid
            except Users.DoesNotExist:
                pass

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


class ProductUnitViewSet(viewsets.ModelViewSet):
    queryset = Productunit.objects.all()
    serializer_class = ProductUnitSerializer
