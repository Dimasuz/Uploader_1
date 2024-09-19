from django.urls import path
from graphene_django.views import GraphQLView
from graphene_file_upload.django import FileUploadGraphQLView

from uploader.schema import schema

# from uploader.views import (FileDeleteAPIView, FileDownloadAPIView,
#                             FileProcessingAPIView, FileUploadAPIView)
from uploader.views import FileUploadAPIView
from uploader_1.settings import API_VERTION

api_vertion = API_VERTION

app_name = "uploader"

urlpatterns = [
    path("file/", FileUploadAPIView.as_view(), name="file_upload"),
    path("graphql/db/", FileUploadGraphQLView.as_view(graphiql=True)),
    # path("file/graphql/", GraphQLView.as_view(graphiql=True, schema=schema)),
]
