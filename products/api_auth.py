from django.core import signing
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


_TOKEN_SALT = 'products.role-api-token'
_TOKEN_MAX_AGE = 60 * 60 * 24 * 30
_ALLOWED_ROLES = {'admin', 'company', 'enduser', 'supplier', 'manager', 'executive'}


class ApiPrincipal:
    is_authenticated = True
    is_anonymous = False

    def __init__(self, claims):
        self.role = claims['role']
        self.user_id = claims['user_id']
        self.company_id = claims.get('company_id')
        self.supplier_id = claims.get('supplier_id')
        self.supplier_user_id = claims.get('supplier_user_id')
        self.manager_id = claims.get('manager_id') or (self.user_id if self.role == 'manager' else None)
        self.executive_id = claims.get('executive_id') or (self.user_id if self.role == 'executive' else None)

    @property
    def pk(self):
        return self.user_id


class RoleTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header:
            return None
        scheme, _, token = header.partition(' ')
        if scheme.lower() != 'bearer' or not token:
            raise AuthenticationFailed('Invalid authorization header.')
        try:
            claims = signing.loads(token, salt=_TOKEN_SALT, max_age=_TOKEN_MAX_AGE)
        except signing.SignatureExpired as exc:
            raise AuthenticationFailed('Session expired. Please sign in again.') from exc
        except signing.BadSignature as exc:
            raise AuthenticationFailed('Invalid access token.') from exc
        if (
            not isinstance(claims, dict)
            or claims.get('role') not in _ALLOWED_ROLES
            or not isinstance(claims.get('user_id'), int)
            or claims['user_id'] <= 0
        ):
            raise AuthenticationFailed('Invalid access token.')
        return ApiPrincipal(claims), token

    def authenticate_header(self, request):
        return 'Bearer'


def issue_access_token(role, user_id, **identity):
    if role not in _ALLOWED_ROLES or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError('Invalid token identity.')
    claims = {'role': role, 'user_id': user_id}
    claims.update({key: value for key, value in identity.items() if value is not None})
    return signing.dumps(claims, salt=_TOKEN_SALT, compress=True)
