from django.urls import path

from uploader_1.settings import API_VERTION
from uploader_mongo.views import FileUploadMongoAPIView

api_vertion = API_VERTION

app_name = "uploader_mongo"

urlpatterns = [
    path("file/mongo/", FileUploadMongoAPIView.as_view(), name="file_upload_mongo"),
]
