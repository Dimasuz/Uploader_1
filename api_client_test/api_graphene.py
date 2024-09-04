import os.path
import time
import uuid
from datetime import datetime
from pprint import pprint
from tempfile import NamedTemporaryFile

import django.test
import requests

from tests.conftest import api_client

# url_adress = "0:0:0:0"
url_adress = "127.0.0.1"
# url_adress = "79.174.82.110"
url_port = "8000"
api_version = "api/v1"
url = f"http://{url_adress}:{url_port}/{api_version}/graphql/"


def users_details_get():

    body = """
    query {
        users {
            id
            first_name
            last_name
            email                   
        }
    }
    """

    response = requests.get(url=url, json={"query": body})
    print("response status code: ", response.status_code)
    if response.status_code == 200:
        print("response : ", response.content)


def user_details_update():

    body = """
    mutation {
        user_update (
        "id": 1
        "fist_name": "new_1"
        )
        users {
            id
            firstName
            lastName
            email
            password       
        }
    }
    """

    response = requests.post(url=url, json={"query": body})
    print("response status code: ", response.status_code)
    if response.status_code == 200:
        print("response : ", response.content)


if __name__ == "__main__":
    users_details_get()

    # user_details_update()
