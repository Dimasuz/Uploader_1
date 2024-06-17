import asyncio
from datetime import datetime, timedelta

from celery.result import AsyncResult
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse, JsonResponse

from asgiref.sync import sync_to_async
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from mongoengine import DoesNotExist, ValidationError

from .models import UploadFileMongo
from regloginout.models import User
from uploader_1.settings import MAX_TIME_UPLOAD_FILE
from uploader_1.tasks import processing_file_mongo


# @extend_schema(
#     request=UploadFileSerializer,
#     responses={201: inline_serializer(
#             name="UploadFileMongo",
#             fields={"Status": serializers.BooleanField(), "File_id": serializers.CharField(),},
#                     ),
#     },
# )
class FileUploadMongoAPIView(APIView):
    """Upload file"""

    parser_classes = (MultiPartParser, FormParser)

    # Upload file by method POST
    """POST"""

    async def uploaded_file_save(self, request):
        file = request.FILES["file"]
        file_upload = UploadFileMongo(
            user=request.user.pk,
        )
        file_upload.file.put(
            file.file,
            content_type=file.content_type,
            filename=file.name,
        )

        await sync_to_async(file_upload.asave(), thread_sensitive=False)
        return str(file_upload.id)

    async def handle_uploaded_file(self, request):
        task = asyncio.create_task(self.uploaded_file_save(request))
        upload_file = await task
        # ограничим время загрузки файла
        stop_time = datetime.now() + timedelta(minutes=int(MAX_TIME_UPLOAD_FILE))
        while datetime.now() < stop_time:
            if task.done():
                return {"Status": True, "File_id": upload_file}
            else:
                await asyncio.sleep(1)
        task.cancel()
        return {"Status": False, "Error": "UPLOAD_TIMED_OUT"}

    def post(self, request):

        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"}, status=403
            )

        if "file" in request.FILES:
            file = request.FILES["file"]
        else:
            return JsonResponse(
                {"Status": False, "Error": 'There is no "file" in the request.'},
                status=400,
            )

        if request.data.get("sync_mode", False):
            file_upload = UploadFileMongo(
                user=request.user.pk,
            )
            file_upload.file.put(
                file.file,
                content_type=file.content_type,
                filename=file.name,
            )
            file_upload.save()
            return JsonResponse(
                {"Status": True, "File_id": str(file_upload.id)}, status=201
            )
        else:
            # async upload
            uploaded_file = asyncio.run(self.handle_uploaded_file(request))
            if uploaded_file["Status"]:
                return JsonResponse(
                    uploaded_file,
                    status=201,
                )
            else:
                return JsonResponse(uploaded_file, status=400)

    def check_user_file_id(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"}, status=403
            )

        if request.method == "GET":
            file_id = request.query_params.get("file_id", None)
        else:
            file_id = request.data.get("file_id", None)

        if file_id:
            try:
                file = UploadFileMongo.objects.get(pk=file_id)
            except DoesNotExist:
                return JsonResponse(
                    {"Status": False, "Error": "File not found."}, status=404
                )
            except ValidationError:
                return JsonResponse(
                    {
                        "Status": False,
                        "Error": "File_id must be a 12-byte input or a 24-character hex string.",
                    },
                    status=404,
                )

        else:
            return JsonResponse(
                {"Status": False, "Error": "file_id is required"}, status=400
            )

        try:
            user = User.objects.get(pk=file.user)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"Status": False, "Error": "User not found."}, status=404
            )

        if user != request.user:
            return JsonResponse(
                {"Status": False, "Error": "You try to get not yours file."},
                status=403,
            )

        return file

    # Download file by method GET
    """GET"""

    def get(self, request, *args, **kwargs):

        download_file = self.check_user_file_id(request)

        if not isinstance(download_file, UploadFileMongo):
            return download_file

        # file = download_file.file
        response = FileResponse(
            download_file.file,
            filename=download_file.file.filename,
            content_type="application/octet-stream",
            as_attachment=True,
        )
        # response["Content-Disposition"] = (
        #     f'attachment; filename="{download_file.file.filename}"'
        #     # f'attachment; filename="{download_file.file.filename}"'
        # )

        # could be used also
        # response = HttpResponse(download_file.file,
        #                         # content_type="text/csv",
        #                         # headers={"Content-Disposition": f'attachment;
        #                                    filename={file_name}'},
        #                         )
        # or
        # response = StreamingHttpResponse(download_file.file,
        #                           content_type="text/csv",
        #                           headers={"Content-Disposition": f'attachment;
        #                                    filename={download_file.file.name}'},
        #                           )

        return response

    """DELETE"""

    def delete(self, request, *args, **kwargs):

        uploaded_file = self.check_user_file_id(request)

        if not isinstance(uploaded_file, UploadFileMongo):
            return uploaded_file

        uploaded_file.delete()

        return JsonResponse(
            {
                "Status": True,
            },
            status=200,
        )

    """PUT"""

    # Processing file by method PUT
    def put(self, request, *args, **kwargs):

        uploaded_file = self.check_user_file_id(request)

        if isinstance(uploaded_file, UploadFileMongo):

            # processing by Celery
            async_result = processing_file_mongo.delay(str(uploaded_file.id))
            return JsonResponse(
                {
                    "Status": True,
                    "Task_id": async_result.task_id,
                },
                status=201,
            )
        else:
            return uploaded_file


class CeleryStatus(APIView):
    """
    Класс для получения статуса отлооженных задач в Celery
    """

    # Получение сатуса задач Celery методом GET
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        task_id = request.query_params.get("task_id")
        if task_id:
            try:
                task = AsyncResult(task_id)
                task_status = task.status
                task_result = task.ready()
                return JsonResponse(
                    {"Status": task_status, "Result": task_result}, status=200
                )
            except Exception as err:
                return err

        return JsonResponse({"Status": False, "Error": "Task_id required"}, status=400)
