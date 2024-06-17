import time
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from uploader_1.celery import app
from uploader_mongo.models import UploadFileMongo


# формирование и отправка писем для применения в celery
@app.task
def send_email(email, title, massage):

    msg = EmailMultiAlternatives(
        # title:
        title,
        # message:
        massage,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [email],
    )
    msg.send()


# task for processing file
@app.task
def processing_file(file_path):

    time.sleep(10)

    with open(file_path, "rb+") as f:
        f.seek(0, 2)
        f.write(f"\ncelery_{datetime.now()}".encode())

    return file_path


# task for processing file in mongo
@app.task
def processing_file_mongo(file_id):

    time.sleep(5)

    file_celery = UploadFileMongo.objects.get(pk=file_id)
    content_type = file_celery.file.content_type
    filename = file_celery.file.filename
    file_content = file_celery.file.read()
    file_content += f"\ncelery_{datetime.now()}".encode()
    file_celery.file.replace(file_content, content_type=content_type, filename=filename)
    file_modify = file_celery.save()

    time.sleep(5)

    return str(file_modify.id)
