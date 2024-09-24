from django.db import models


class UploadFile(models.Model):
    file = models.FileField()
    file_name = models.TextField(blank=True)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    user = models.IntegerField()

    def __str__(self):
        return f'file name: {self.file_name}, uploaded on: {self.uploaded_on}'

    class Meta:
        app_label = 'uploader'
