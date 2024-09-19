import os.path
import time
import uuid
from datetime import datetime
from pprint import pprint
from tempfile import NamedTemporaryFile

import requests

# TOKEN = "5a9da05f4a2443a4527cc5822a085552ddce0e52"
TOKEN = "0e8088707c3aa81e7918908aa01cb24ae7f1af9b"

# url_adress = "0:0:0:0"
url_adress = "127.0.0.1"
# url_adress = "79.174.82.110"
url_port = "8000"
api_version = "api/v1"
url_base = f"http://{url_adress}:{url_port}/{api_version}/"

# url_base = 'http://0.0.0.0:8000/api/v1/auth0/'

# add_url_file_view = ""
add_url_file_view = "mongo/"


time_now = str(datetime.now())[11:20]


def base_request(
    url_view="", method="get", headers=None, data=None, params=None, files=None
):
    url = url_base + url_view
    print()
    print(method, url_view)
    if method == "get":
        response = requests.get(
            url, headers=headers, params=params, timeout=60, verify=False
        )
    if method == "post":
        response = requests.post(url, headers=headers, data=data, files=files)
    if method == "put":
        response = requests.put(
            url,
            headers=headers,
            data=data,
        )
    if method == "delete":
        response = requests.delete(
            url,
            headers=headers,
            data=data,
        )
    print(response.status_code)
    try:
        response.json()
    except BaseException as e:
        print("JSON ERROR:")
        pprint(e)
        print("RESPONSE TEXT:")
        pprint(response.text)
        return response, None
    else:
        print("JSON:")
        pprint(response.json())
        return response, True


def get_headers(token=None, content_type=None):
    authorization = f"Token {token}"
    if content_type:
        headers = {
            "Content-Type": content_type,
            "Authorization": authorization,
        }
    else:
        headers = {
            "Authorization": authorization,
        }
    return headers


# registration-----------
def user_register(email=None, password=None):
    url_view = "user/register/"
    if not email:
        email = int(input("Введите email: "))
    if not password:
        password = int(input("Введите пароль: "))
    data = {
        "first_name": f"first_name_{email}",
        "last_name": f"last_name_{email}",
        "email": email,
        "password": f"Password_{email}",
    }
    response, json_status = base_request(url_view=url_view, method="post", data=data)
    if response.status_code == 200 and json_status:
        if response.json()["Status"] == False:
            task_id = None
            token_confirm = None
        else:
            task_id = response.json()["Task_id"]
            token_confirm = response.json()["Token"]
    else:
        task_id = None
        token_confirm = None
    return task_id, token_confirm


# confirm email----------------------
def confirm(email=None, token=None):
    url_view = "user/register/confirm/"
    if not email:
        email = input("Введите email пользователя: ")
    if not token:
        token = input("Введите token: ")
    data = {
        "email": email,
        "token": token,
    }
    response, json_status = base_request(url_view=url_view, method="post", data=data)
    return response


# login user -----------------------
def login(email=None, password=None):
    url_view = "user/login/"
    if not email:
        email = input("Введите email пользователя = ")
    if not password:
        password = f"Password_{email}"
    data = {
        "email": email,
        "password": password,
    }
    response, json_status = base_request(url_view=url_view, method="post", data=data)
    if response.status_code == 200 and json_status:
        if response.json()["Status"] == False:
            token_login = None
        else:
            token_login = response.json()["Token"]
    else:
        token_login = None
    return token_login


# user/details/ -----------------------------
def details_get(token=None):
    url_view = "user/details/"
    if not token:
        token = input("Введите token пользователя = ")
    headers = get_headers(token=token)
    response, json_status = base_request(
        url_view=url_view,
        method="get",
        headers=headers,
    )
    return response


def details_post(token=None, **kwargs):
    url_view = "user/details/"
    if not token:
        token = input("Введите token пользователя = ")
    headers = get_headers(token=token)
    response, json_status = base_request(
        url_view=url_view, method="post", data=kwargs, headers=headers
    )
    return response


# logout user-----------------------
def logout(token=None):
    url_view = "user/logout/"
    if not token:
        token = input("Введите token пользователя = ")
    headers = get_headers(token=token)
    response, json_status = base_request(
        url_view=url_view,
        method="post",
        headers=headers,
    )
    return response


# delete user-----------------------
def delete(token=None):
    url_view = "user/delete/"
    if not token:
        token = input("Введите token пользователя = ")
    headers = get_headers(token=token)
    response, json_status = base_request(
        url_view=url_view,
        method="delete",
        headers=headers,
    )
    return response


# /user/password_reset/ ----------------------------
def password_reset(email=None):
    url_view = "user/password_reset/"
    if not email:
        email = input("Введите email пользователя = ")
    data = {
        "email": email,
    }
    response, json_status = base_request(url_view=url_view, method="post", data=data)


