import asyncio
from datetime import datetime, timedelta

import graphene
from asgiref.sync import sync_to_async
from celery.result import AsyncResult
from django.core.exceptions import ObjectDoesNotExist
from graphene_file_upload.scalars import Upload
from graphql_jwt.decorators import login_required
from mongoengine import DoesNotExist, ValidationError

from regloginout.models import User
from regloginout.schema import CeleryType, MutationPayload, UserModelType
from uploader_1.settings import MAX_TIME_UPLOAD_FILE
from uploader_1.tasks import processing_file_mongo
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
    celery = graphene.Field(CeleryType, task_id=graphene.String(required=True))

    def resolve_celery(self, info, task_id):
        try:
            task = AsyncResult(task_id)
            task_status = task.status
            task_result = task.ready()
            return CeleryType(task_status=task_status, task_result=task_result)
        except Exception as err:
            return err


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


class UploadFileMongoMutation(MutationPayload, graphene.Mutation):
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


class DeleteFileMongoMutation(MutationPayload, graphene.Mutation):
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


class ChangeFileMongoMutation(MutationPayload, graphene.Mutation):
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
