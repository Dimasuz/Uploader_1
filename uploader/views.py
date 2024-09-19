import asyncio
import os.path
from contextlib import suppress
from datetime import datetime, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse, JsonResponse
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from regloginout.models import User
from uploader_1.settings import MAX_TIME_UPLOAD_FILE
from uploader_1.tasks import processing_file

from .models import UploadFile
from .serializers import UploadFileSerializer


@extend_schema(
    tags=["file/"],
)
class FileUploadAPIView(APIView):
    """Upload file"""

    parser_classes = (MultiPartParser, FormParser)
    serializer_classe = UploadFileSerializer

    # Upload file by method POST
    """POST"""

    async def uploaded_file_save(self, request):
        file_upload = UploadFile(user=request.data["user"], file=request.FILES["file"])
        await file_upload.asave()
        return file_upload.pk

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

    @extend_schema(
        summary="File upload",
        parameters=[
            OpenApiParameter(
                name="token", location=OpenApiParameter.HEADER, required=True, type=str
            ),
            OpenApiParameter(
                name="file", location=OpenApiParameter.PATH, required=True, type=str
            ),
            OpenApiParameter(
                name="sync_mode",
                location=OpenApiParameter.QUERY,
                required=False,
                type=bool,
            ),
        ],
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

    @extend_schema(
        summary="File download",
        parameters=[
            OpenApiParameter(
                name="token", location=OpenApiParameter.HEADER, required=True, type=str
            ),
            OpenApiParameter(
                name="file_id", location=OpenApiParameter.QUERY, required=True, type=str
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=bytes,
                description="Successful file download",
                examples=[
                    OpenApiExample(
                        "Response example",
                        description="File delete response example",
                        status_codes=[str(status.HTTP_200_OK)],
                    )
                ],
            )
        },
    )
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

    @extend_schema(
        summary="File delete",
        parameters=[
            OpenApiParameter(
                name="token", location=OpenApiParameter.HEADER, required=True, type=str
            ),
            OpenApiParameter(
                name="file_id",
                location=OpenApiParameter.QUERY,
                required=True,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=dict,
                description="Successful file delete",
                examples=[
                    OpenApiExample(
                        "Response example",
                        description="File delete response example",
                        value={
                            "Status": True,
                            "Files_deleted": 1,
                        },
                        status_codes=[str(status.HTTP_200_OK)],
                    )
                ],
            )
        },
    )
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

    @extend_schema(
        summary="File modification",
        parameters=[
            OpenApiParameter(
                name="token", location=OpenApiParameter.HEADER, required=True, type=str
            ),
            OpenApiParameter(
                name="file_id",
                location=OpenApiParameter.QUERY,
                required=True,
                type=str,
            ),
        ],
        responses={
            202: OpenApiResponse(
                response=dict,
                description="Successful file modification",
                examples=[
                    OpenApiExample(
                        "Response example",
                        description="File modification response example",
                        value={
                            "Status": True,
                            "Task_id": "celery_task.id",
                        },
                        status_codes=[str(status.HTTP_202_ACCEPTED)],
                    )
                ],
            )
        },
    )
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
