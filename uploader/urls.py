from django.urls import path

from uploader_1.settings import API_VERTION

# from uploader.views import (FileDeleteAPIView, FileDownloadAPIView,
#                             FileProcessingAPIView, FileUploadAPIView)
from uploader.views import FileUploadAPIView

api_vertion = API_VERTION

app_name = "uploader"

urlpatterns = [
    path("file/", FileUploadAPIView.as_view(), name="file_upload"),
]
