import warnings
import json
import pytest

from graphene_django.utils.testing import graphql_query
from uritemplate import variables

from regloginout.models import User
from uploader_1.schema import schema
from .conftest import URL_BASE

warnings.filterwarnings(action="ignore")

pytestmark = pytest.mark.django_db

url = URL_BASE + "graphql/"

@pytest.fixture
def client_query(client):
    def func(*args, **kwargs):
        return graphql_query(*args, **kwargs, client=client)

    return func

def test_user_details(client_query, login):

    _, user, token = login
    print(user.is_authenticated)
    print("users")
    body = """
        query GetUsers{ 
            users {
                id
                email
                first_name
                last_name
            }
        }
    """
    response_users = client_query(body, graphql_url=url)

    print(response_users.content)
    print(user.auth_token)
    print("user")

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
    print(variables)
    # запрос почему-то не проходит через декоратор @login_required в shema.Query
    response = client_query(body, variables=variables, graphql_url=url)

    # content = json.loads(response.content)
    print(response.content)
    assert False


    # response = api_client.get(
    #     url,
    #     # variables=variables,
    #     data={"query": body},
    # )



# def test_graphql_user_details_get(login):
#     api_client, user, token = login
# # как передать аргумент?
#     body = f"""
#     query($token_1: String! = {token}) {{
#         user(token: $token_1) {{
#             id
#             email
#             first_name
#             last_name
#         }}
#     }}
#     """
#
#     # variables = {
#     #     "token_1": token,
#     # }
#
#     response = api_client.get(
#         url,
#         # variables=variables,
#         data={"query": body},
#     )

    # # print(response.content)
    # print(response.json())
    # # response_user = response.json()["data"]["users"][0]
    # # print(response_user)
    #
    # assert response.status_code == 200
    # # assert response_user["id"] == str(user.id)
    # # assert response_user["first_name"] == user.first_name
    # # assert response_user["last_name"] == user.last_name
    # # assert response_user["email"] == user.email

#
# def test_graphql_user_details_change(login):
#     api_client, user, token = login
#
#     first_name = "new_" + user.first_name
#
#     body = """
#     {
#         user_update {
#             "id": str(user.id)
#             "first_name": fist_name
#         }
#     }
#     """
#
#     # headers = {
#     #     "Authorization": f"Token {token}",
#     # }
#     response = api_client.post(
#         url,
#         # headers=headers,
#         data={"query": body},
#     )
#
#     print(response.content)
#     print(response.json())
#     response_user = response.json()["data"]["users"][0]
#     print(response_user)
#
#     assert response.status_code == 200
#     assert response_user["id"] == str(user.id)
#     assert response_user["first_name"] == user.first_name
#     assert response_user["last_name"] == user.last_name
#     assert response_user["email"] == user.email
#
#     # assert False
#
#
# # pytest tests/test_graphene.py
