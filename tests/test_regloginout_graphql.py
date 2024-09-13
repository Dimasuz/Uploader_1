import uuid
import warnings

import pytest

from regloginout.models import User

from .conftest import URL_BASE, get_password

warnings.filterwarnings(action="ignore")

pytestmark = pytest.mark.django_db

url = URL_BASE + "graphql/"


def test_user_details(login):
    api_client, user, token = login

    body = """
    query GetUser($token: String!) {
        user(token: $token) {
                id
                email
                first_name
                last_name
        }
    }
    """
    variables = {"token": token}

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    # print("test_user_details")
    # print(f"{user=}")
    # print(f"{response.json()=}")

    response_user = response.json()["data"]["user"]

    assert response_user["id"] == str(user.id)
    assert response_user["email"] == user.email
    assert response_user["first_name"] == user.first_name
    assert response_user["last_name"] == user.last_name


def test_graphql_user_details_change(login):
    api_client, user, token = login

    body = """
    mutation TokenMutation($token: String!, $input: UserInput!) {
        user_update(token: $token, input: $input) {
            status
            errors
            query {
                user(token: $token) {
                    id
                    email
                    first_name
                    last_name
                }
            }
        }
    }
    """
    variables = {
        "token": token,
        "input": {
            "email": "1_new@mail.ru",
            "first_name": "first_name_new",
            "last_name": "last_name_new",
            "password": "password_new",
        },
    }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    user_new = User.objects.filter(id=user.id).get()

    # print("test_graphql_user_details_change")
    # print(f"{user=}")
    # print(f"{user_new=}")
    # print(f"{user_new.password=}")
    # print(f"{response.json()=}")

    assert response.status_code == 200
    assert response.json()["data"]["user_update"]["status"] == 202
    assert response.json()["data"]["user_update"]["errors"] == []
    assert user_new.id == user.id
    assert user_new.first_name == "first_name_new"
    assert user_new.last_name == "last_name_new"
    assert user_new.email == "1_new@mail.ru"
    assert user_new.password != user.password


def test_graphql_user_details_change_wrong_password(login):
    api_client, user, token = login

    body = """
    mutation TokenMutation($token: String!, $input: UserInput!) {
        user_update(token: $token, input: $input) {
            status
            errors
            query {
                user(token: $token) {
                    id
                    email
                    first_name
                    last_name
                }
            }
        }
    }
    """
    variables = {
        "token": token,
        "input": {
            "password": "pswrd",
        },
    }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    user_new = User.objects.filter(id=user.id).get()

    # print("test_graphql_user_details_change_wrong_password")
    # print(f"{user=}")
    # print(f"{user_new=}")
    # print(f"{user_new.password=}")
    # print(f"{response.status_code=}")

    assert response.status_code == 200
    assert (
        response.json()["errors"][0]["message"]
        == "String cannot represent value: ['This password is too short. It must contain at least 8 characters.']"
    )
    assert user_new.id == user.id
    assert user_new.password == user.password


def test_graphql_user_create(api_client):
    num = str(uuid.uuid4())
    email = f"email_{num}@mail.ru"
    first_name = f"first_name_{num}"
    last_name = f"last_name_{num}"
    password = get_password(16)

    body = """
    mutation CreateMutation($input: UserInput!) {
        user_create(input: $input) {
            status
            errors
            message
        }
    }
    """
    variables = {
        "input": {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": password,
        }
    }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    user_new = User.objects.filter(email=email).get()

    # print("test_graphql_user_create")
    # print(f"{user_new=}")
    # print(f"{response.json()=}")

    assert response.status_code == 200
    assert response.json()["data"]["user_create"]["status"] == 202
    assert response.json()["data"]["user_create"]["message"]["task_id"]
    assert response.json()["data"]["user_create"]["message"]["token"]
    assert user_new.first_name == first_name
    assert user_new.last_name == last_name


def test_graphql_user_confirm(register_user):
    api_client, user, conform_token, _, _ = register_user

    body = """
    mutation UserConfirm($token: String!, $input: UserInput!) {
        user_confirm(token: $token, input: $input) {
            status
            errors            
        }
    }
    """
    variables = {
        "token": conform_token,
        "input": {
            "email": user.email,
        },
    }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    user_confirm = User.objects.filter(email=user.email).get()

    # print("test_graphql_user_confirm")
    # print(f"{conform_token=}")
    # print(f"{user=}")
    # print(f"{user.is_active=}")
    # print(f"{user_confirm=}")
    # print(f"{user_confirm.is_active=}")
    # print(f"{response.status_code=}")
    # print(f"{response.json()=}")

    assert response.status_code == 200
    assert response.json()["data"]["user_confirm"]["status"] == 204
    assert response.json()["data"]["user_confirm"]["errors"] == []
    assert user_confirm.is_active == True


def test_graphql_user_login(register_confirm):
    api_client, user, password, _ = register_confirm

    body = """
    mutation LoginMutation($input: UserInput!) {
        user_login(input: $input) {
            status
            errors
            message          
        }
    }
    """
    variables = {
        "input": {
            "email": user.email,
            "password": password,
        }
    }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    # print("test_graphql_user_login")
    # print(f"{user.email=}")
    # print(f"{password=}")
    # print(f"{response.status_code=}")
    # print(f"{response.json()=}")

    assert response.status_code == 200
    assert response.json()["data"]["user_login"]["status"] == 202
    assert response.json()["data"]["user_login"]["message"]["task_id"]
    assert response.json()["data"]["user_login"]["message"]["token"]


def test_graphql_user_loguot(login):
    api_client, user, token = login

    body = """
    mutation LogoutMutation($token: String!) {
        user_logout(token: $token) {
            status
            errors            
        }
    }
    """
    variables = {
        "token": token,
    }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    try:
        user.auth_token
    except User.auth_token.RelatedObjectDoesNotExist as exp:
        auth_token_check = str(exp)

    # print("test_graphql_user_logout")
    # print(f"{token=}")
    # print(f"{user=}")
    # print(f"{response.status_code=}")
    # print(f"{response.json()=}")

    assert response.status_code == 200
    assert response.json()["data"]["user_logout"]["status"] == 204
    assert response.json()["data"]["user_logout"]["errors"] == []
    assert auth_token_check == "User has no auth_token."


def test_graphql_user_delete(login):
    api_client, user, token = login

    body = """
    mutation DeleteUserMutation($token: String!) {
        user_delete(token: $token) {
            status
            errors            
        }
    }
    """
    variables = {
        "token": token,
    }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    # print("test_graphql_user_delete")
    # print(f"{token=}")
    # print(f"{user=}")
    # print(f"{response.status_code=}")
    # print(f"{response.json()=}")

    assert response.status_code == 200
    assert response.json()["data"]["user_delete"]["status"] == 204
    assert response.json()["data"]["user_delete"]["errors"] == []
    assert not User.objects.filter(id=user.id)


def test_graphql_celery(register_user):
    api_client, _, _, _, response = register_user

    body = """
    query GetCelery($task_id: String!) {
        celery(task_id: $task_id) {
            task_status
    		task_result
        }
    }
    """
    variables = {"task_id": response.json()["Task_id"]}

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    # print("test_graphql_celery")
    # print(f"{response.json()=}")

    assert response.status_code == 200
    assert response.json()["data"]["celery"]["task_status"]
    assert response.json()["data"]["celery"]["task_result"]


# # pytest tests/test_regloginout_graphql.py
