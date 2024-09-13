from django.urls import path
from graphene_file_upload.django import FileUploadGraphQLView

# from uploader.views import (FileDeleteAPIView, FileDownloadAPIView,
#                             FileProcessingAPIView, FileUploadAPIView)
from uploader.views import FileUploadAPIView
from uploader_1.settings import API_VERTION

api_vertion = API_VERTION

app_name = "uploader"

urlpatterns = [
    path("file/", FileUploadAPIView.as_view(), name="file_upload"),
    path("file/db/graphql/", FileUploadGraphQLView.as_view(graphiql=True)),
]
