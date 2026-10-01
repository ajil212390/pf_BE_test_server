from django.contrib.auth.hashers import check_password, make_password
from django.utils.crypto import constant_time_compare


def hash_password(raw_password):
    if not isinstance(raw_password, str) or not raw_password:
        raise ValueError('Password is required.')
    return make_password(raw_password)


def verify_and_upgrade_password(instance, field_name, raw_password):
    if not isinstance(raw_password, str) or not raw_password:
        return False

    stored_password = getattr(instance, field_name, None)
    if not isinstance(stored_password, str) or not stored_password:
        return False

    if check_password(raw_password, stored_password):
        return True

    if not constant_time_compare(stored_password, raw_password):
        return False

    try:
        setattr(instance, field_name, make_password(raw_password))
        instance.save(update_fields=[field_name])
    except Exception:
        pass
    return True