from django.apps import AppConfig


class BackendConfig(AppConfig):
    name = "regloginout"

    def ready(self):
        """
        импортируем сигналы
        """
        pass
