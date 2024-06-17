# from django.conf import settings


class UploaderRouter:
    """
    A router to control database operations on models in the
    uploader application.
    """

    route_app_labels = {"uploader"}
    # db_uploader = settings.DATABASES['db_uploader']

    def db_for_read(self, model, **hints):
        """
        Attempts to read uploader models go to mongo_db.
        """
        if model._meta.app_label in self.route_app_labels:
            return "db_uploader"
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write uploader models go to mongo_db.
        """
        if model._meta.app_label in self.route_app_labels:
            return "db_uploader"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if models of the uploader app is
        involved.
        """
        if (
            obj1._meta.app_label in self.route_app_labels
            or obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the uploaders apps only appear in the
        'db_uploader' database.
        """
        if app_label in self.route_app_labels:
            return db == "db_uploader"
        return None


# python manage.py migrate --database=db_uploader
