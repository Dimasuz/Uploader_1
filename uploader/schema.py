import asyncio
import os
from contextlib import suppress
from datetime import datetime, timedelta

import graphene
from celery.result import AsyncResult
from django.core.exceptions import ObjectDoesNotExist
from graphene_file_upload.scalars import Upload
from graphql_jwt.decorators import login_required

from regloginout.models import User
from regloginout.schema import CeleryType, MutationPayload, UserModelType
from uploader.models import UploadFile
from uploader_1.settings import MAX_TIME_UPLOAD_FILE
from uploader_1.tasks import processing_file


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
        file = UploadFile.objects.get(pk=file_id)
    except ObjectDoesNotExist:
        errors.append("File not found.")
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
    file_upload = UploadFile(user=user, file=file)
    await file_upload.asave()
    return file_upload.pk


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


class UploadFileMutation(MutationPayload, graphene.Mutation):
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
            return UploadFileMutation(status=404, errors=errors)

        if not info.context.user.is_authenticated:
            errors.append("not_authenticated")
            return UploadFileMutation(status=404, errors=errors)

        if sync:
            file_upload = UploadFile(user=user.id, file=file)
            file_upload.save()
            message = {"file_id": file_upload.pk}
            return UploadFileMutation(message=message, status=201)

        # async upload
        uploaded_file = asyncio.run(handle_uploaded_file(file, user.pk))
        if uploaded_file["result"]:
            message = {"file_id": uploaded_file["file_id"]}
            return UploadFileMutation(message=message, status=201)
        else:
            errors.append(uploaded_file["errors"])
            return UploadFileMutation(errors=errors, status=404)


class DeleteFileMutation(MutationPayload, graphene.Mutation):
    class Arguments:
        file_id = graphene.Int(required=True)
        token = graphene.String(required=True)

    user = graphene.Field(UserModelType)

    def mutate(self, info, token, file_id):
        errors = []

        uploaded_file = check_user_file_id(token, file_id)

        if not isinstance(uploaded_file, UploadFile):
            errors.append(uploaded_file["errors"])
            return DeleteFileMutation(errors=errors, status=uploaded_file["status"])

        file_path = uploaded_file.file.path
        uploaded_file.delete()
        if os.path.exists(file_path):
            with suppress(OSError):
                os.remove(file_path)

        message = f"your file with {file_id} was deleted"
        return DeleteFileMutation(message=message, status=200)


class ChangeFileMutation(MutationPayload, graphene.Mutation):
    class Arguments:
        file_id = graphene.Int(required=True)
        token = graphene.String(required=True)

    user = graphene.Field(UserModelType)

    def mutate(self, info, token, file_id):
        errors = []

        uploaded_file = check_user_file_id(token, file_id)

        if not isinstance(uploaded_file, UploadFile):
            errors.append(uploaded_file["errors"])
            return ChangeFileMutation(errors=errors, status=uploaded_file["status"])

        # processing by Celery
        file_path = uploaded_file.file.path

        if os.path.exists(file_path):
            # processing by Celery
            async_result = processing_file.delay(file_path)

        message = {"task_id": async_result.task_id}
        return ChangeFileMutation(message=message, status=202)


class Mutation(graphene.ObjectType):
    file_db_upload = UploadFileMutation.Field()
    file_db_delete = DeleteFileMutation.Field()
    file_db_change = ChangeFileMutation.Field()


schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)
