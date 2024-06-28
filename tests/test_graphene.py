import warnings

import pytest

from .conftest import URL_BASE

warnings.filterwarnings(action="ignore")

pytestmark = pytest.mark.django_db

url = URL_BASE + 'graphql/'

def test_graphql_user_details_get(login):
    api_client, user, token = login

    body = '''
    {
        users {
            id
            first_name
            last_name
            email
            password       
        }
    }
    '''

    # headers = {
    #     "Authorization": f"Token {token}",
    # }
    response = api_client.get(
        url,
        # headers=headers,
        data={"query": body}
    )

    # print(response.content)
    # print(response.json())
    response_user = response.json()["data"]["users"][0]
    # print(response_user)
    
    assert response.status_code == 200
    assert response_user['id'] == str(user.id)
    assert response_user["first_name"] == user.first_name
    assert response_user["last_name"] == user.last_name
    assert response_user["email"] == user.email

    # assert False


# pytest tests/test_graphene.py
