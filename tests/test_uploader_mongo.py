import warnings

import pytest
from mongoengine import DoesNotExist

from uploader_mongo.models import UploadFileMongo

from .conftest import URL_BASE

warnings.filterwarnings(action="ignore")

pytestmark = pytest.mark.django_db

url_view = "file/mongo/"
url = URL_BASE + url_view


# upload/mongo/ POST
@pytest.mark.parametrize("tmp_file", ["txt", "exe"], indirect=True)
def test_upload(login, tmp_file):
    """POST"""
    api_client, user, token = login
    headers = {
        "Authorization": f"Token {token}",
    }
    with open(tmp_file, "rb") as file:
        data = {
            "file": file,
            "sync_mode": True,
        }
        response = api_client.post(
            url,
            headers=headers,
            data=data,
        )
        file.seek(0)
        file_bytes = file.read()

    file_id = response.json()["File_id"]
    uploaded_file = UploadFileMongo.objects.get(pk=file_id)
    uploaded_file_bytes = uploaded_file.file.read()
    uploaded_file.delete()

    assert response.status_code == 201
    assert response.json()["Status"] == True
    assert response.json()["File_id"] == str(uploaded_file.id)
    assert uploaded_file_bytes == file_bytes


# file/mongo/ POST - no authorization user
@pytest.mark.parametrize("tmp_file", ["txt"], indirect=True)
def test_upload_not_authorization(login, tmp_file):
    api_client, user, token = login
    url_view = "user/logout/"
    url = URL_BASE + url_view
    headers = {"Authorization": f"Token {token}"}
    api_client.post(
        url,
        headers=headers,
    )

    """POST"""
    with open(tmp_file) as file:
        data = {
            "file": file,
            "sync_mode": True,
        }
        response = api_client.post(
            url,
            headers=headers,
            data=data,
        )

    assert response.status_code == 401


# file/mongo/ GET
@pytest.mark.parametrize("tmp_file", ["txt"], indirect=True)
def test_download(login, tmp_file):
    # prepare file by POST
    api_client, user, token = login
    headers = {
        "Authorization": f"Token {token}",
    }
    with open(tmp_file, "rb") as file_upload:
        data = {
            "file": file_upload,
            "sync_mode": True,
        }
        response = api_client.post(
            url,
            headers=headers,
            data=data,
        )
        file_id = response.json()["File_id"]
        file_upload.seek(0)
        file_upload_bytes = file_upload.read()

    """GET"""
    data = {
        "file_id": file_id,
    }
    response = api_client.get(
        url,
        headers=headers,
        data=data,
    )
    # if now delete file in mongo so response.getvalue() not work
    response_bytes = response.getvalue()

    download_file = UploadFileMongo.objects.get(pk=file_id)
    download_file.delete()

    assert response.status_code == 200
    assert file_upload_bytes == response_bytes


# file/mongo/ GET - wrong user
@pytest.mark.parametrize("tmp_file", ["txt"], indirect=True)
def test_download_wrong_user(login, tmp_file, create_token):
    # prepare file
    api_client, user, token = login
    headers = {
        "Authorization": f"Token {token}",
    }
    with open(tmp_file, "rb") as file_upload:
        data = {
            "file": file_upload,
            "sync_mode": True,
        }
        response = api_client.post(
            url,
            headers=headers,
            data=data,
        )
        file_id = response.json()["File_id"]

    """GET"""
    token_wrong_user = create_token
    headers = {
        "Authorization": f"Token {token_wrong_user}",
    }
    data = {
        "file_id": file_id,
    }
    response = api_client.get(
        url,
        headers=headers,
        data=data,
    )

    upload_file = UploadFileMongo.objects.get(pk=file_id)
    upload_file.delete()

    assert response.status_code == 403
    assert not response.json()["Status"]
    assert response.json()["Error"] == "You try to get not yours file."


# file/mongo/ PUT
@pytest.mark.parametrize("tmp_file", ["txt"], indirect=True)
def test_processing_file(login, tmp_file):
    # prepare file
    api_client, user, token = login
    headers = {
        "Authorization": f"Token {token}",
    }
    with open(tmp_file, "rb") as file_upload:
        data = {"file": file_upload, "sync_mode": True}
        response = api_client.post(
            url,
            headers=headers,
            data=data,
        )
        file_id = response.json()["File_id"]

    """PUT"""
    data = {
        "file_id": file_id,
    }
    response = api_client.put(
        url,
        headers=headers,
        data=data,
    )

    upload_file = UploadFileMongo.objects.get(pk=file_id)
    upload_file.delete()

    assert response.status_code == 201
    assert response.json()["Status"]
    assert response.json()["Task_id"]


# file/mongo/ DELETE
@pytest.mark.parametrize("tmp_file", ["txt"], indirect=True)
def test_delete_file(login, tmp_file):
    # prepare file
    api_client, user, token = login
    headers = {
        "Authorization": f"Token {token}",
    }
    with open(tmp_file, "rb") as file_upload:
        data = {"file": file_upload, "sync_mode": True}
        response = api_client.post(
            url,
            headers=headers,
            data=data,
        )
        file_id = response.json()["File_id"]

    """GET"""
    data = {
        "file_id": file_id,
    }
    response = api_client.get(
        url,
        headers=headers,
        data=data,
    )
    response_get_status_code = response.status_code

    """DELETE"""
    response = api_client.delete(
        url,
        headers=headers,
        data=data,
    )

    # check file exist in mongo
    try:
        uploader_file = UploadFileMongo.objects.get(pk=file_id)
    except DoesNotExist as ex:
        uploader_file = str(ex)
    else:
        uploader_file.delete()

    assert response_get_status_code == 200
    assert response.status_code == 200
    assert response.json()["Status"]
    assert uploader_file == "UploadFileMongo matching query does not exist."


# pytest --ignore=tests/test_regloginout.py
# pytest tests/test_uploader_mongo.py
