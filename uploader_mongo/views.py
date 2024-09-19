import asyncio
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse, JsonResponse
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from mongoengine import DoesNotExist, ValidationError
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from regloginout.models import User
from uploader_1.settings import MAX_TIME_UPLOAD_FILE
from uploader_1.tasks import processing_file_mongo

from .models import UploadFileMongo


@extend_schema(
    tags=["file/mongo/"],
)
class FileUploadMongoAPIView(APIView):
    """Upload file"""

    parser_classes = (MultiPartParser, FormParser)

    # Upload file by method POST
    """POST"""
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

        if "file" in request.FILES:
            file = request.FILES["file"]
        else:
            return JsonResponse(
                {"Status": False, "Error": 'There is no "file" in the request.'},
                status=400,
            )

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
                        },
                        status_codes=[str(status.HTTP_200_OK)],
                    )
                ],
            )
        },
    )
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

        if isinstance(uploaded_file, UploadFileMongo):

            # processing by Celery
            async_result = processing_file_mongo.delay(str(uploaded_file.id))
            return JsonResponse(
                {
                    "Status": True,
                    "Task_id": async_result.task_id,
                },
                status=202,
            )
        else:
            return uploaded_file
