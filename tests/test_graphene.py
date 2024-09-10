import warnings
import pytest

from regloginout.models import User

from .conftest import URL_BASE

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

    print('test_user_details')
    print(f'{user=}')
    print(f'{response.json()=}')

    response_user = response.json()['data']['user']

    assert response_user['id'] == str(user.id)
    assert response_user['email'] == user.email
    assert response_user["first_name"] == user.first_name
    assert response_user["last_name"] == user.last_name


def test_graphql_user_details_change(login):
    api_client, user, token = login

    body = """
    mutation TokenMutation($token: String!, $input: UpdateUserInput!) {
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
    variables = {"token": token,
         "input": {
             "email": "1_new@mail.ru",
             "first_name": "first_name_new",
             "last_name": "last_name_new",
             "password": "password_new",
         }
     }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    user_new = User.objects.filter(id=user.id).get()

    print('test_graphql_user_details_change')
    print(f'{user=}')
    print(f'{user_new=}')
    print(f'{user_new.password=}')
    print(f'{response.json()=}')

    assert response.status_code == 200
    assert response.json()['data']['user_update']['status'] == 202
    assert response.json()['data']['user_update']['errors'] == []
    assert user_new.id == user.id
    assert user_new.first_name == "first_name_new"
    assert user_new.last_name == "last_name_new"
    assert user_new.email == "1_new@mail.ru"
    assert user_new.password == "password_new"


def test_graphql_user_details_change_wrong_password(login):
    api_client, user, token = login

    body = """
    mutation TokenMutation($token: String!, $input: UpdateUserInput!) {
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
    variables = {"token": token,
         "input": {
             "password": "pswrd",
         }
     }

    response = api_client.post(
        url,
        data={"query": body, "variables": variables},
        format="json",
    )

    user_new = User.objects.filter(id=user.id).get()

    print('test_graphql_user_details_change_wrong_password')
    print(f'{user=}')
    print(f'{user_new=}')
    print(f'{user_new.password=}')
    print(f'{response.status_code=}')

    # assert response.status_code == 200
    assert response.json()['errors'][0]['message'] == "String cannot represent value: ['This password is too short. It must contain at least 8 characters.']"
    assert user_new.id == user.id
    assert user_new.password == user.password


# # pytest tests/test_graphene.py