# /user/password_reset/confirm/ ----------------------------
def password_reset_confirm(token=None, password=None):
    url_view = "user/password_reset/confirm/"
    if not token:
        token = input("Введите token = ")
    if not password:
        password = input("Введите password = ")
    data = {
        "token": token,
        "password": password,
    }
    response, json_status = base_request(url_view=url_view, method="post", data=data)


# ------------------------------------
# UPLOAD FILE


# file/upload/
def upload(token=None, data=None):
    url_view = f"file/{add_url_file_view}"
    if not token:
        token = input("Введите token пользователя = ")
    headers = get_headers(token=token)
    uploaded_file_time = time_now
    uploaded_file_name = f"test_{uploaded_file_time[:19]}_uploaded_file.txt"
    with NamedTemporaryFile(
        "w+b", prefix="uploaded_file_name", suffix="uploaded_file_ext"
    ) as f:
        f.write(f"<begin - client_api_test - {uploaded_file_time} - end>".encode())
        f.seek(0)
        files = {"file": (uploaded_file_name, f, "text/x-spam")}
        try:
            response, json_status = base_request(
                url_view=url_view,
                method="post",
                headers=headers,
                files=files,
                data=data,
            )
            return response
        except Exception as e:
            return e


# file/download/
def download(
    token=None,
    file_id=None,
):
    url_view = f"file/{add_url_file_view}"
    if not token:
        token = input("Введите token пользователя = ")
    if not file_id:
        file_id = input("Введите file_id = ")
    headers = get_headers(token=token)
    params = {
        "file_id": file_id,
    }
    response, json_status = base_request(
        url_view=url_view,
        method="get",
        headers=headers,
        params=params,
    )
    if response.status_code == 200:

        filename = response.headers.get("Content-Disposition")
        start_index = filename.find("filename=") + 10
        filename = filename[start_index:-1]

        # downloaded_file_name = f"test_{response.text[9:28]}_download_file.txt"
        downloaded_file_time = time_now
        downloaded_file_name = (
            f"test_{filename}_download_time_{downloaded_file_time[:19]}.txt"
        )
        CURR_DIR = os.path.dirname(os.path.realpath(__file__))
        downloaded_file = os.path.join(CURR_DIR, downloaded_file_name)

        with open(downloaded_file, "wb+") as f:
            f.write(response.content)
            # f.write(filename.encode('utf-8'))
        print("File downloaded:")
        with open(downloaded_file, "rb") as f:
            print(f.read())
        # time.sleep(5)
        if input("Удалить скаченный файл? Y: "):
            os.remove(downloaded_file)
            print("File deleted")
    else:
        return response


# file/processing/
def processing(token=None, file_id=None):
    url_view = f"file/{add_url_file_view}"
    if not token:
        token = input("Введите token пользователя = ")
    if not file_id:
        file_id = input("Введите file_id = ")
    headers = get_headers(token=token)
    data = {
        "file_id": file_id,
    }
    response, json_status = base_request(
        url_view=url_view,
        method="put",
        headers=headers,
        data=data,
    )

    return response


# file/delete/
def file_delete(token=None, file_id=None):
    url_view = f"file/{add_url_file_view}"
    if not token:
        token = input("Введите token пользователя = ")
    if not file_id:
        file_id = input("Введите file_id = ")
    headers = get_headers(token=token)
    data = {
        "file_id": file_id,
    }
    response, json_status = base_request(
        url_view=url_view,
        method="delete",
        headers=headers,
        data=data,
    )

    return response


# celery tesk status-----------------------
def celery_status(task_id=None):
    url_view = "celery_status/"
    if not task_id:
        task_id = input("Введите task_id = ")
    if task_id:
        celery_status = "-"
        while celery_status != "SUCCESS":
            #  or celery_status != 'FAILURE'
            response, json_status = base_request(
                url_view=url_view, method="get", params={"Task_id": task_id}
            )
            celery_status = response.json()["Status"]
            file = response.json()["Result"]
            time.sleep(1)
            # if not celery_status == "SUCCESS":
            #     if input("Stop? y/n") == "y":
            #         return celery_status
        return celery_status, file


