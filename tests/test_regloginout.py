import warnings

import pytest
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework.authtoken.models import Token

from regloginout.models import User

from .conftest import URL_BASE, get_password

warnings.filterwarnings(action="ignore")

pytestmark = pytest.mark.django_db


def test_example():
    assert True, "Just test example"


# check /api/v1/user/register
def test_user_register(register_user):
    api_client, user, confirm_token, _, response = register_user

    assert user
    assert confirm_token
    assert response.json()["Status"] == True
    assert response.json()["Task_id"]


# check /api/v1/user/register/confirm
def test_register_confirm(register_confirm):
    api_client, _, _, response = register_confirm

    assert response.status_code == 204


# check /api/v1/user/login
def test_user_login(register_confirm):
    api_client, user, password, _ = register_confirm

    # user/login
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
    assert response.status_code == 202
    assert response.json()["Token"] == Token.objects.get(user=user).key


# user/logout
def test_user_logout(login):
    api_client, user, token = login
    url_view = "user/logout/"
    url = URL_BASE + url_view
    headers = {"Authorization": f"Token {token}"}
    response = api_client.post(
        url,
        headers=headers,
    )
    try:
        token = Token.objects.get(user=user)
    except Token.DoesNotExist as e:
        token = str(e)

    assert response.status_code == 204
    assert token == "Token matching query does not exist."


# user/delete
def test_user_delete(login):
    api_client, user, token = login
    url_view = "user/delete/"
    url = URL_BASE + url_view
    headers = {"Authorization": f"Token {token}"}
    response = api_client.delete(
        url,
        headers=headers,
    )
    try:
        user = User.objects.filter(email=user.email).get()
    except User.DoesNotExist as e:
        user = str(e)

    assert response.status_code == 204
    assert user == "User matching query does not exist."


# check details/ [GET]
def test_user_details_get(login):
    api_client, user, token = login

    url_view = "user/details/"
    url = URL_BASE + url_view
    headers = {
        "Authorization": f"Token {token}",
    }
    response = api_client.get(
        url,
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == user.id
    assert response.json()["first_name"] == user.first_name
    assert response.json()["last_name"] == user.last_name
    assert response.json()["email"] == user.email


# check details/ [POST]
def test_user_details_post(login):
    api_client, user, token = login
    url_view = "user/details/"
    url = URL_BASE + url_view
    # Меняем данные пользователя добавив "_new"
    password_new = f"{user.password}_new"
    first_name_new = f"{user.first_name}_new"
    last_name_new = f"{user.last_name}_new"
    data = {
        "first_name": first_name_new,
        "last_name": last_name_new,
        "password": password_new,
    }
    headers = {
        "Authorization": f"Token {token}",
    }
    response = api_client.post(
        url,
        headers=headers,
        data=data,
    )
    assert response.status_code == 202
    assert response.json()["Status"] == True

    # проверяем изменения

    # чтобы проверить новый пароль, выходим из системы
    url_logout = URL_BASE + "user/logout/"
    response = api_client.post(
        url_logout,
        headers=headers,
    )

    # входим в систему с новым паролем
    url_login = URL_BASE + "user/login/"
    data = {
        "email": user.email,
        "password": password_new,
    }
    response = api_client.post(
        url_login,
        data=data,
    )
    token = response.json()["Token"]
    assert response.status_code == 202
    assert response.json()["Status"] == True

    # проверяем новые данные пользователя
    headers = {
        "Authorization": f"Token {token}",
    }
    response = api_client.get(
        url,
        headers=headers,
    )
    assert response.json()["id"] == user.id
    assert response.json()["first_name"] == first_name_new
    assert response.json()["last_name"] == last_name_new


# check user/password_reset
def test_user_password_reset(login):
    api_client, user, _ = login
    url_view = "user/password_reset/"
    url = URL_BASE + url_view
    data = {
        "email": user.email,
    }
    response = api_client.post(
        url,
        data=data,
    )
    token = ResetPasswordToken.objects.get(
        user=user,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert token.key


# check user/password_reset/confirm/
def test_user_password_reset_confirm(login):
    # подготовка: создание пользоателя и токена восстановления пароля
    api_client, user, _ = login
    url_view = "user/password_reset/"
    url = URL_BASE + url_view
    data = {
        "email": user.email,
    }
    api_client.post(
        url,
        data=data,
    )
    token = ResetPasswordToken.objects.get(
        user=user,
    ).key
    # проверка password_reset/confirm/
    url_view = "user/password_reset/confirm/"
    url = URL_BASE + url_view
    password_new = get_password(12)
    data = {"token": token, "password": password_new}
    response = api_client.post(
        url,
        data=data,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    # проверка нового пароля
    url_view = "user/login/"
    url = URL_BASE + url_view
    data = {
        "email": user.email,
        "password": password_new,
    }
    response = api_client.post(
        url,
        data=data,
    )
    assert response.status_code == 202
    assert response.json()["Token"] == Token.objects.get(user=user).key


# start tests
# >>> pytest
# tests coverage
# >>> pytest --cov=uploader_1
# pytest tests/test_regloginout.py
