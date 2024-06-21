import asyncio
import os.path
from contextlib import suppress
from datetime import datetime, timedelta

from celery.result import AsyncResult
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse, JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from regloginout.models import User
from uploader_1.settings import MAX_TIME_UPLOAD_FILE
from uploader_1.tasks import processing_file

from .models import UploadFile
from .serializers import UploadFileSerializer


@extend_schema(
    request=UploadFileSerializer,
    responses={
        201: inline_serializer(
            name="UploadFile",
            fields={
                "Status": serializers.BooleanField(),
                "File_id": serializers.CharField(),
            },
        ),
    },
)
class FileUploadAPIView(APIView):
    """Upload file"""

    parser_classes = (MultiPartParser, FormParser)
    serializer_classe = UploadFileSerializer

    # Upload file by method POST
    """POST"""

    async def upladed_file_save(self, request):
        file_upload = UploadFile(user=request.data["user"], file=request.FILES["file"])
        await file_upload.asave()
        return file_upload.pk

    async def handle_uploaded_file(self, request):
        task = asyncio.create_task(self.upladed_file_save(request))
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

        if "file" not in request.FILES:
            return JsonResponse(
                {"Status": False, "Error": 'There is no "file" in the request.'},
                status=400,
            )
        request.data["user"] = request.user.pk
        serializer = self.serializer_classe(data=request.data)
        if serializer.is_valid():
            if request.data.get("sync_mode", False):
                file_upload = serializer.save()
                return JsonResponse(
                    {"Status": True, "File_id": file_upload.pk}, status=201
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
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                file = UploadFile.objects.get(pk=file_id)
                user = User.objects.get(pk=file.user)
            except ObjectDoesNotExist:
                return JsonResponse(
                    {"Status": False, "Error": "File not found."}, status=404
                )
        else:
            return JsonResponse(
                {"Status": False, "Error": "file_id is required"}, status=400
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
        if not isinstance(download_file, UploadFile):
            return download_file

        response = FileResponse(
            download_file.file,
            content_type="application/octet-stream",
            as_attachment=True,
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{download_file.file.name}"'
        )

        # response = HttpResponse(download_file.file,
        #                         # content_type="text/csv",
        #                         # headers={"Content-Disposition": f'attachment;
        #                                    filename={file_name}'},
        #                         )

        # response = StreamingHttpResponse(download_file.file,
        #                           content_type="text/csv",
        #                           headers={"Content-Disposition": f'attachment;
        #                                    filename={download_file.file.name}'},
        #                           )

        return response

    """DELETE"""

    def delete(self, request, *args, **kwargs):

        uploaded_file = self.check_user_file_id(request)
        if not isinstance(uploaded_file, UploadFile):
            return uploaded_file

        file_path = uploaded_file.file.path
        file_deleted = uploaded_file.delete()
        if os.path.exists(file_path):
            with suppress(OSError):
                os.remove(file_path)

        return JsonResponse(
            {
                "Status": True,
                "Files_deleted": file_deleted[1]["uploader.UploadFile"],
            },
            status=200,
        )

    """PUT"""

    # Processing file by method PUT
    def put(self, request, *args, **kwargs):

        uploaded_file = self.check_user_file_id(request)
        if not isinstance(uploaded_file, UploadFile):
            return uploaded_file

        file_path = uploaded_file.file.path

        if os.path.exists(file_path):
            # processing by Celery
            async_result = processing_file.delay(file_path)
        else:
            return JsonResponse(
                {"Status": False, "Error": "File not found."}, status=404
            )

        return JsonResponse(
            {
                "Status": True,
                "Task_id": async_result.task_id,
            },
            status=201,
        )


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
