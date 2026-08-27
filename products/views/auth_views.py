from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

from ..models import Company, Users, EndUser, Supplieruser
from django.db.models import Q


@extend_schema(
    request=inline_serializer(
        name="RegisterEndUserRequest",
        fields={
            "endusername": serializers.CharField(),
            "enduserpassword": serializers.CharField(),
            "enduseremail": serializers.EmailField(required=False),
            "enduserphone": serializers.CharField(required=False),
        }
    ),
    responses={201: OpenApiResponse(description="Registration successful"), 400: OpenApiResponse(description="Bad request")}
)
@api_view(['POST'])
def register_enduser(request):
    data = request.data
    try:
        if EndUser.objects.filter(endusername__iexact=data.get('endusername')).exists():
            return Response({'error': 'Username already taken.'}, status=status.HTTP_400_BAD_REQUEST)

        enduser = EndUser.objects.create(
            endusername=data.get('endusername'),
            enduserpassword=data.get('enduserpassword'),  # plain text, matching your existing pattern
            enduseremail=data.get('enduseremail'),
            enduserphone=data.get('enduserphone'),
        )
        return Response({
            'message': 'Registration successful',
            'enduserid': enduser.endsuerid,
            'endusername': enduser.endusername,
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="LoginSupplierRequest",
        fields={
            "supplierusername": serializers.CharField(required=False),
            "supplieruserphone": serializers.CharField(required=False),
            "supplieruserpassword": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Login successful"), 400: OpenApiResponse(description="Bad request"), 401: OpenApiResponse(description="Unauthorized"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def login_supplier(request):
    data = request.data
    username_or_phone = data.get('supplierusername') or data.get('username') or data.get('supplieruserphone') or data.get('phone')
    password = data.get('supplieruserpassword') or data.get('password')

    if not username_or_phone or not password:
        return Response({'error': 'Username (or phone) and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        supplier_user = Supplieruser.objects.filter(
            Q(supplierusername__iexact=username_or_phone) |
            Q(supplieruserphone__iexact=username_or_phone)
        ).first()

        if not supplier_user:
            return Response({'error': 'Username or phone not found.'}, status=status.HTTP_404_NOT_FOUND)

        if supplier_user.supplieruserpassword == password:
            return Response({
                'message': 'Login successful',
                'supplieruserid': supplier_user.supplieruserid,
                'supplierid': supplier_user.supplierid_id,
                'suppliername': supplier_user.suppliername or '',
                'supplierusername': supplier_user.supplierusername,
                'supplieruseremail': supplier_user.supplieruseremail or '',
                'supplieruserphone': supplier_user.supplieruserphone or '',
                'supplierusergstnumber': supplier_user.supplierusergstnumber or '',
                'supplieruseraddress': supplier_user.supplieruseraddress or '',
            }, status=status.HTTP_200_OK)
        return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="LoginEndUserRequest",
        fields={
            "endusername": serializers.CharField(),
            "enduserpassword": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Login successful"), 401: OpenApiResponse(description="Unauthorized"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def login_enduser(request):
    data = request.data
    username = data.get('endusername')
    password = data.get('enduserpassword')

    try:
        enduser = EndUser.objects.get(endusername__iexact=username)
        if enduser.enduserpassword == password:
            return Response({
                'message': 'Login successful',
                'enduserid': enduser.endsuerid,
                'endusername': enduser.endusername,
                'enduseremail': enduser.enduseremail or '',
                'enduserphone': enduser.enduserphone or '',
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except EndUser.DoesNotExist:
        return Response({'error': 'Username not found.'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    request=inline_serializer(
        name="RegisterUserRequest",
        fields={
            "companyname": serializers.CharField(required=False),
            "companyphonenumber": serializers.CharField(required=False),
            "username": serializers.CharField(),
            "useremail": serializers.EmailField(required=False),
            "userpassword": serializers.CharField(),
        }
    ),
    responses={201: OpenApiResponse(description="Registration successful"), 400: OpenApiResponse(description="Bad request")}
)
@api_view(['POST'])
def register_user(request):
    data = request.data
    try:
        # Create Company
        company_name = data.get('companyname')
        company_phone = data.get('companyphonenumber')

        company = None
        if company_name:
            company, _ = Company.objects.get_or_create(
                companyname=company_name,
                defaults={'companyphonenumber': company_phone}
            )

        # Create User
        user = Users.objects.create(
            username=data.get('username'),
            useremail=data.get('useremail'),
            userpassword=data.get('userpassword'),  # Warning: Storing plain text password for demo
            companyid=company
        )

        return Response({
            'message': 'Registration successful',
            'userid': user.userid,
            'username': user.username,
            'companyid': company.companyid if company else None
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="LoginUserRequest",
        fields={
            "username": serializers.CharField(),
            "userpassword": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Login successful"), 401: OpenApiResponse(description="Unauthorized"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def login_user(request):
    data = request.data
    username = data.get('username')
    password = data.get('userpassword')

    try:
        user = Users.objects.get(username__iexact=username)
        if user.userpassword == password:
            company = user.companyid
            return Response({
                'message': 'Login successful',
                'userid': user.userid,
                'username': user.username,
                'useremail': user.useremail or '',
                'companyid': company.companyid if company else None,
                'companyname': company.companyname if company else '',
                'companyphonenumber': str(company.companyphonenumber) if company and company.companyphonenumber else '',
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Incorrect password.'}, status=status.HTTP_401_UNAUTHORIZED)
    except Users.DoesNotExist:
        return Response({'error': 'Username not found.'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    request=inline_serializer(
        name="UpdateCompanyRequest",
        fields={
            "userid": serializers.IntegerField(),
            "companyname": serializers.CharField(required=False),
            "companyphonenumber": serializers.CharField(required=False),
        }
    ),
    responses={200: OpenApiResponse(description="Company updated successfully"), 400: OpenApiResponse(description="Bad request"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def update_company(request):
    data = request.data
    user_id = data.get('userid')
    try:
        user = Users.objects.get(userid=user_id)
        company = user.companyid
        if company:
            if 'companyname' in data:
                company.companyname = data['companyname']
            if 'companyphonenumber' in data:
                company.companyphonenumber = data['companyphonenumber']
            company.save()
            return Response({'message': 'Company updated successfully'})
        else:
            return Response({'error': 'No company found for this user'}, status=status.HTTP_404_NOT_FOUND)
    except Users.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="ChangePasswordRequest",
        fields={
            "userid": serializers.IntegerField(),
            "current_password": serializers.CharField(),
            "new_password": serializers.CharField(),
        }
    ),
    responses={200: OpenApiResponse(description="Password changed successfully"), 400: OpenApiResponse(description="Bad request"), 404: OpenApiResponse(description="Not found")}
)
@api_view(['POST'])
def change_password(request):
    data = request.data
    user_id = data.get('userid')
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    try:
        user = Users.objects.get(userid=user_id)
        if user.userpassword != current_password:
            return Response({'error': 'Incorrect current password.'}, status=status.HTTP_400_BAD_REQUEST)

        user.userpassword = new_password
        user.save()
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
    except Users.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