def api_test(token=None, url_store="disk"):
    a = input("1 - операции с пользователями, \n2 - операции с файлами\n: ")
    if a == "1":
        a = input(
            "1 - user registration,\n2 - email confirm,\n3 - login,\n4 - logout,\n"
            "5 - delete user,\n6 - user deteils get,\n7 - user deteils change,\n"
            "8 - task get,\n11 - reset password\n: "
        )
        # регистраиця нового пользователя
        if a == "0":
            email = str(uuid.uuid4())
            email = email + "@mail.ru"
            password = f"Password_{email}"
            _, token = user_register(email=email, password=password)
            confirm(email=email, token=token)
            token = login(email=email)
            logout(token)
            token = login(email=email)
            delete(token)

        elif a == "1":
            email = input("Введите {адрес} @mail.ru: ")
            email = email + "@mail.ru"
            password = f"Password_{email}"
            response = user_register(email=email, password=password)
            celery = input("Запросить очередь celery? ")
            if celery:
                celery_status(response["Task_id"])
            else:
                return
        # подтверждение почты нового пользователя
        elif a == "2":
            email = input("Введите {адрес} @mail.ru: ")
            email = email + "@mail.ru"
            confirm(email=email)
        # вход в систему
        elif a == "3":
            email = input("Введите {адрес} @mail.ru: ")
            email = email + "@mail.ru"
            if not input("Стандартный пароль? Y(enter)/N"):
                login(email=email)
            else:
                password = input("Введите пароль: ")
                login(email=email, password=password)
        # выход из системы
        elif a == "4":
            logout(token=token)
        # удаление пользователя
        elif a == "5":
            delete(token=token)

        # запрос данных пользователя
        elif a == "6":
            # email = input("Введите {адрес} @mail.ru: ")
            # email = email + "@mail.ru"
            # token = login(email=email)
            details_get(token)
        # изменение данных пользователя
        elif a == "7":
            email = input("Введите {адрес} @mail.ru: ")
            email = email + "@mail.ru"
            # print("Входим в систему.")
            # token = login(email=email)
            # получаем текущие данные пользователя
            data_old = details_get(token).json()
            print(data_old)
            print(f'Меняем данные пользователя добавив "new_{time_now}_".')
            password_new = f"new_Password_{email}"
            data = {
                "first_name": f"new_{time_now}_{data_old['first_name']}",
                "last_name": f"new_{time_now}_{data_old['last_name']}",
                # "password": password_new,
            }
            details_post(token=token, **data)
            details_get(token=token)
            print("Выходим из системы")
            logout()
            if input("Меняем данные пользователя обратно? Y "):
                print("Входим в систему.")
                token = login(email=email, password=password_new)
                data = data_old + {"password": f"Password_{email}"}
                details_post(token, **data)
                details_get(token)
                print("Выходим из системы")
                logout(token)
        # запрос таски
        elif a == "8":
            celery_status()
        elif a == "11":
            password_reset()
            password_reset_confirm()
    elif a == "2":
        a = input(
            "0 - file upload, processing, get task, download and all delete,\n"
            "1 - file upload,\n2 - file processing,\n3 - file download,\n4 - file delete,\n: "
        )

        if a == "0":
            # email = input("Введите {адрес} @mail.ru: ")
            # email = str(uuid.uuid4()) + "@mail.ru"
            # print(f'email пользователя - {email}')
            # password = f"Password_{email}"
            # _, token = user_register(email=email, password=password)
            # confirm(email=email, token=token)
            # token = login(email=email)
            # print(f"{token=}")
            print("Загрузка файла.")
            data = {"sync_mode": False}
            file_id = upload(token=token, data=data).json()["File_id"]
            print(f"Загружен файл с {file_id=}")
            print()
            # print(f"Скачивание файла с id - {file_id}.")
            # download(
            #     token=token,
            #     file_id=file_id,
            # )
            print()
            print(f"Обработка файла с id - {file_id}.")
            task_id = processing(token=token, file_id=file_id)
            print(task_id.json())
            task_id = task_id.json()["Task_id"]
            print(f"Запрос таски - {task_id}.")
            print(celery_status(task_id=task_id))
            print()
            time.sleep(11)
            print(f"Запрос таски - {task_id}.")
            print(celery_status(task_id=task_id))
            print()
            print(f"Скачивание файла с id - {file_id}.")
            download(
                token=token,
                file_id=file_id,
            )
            print()
            # input("Удаление файла и пользователя.")
            print(f"Удаление файла с id - {file_id}.")
            file_delete(token=token, file_id=file_id)
            # print(f"Удаление из базы пользователя.")
            # delete(token=token)
        elif a == "1":
            print(f"Загрузка файла.")
            data = {"sync_mode": False}
            upload(token=token, data=data)
            # upload(token=token)
        elif a == "2":
            print(f"Обработка файла.")
            file_id = input("file_id = ")
            responce = processing(token=token, file_id=file_id)
            if input("Get celery task result? y"):
                celery_status(responce.json()["Task_id"])
        elif a == "3":
            print(f"Скачивание файла.")
            download(
                token=token,
            )
        elif a == "4":
            print(f"Удаление файла.")
            file_id = input("file_id = ")
            file_delete(token=token, file_id=file_id)

    else:
        pass
    return None


if __name__ == "__main__":
    token = TOKEN

    # url_list = ['disk', 'db']
    # url_store = url_list[1]
    api_test(token=token)

    # curl --location --request POST 'http://localhost:8000/api/upload-file/' \
    # --form 'file=@"/path/to/yourfile.pdf"'

# from django.conf import settings
# from django.core.cache import cache
# cache_keys = cache._cache.get_cient().keys(f"*{settings.CACHES['default']['KEY_PREFIX']}*")
