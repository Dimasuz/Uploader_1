import datetime
import os

from mongoengine import DateTimeField, Document, FileField, LongField, connect

mongo_db_name = os.environ.get("MONGO_DB_NAME", "db_mongo")
mongo_db_host = os.environ.get("MONGO_DB_HOST", "localhost")
mongo_db_port = int(os.environ.get("MONGO_DB_PORT", 27017))
mongo_db_username = os.environ.get("MONGO_INITDB_ROOT_USERNAME", "username")
mongo_db_password = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "password")

connect(
    mongo_db_name,
    host=mongo_db_host,
    port=mongo_db_port,
    username=mongo_db_username,
    password=mongo_db_password,
)


class UploadFileMongo(Document):
    file = FileField(required=True)
    uploaded_on = DateTimeField(default=datetime.datetime.utcnow, required=True)
    user = LongField(required=True)
