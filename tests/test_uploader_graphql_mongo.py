import os
import warnings

import pytest
from graphene_file_upload.django.testing import file_graphql_query
from mongoengine import DoesNotExist

from uploader.models import UploadFile
from uploader_mongo.models import UploadFileMongo

from .conftest import URL_BASE

warnings.filterwarnings(action="ignore")

pytestmark = pytest.mark.django_db

db = "mongo"
url_view = f"file/{db}/graphql/"
url = URL_BASE + url_view


# upload
@pytest.mark.url(db)
def test_upload(file_upload):

    token, response = file_upload
    file_id = response.json()["data"][f"file_mongo_upload"]["message"]["file_id"]

    uploaded_file = UploadFileMongo.objects.all().filter(pk=file_id)[0]

    assert response.status_code == 200
    assert response.json()["data"]["file_mongo_upload"]["status"] == 201
    assert uploaded_file.file

    uploaded_file.delete()


@pytest.mark.parametrize("tmp_file", ["txt"], indirect=True)
def test_upload_wrong_token(login, tmp_file):
    api_client, _, token = login

    body = """
    mutation testUploadMutation($file: Upload!, $token: String!,  $sync: Boolean) {
        file_mongo_upload(file: $file, token: $token, sync: $sync) {
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
    assert response.json()["data"]["file_mongo_upload"]["status"] == 404


# delete
@pytest.mark.url(db)
def test_delete(api_client, file_upload):
    # prepare file
    token, response = file_upload
    file_id = response.json()["data"][f"file_mongo_upload"]["message"]["file_id"]

    # delete
    body = """
        mutation testUploadMutation($file_id: String!, $token: String!) {
            file_mongo_delete(file_id: $file_id, token: $token) {
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
        file = UploadFileMongo.objects.get(pk=file_id)
    except DoesNotExist:
        file = False

    assert response.status_code == 200
    assert response.json()["data"]["file_mongo_delete"]["status"] == 200
    assert not file


# file/mongo/ PUT
@pytest.mark.url(db)
def test_processing_file(file_upload, api_client):
    # prepare file
    token, response = file_upload
    file_id = response.json()["data"][f"file_mongo_upload"]["message"]["file_id"]

    # change
    body = """
           mutation testUploadMutation($file_id: String!, $token: String!) {
               file_mongo_change(file_id: $file_id, token: $token) {
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

    assert response.status_code == 200
    assert response.json()["data"]["file_mongo_change"]["status"] == 202
    assert response.json()["data"]["file_mongo_change"]["message"]["task_id"]

    uploaded_file = UploadFileMongo.objects.get(pk=file_id)
    uploaded_file.delete()


# pytest tests/test_uploader_graphql_mongo.py
