import asyncio
import os
from datetime import datetime, timedelta

import graphene
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from graphene_file_upload.scalars import Upload
from mongoengine import DoesNotExist, ValidationError

from regloginout.models import User
from regloginout.schema import CeleryType, ObjectPayload, UserModelType
from uploader_1.settings import (
    FILES_DOWNLOAD,
    MAX_TIME_UPLOAD_FILE,
    MEDIA_ROOT,
    MEDIA_URL,
)
from uploader_1.tasks import file_download_delete_mongo, processing_file_mongo
from uploader_mongo.models import UploadFileMongo


def check_user_file_id(token, file_id, *args, **kwargs):
    errors = []

    try:
        user_token = User.objects.get(auth_token=token)
    except ObjectDoesNotExist:
        errors.append("Log in required")
        return {
            "status": 404,
            "errors": errors,
        }

    if not user_token.is_authenticated:
        errors.append("Log in required")
        return {
            "status": 404,
            "errors": errors,
        }

    try:
        file = UploadFileMongo.objects.get(pk=file_id)
    except DoesNotExist:
        errors.append("File not found.")
        return {
            "status": 404,
            "errors": errors,
        }
    except ValidationError:
        errors.append("File_id must be a 12-byte input or a 24-character hex string.")
        return {
            "status": 404,
            "errors": errors,
        }

    try:
        user_file = User.objects.get(pk=file.user)
    except ObjectDoesNotExist:
        errors.append("User not found.")
        return {
            "status": 404,
            "errors": errors,
        }

    if user_token != user_file:
        errors.append("You try to get not yours file.")
        return {
            "status": 404,
            "errors": errors,
        }

    return file


class Query(graphene.ObjectType):
    file_download_mongo = graphene.Field(
        ObjectPayload,
        file_id=graphene.String(required=True),
        token=graphene.String(required=True),
    )

    def resolve_file_download_mongo(self, info, token, file_id):
        download_file = check_user_file_id(token, file_id)

        if not isinstance(download_file, UploadFileMongo):
            return ObjectPayload(
                message=download_file["status"],
                errors=download_file["errors"],
            )

        file_download = os.path.join(MEDIA_ROOT, FILES_DOWNLOAD, file_id)

        with open(file_download, "wb") as f:
            f.write(download_file.file.read())

        message = {"file_url": MEDIA_URL + FILES_DOWNLOAD + file_id}

        file_download_delete_mongo.delay(file_download, datetime.now())

        return ObjectPayload(message=message)


# Mutetions
async def uploaded_file_save(file, user):
    file_upload = UploadFileMongo(
        user=user,
    )
    file_upload.file.put(
        file.file,
        content_type=file.content_type,
        filename=file.name,
    )

    await sync_to_async(file_upload.asave())
    return str(file_upload.id)


async def handle_uploaded_file(file, user):
    task = asyncio.create_task(uploaded_file_save(file, user))
    upload_file = await task
    # ограничим время загрузки файла
    stop_time = datetime.now() + timedelta(minutes=int(MAX_TIME_UPLOAD_FILE))
    while datetime.now() < stop_time:
        if task.done():
            return {"result": True, "file_id": upload_file}
        else:
            await asyncio.sleep(1)
    task.cancel()
    return {"result": False, "error": "UPLOAD_TIMED_OUT"}


class UploadFileMongoMutation(ObjectPayload, graphene.Mutation):
    class Arguments:
        file = Upload(required=True)
        token = graphene.String(required=True)
        sync = graphene.Boolean(required=False)

    user = graphene.Field(UserModelType)

    def mutate(self, info, file, token, sync):
        errors = []
        try:
            user = User.objects.get(auth_token=token)
        except ObjectDoesNotExist:
            errors.append("Log in required")
            return UploadFileMongoMutation(status=404, errors=errors)

        if not info.context.user.is_authenticated:
            errors.append("not_authenticated")
            return UploadFileMongoMutation(status=404, errors=errors)

        # sync upload
        if sync:
            file_upload = UploadFileMongo(
                user=user.pk,
            )
            file_upload.file.put(
                file,
                content_type=file.content_type,
                filename=file.name,
            )
            file_upload.save()
            message = {"file_id": str(file_upload.pk)}
            return UploadFileMongoMutation(message=message, status=201)

        # async upload
        uploaded_file = asyncio.run(handle_uploaded_file(file, user.pk))
        if uploaded_file["result"]:
            message = {"file_id": uploaded_file["file_id"]}
            return UploadFileMongoMutation(message=message, status=201)
        else:
            errors.append(uploaded_file["errors"])
            return UploadFileMongoMutation(errors=errors, status=404)


class DeleteFileMongoMutation(ObjectPayload, graphene.Mutation):
    class Arguments:
        file_id = graphene.String(required=True)
        token = graphene.String(required=True)

    user = graphene.Field(UserModelType)

    def mutate(self, info, token, file_id):
        errors = []

        uploaded_file = check_user_file_id(token, file_id)

        if not isinstance(uploaded_file, UploadFileMongo):
            errors.append(uploaded_file["errors"])
            return DeleteFileMongoMutation(
                errors=errors, status=uploaded_file["status"]
            )

        uploaded_file.delete()

        message = f"your file with {file_id} was deleted"
        return DeleteFileMongoMutation(message=message, status=200)


class ChangeFileMongoMutation(ObjectPayload, graphene.Mutation):
    class Arguments:
        file_id = graphene.String(required=True)
        token = graphene.String(required=True)

    user = graphene.Field(UserModelType)

    def mutate(self, info, token, file_id):
        errors = []

        uploaded_file = check_user_file_id(token, file_id)

        if not isinstance(uploaded_file, UploadFileMongo):
            errors.append(uploaded_file["errors"])
            return ChangeFileMongoMutation(
                errors=errors, status=uploaded_file["status"]
            )

        # processing by Celery
        async_result = processing_file_mongo.delay(str(uploaded_file.id))

        message = {"task_id": async_result.task_id}
        return ChangeFileMongoMutation(message=message, status=202)


class Mutation(graphene.ObjectType):
    file_mongo_upload = UploadFileMongoMutation.Field()
    file_mongo_delete = DeleteFileMongoMutation.Field()
    file_mongo_change = ChangeFileMongoMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)
