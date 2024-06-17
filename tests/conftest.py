import os
import uuid
import random
from datetime import datetime

import pytest
from model_bakery import baker
from rest_framework.authtoken.models import Token
from django.core.cache import cache

from regloginout.models import ConfirmEmailToken, User

# from django.contrib.auth import authenticate, login, logout


URL_BASE = "http://127.0.0.1:8000/api/v1/"


def get_password(n):
    pas = random.choice(list("ABCDEFGHIGKLMNOPQRSTUVYXWZ"))
    pas = pas + random.choice(list("abcdefghigklmnopqrstuvyxwz"))
    pas = pas + random.choice(list("1234567890"))
    pas = pas + random.choice(list('`~!@#$%^&*()_-+={[}]:;",<.>?'))
    for x in range(n - 4):
        pas = pas + random.choice(
            list(
                '1234567890abcdefghigklmnopqrstuvyxwzABCDEFGHIGKLMNOPQRSTUVYXWZ`~!@#$%^&*()_-+={[}]:;",<.>?'
            )
        )
    return pas


# фикстура для api-client
@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


# fixture for Multiple Test Databases https://merit-network.github.io/django-pytest-multi-database/
@pytest.fixture(autouse=True, scope="session")
def django_db_multiple():
    """
    Ensure all test functions using Django test cases have
    multiple database rollback support.
    """
    from _pytest.monkeypatch import MonkeyPatch
    from django.conf import settings
    from django.test import TestCase
    from django.test import TransactionTestCase

    db_keys = set(settings.DATABASES.keys())

    monkeypatch = MonkeyPatch()
    monkeypatch.setattr(TestCase, "databases", db_keys)
    monkeypatch.setattr(TransactionTestCase, "databases", db_keys)

    yield monkeypatch

    monkeypatch.undo()


# фикстура для регистрации и получения ConfirmEmailToken
@pytest.fixture
def register_user(api_client):
    cache.clear()
    url_view = "user/register/"
    url = URL_BASE + url_view
    num = str(uuid.uuid4())
    email = f"email_{num}@mail.ru"
    password = get_password(16)
    data = {
        "first_name": f"first_name_{num}",
        "last_name": f"last_name_{num}",
        "email": email,
        "password": password,
    }
    response = api_client.post(
        url,
        data=data,
    )
    user = User.objects.all().filter(email=email).get()
    conform_token = (
        ConfirmEmailToken.objects.filter(user_id=user.id)
        .values_list("key", flat=True)
        .get()
    )
    return api_client, user, conform_token, password, response


@pytest.fixture
def register_confirm(register_user):
    api_client, user, confirm_token, password, _ = register_user
    # user confirmation
    url_view = "user/register/confirm/"
    url = URL_BASE + url_view
    data = {
        "email": user.email,
        "token": confirm_token,
    }
    response = api_client.post(
        url,
        data=data,
    )
    return api_client, user, password, response


@pytest.fixture
def login(register_confirm):
    api_client, user, password, _ = register_confirm
    url_view = "user/login/"
    url = URL_BASE + url_view
    data = {
        "email": user.email,
        "password": password,
    }
    response = api_client.post(
        url,
        data=data,
    )
    token = response.json()["Token"]
    return api_client, user, token


@pytest.fixture()
def create_token():
    user = baker.make(
        User,
        is_active=True,
    )
    token, _ = Token.objects.get_or_create(user=user)
    return token.key


@pytest.fixture
def tmp_file(tmp_path, request):
    file_name = "test_at_" + str(datetime.now())
    file_ext = request.param
    file_name = os.path.join(tmp_path, f"{file_name}.{file_ext}")
    with open(file_name, "w+") as file:
        # file.write(io.BytesIO(b"some initial text data"))
        file.write(f"pytest_file path {file_name}")
    return file_name


# for auth0
# https://github.com/mozilla-iam/auth0-tests/tree/master
