import os
import warnings

import pytest
from django.core.exceptions import ObjectDoesNotExist
from graphene_file_upload.django.testing import file_graphql_query

from uploader.models import UploadFile

from .conftest import URL_BASE

warnings.filterwarnings(action="ignore")

pytestmark = pytest.mark.django_db

db = "db"
url_view = f"file/{db}/graphql/"
url = URL_BASE + url_view


# upload
@pytest.mark.url(db)
def test_upload(file_upload):
    token, response = file_upload
    print(response.json())
    file_id = response.json()["data"][f"file_db_upload"]["message"]["file_id"]

    uploaded_file = UploadFile.objects.all().filter(pk=file_id)[0]
    file_path = uploaded_file.file.path

    assert response.status_code == 200
    assert response.json()["data"]["file_db_upload"]["status"] == 201
    assert type(response.json()["data"]["file_db_upload"]["message"]["file_id"]) == int
    assert uploaded_file.file

    # clear disk
    os.remove(file_path)


# upload wrong user
@pytest.mark.parametrize("tmp_file", ["txt"], indirect=True)
def test_upload_wrong_user(login, tmp_file):
    api_client, _, token = login

    body = """
    mutation testUploadMutation($file: Upload!, $token: String!, $sync: Boolean) {
        file_db_upload(file: $file, token: $token, sync: $sync) {
            errors
            message
            status
        }
    }
    """

    with open(tmp_file, "rb") as file:
        response = file_graphql_query(
            body,
            op_name="testUploadMutation",
            files={"file": file},
            variables={"token": token + "1", "sync": True},
            client=api_client,
            graphql_url=url,
        )

    assert response.status_code == 200
    assert response.json()["data"]["file_db_upload"]["status"] == 404


# delete
@pytest.mark.url(db)
def test_delete(api_client, file_upload):
    # prepare file
    token, response = file_upload
    file_id = response.json()["data"][f"file_db_upload"]["message"]["file_id"]

    # delete
    body = """
        mutation testUploadMutation($file_id: Int!, $token: String!) {
            file_db_delete(file_id: $file_id, token: $token) {
                errors
                message
                status
            }
        }
        """

    response = api_client.post(
        url,
        data={"query": body, "variables": {"token": token, "file_id": file_id}},
        format="json",
    )

    # check delete
    try:
        file = UploadFile.objects.get(pk=file_id)
    except ObjectDoesNotExist:
        file = False

    assert response.status_code == 200
    assert response.json()["data"]["file_db_delete"]["status"] == 200
    assert not file


# file/mongo/ PUT
@pytest.mark.url(db)
def test_processing_file(file_upload, api_client):
    # prepare file
    token, response = file_upload
    file_id = response.json()["data"][f"file_db_upload"]["message"]["file_id"]

    # change
    body = """
           mutation testUploadMutation($file_id: Int!, $token: String!) {
               file_db_change(file_id: $file_id, token: $token) {
                   errors
                   message
                   status
               }
           }
           """

    response = api_client.post(
        url,
        data={"query": body, "variables": {"token": token, "file_id": file_id}},
        format="json",
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json()["data"]["file_db_change"]["status"] == 202
    assert response.json()["data"]["file_db_change"]["message"]["task_id"]

    uploaded_file = UploadFile.objects.get(pk=file_id)
    uploaded_file.delete()


# pytest tests/test_uploader_graphql.py
