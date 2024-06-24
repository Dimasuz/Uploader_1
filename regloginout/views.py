from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from regloginout.models import ConfirmEmailToken
from regloginout.serializers import UserSerializer
from regloginout.signals import user_send_massage


def index(request):
    return render(request, "regloginout/index.html")


def cache_clear():
    # clear whole cache
    # cache.clear()
    # clear app cache by prefix
    cache_key_prefix = settings.CACHES["default"]["KEY_PREFIX"]
    cache_version = str(settings.CACHES["default"]["VERSION"])
    key_list_by_prefix = cache._cache.get_client().keys(f"*{cache_key_prefix}*")
    # the keys has view: "KEY_PREFIX:VERSION:KEY_BODY", so we need only KEY_BODY
    # key_list = [i.decode().split(':')[-1] for i in key_list_by_prefix] # not so good there could be more ":"
    key_list = [
        i.decode()[len(cache_key_prefix) + len(cache_version) + 2 :]
        for i in key_list_by_prefix
    ]
    cache.delete_many(key_list)

    return not bool(cache._cache.get_client().keys(f"*{cache_key_prefix}*"))


# decorators @extend_schema is for OPEN API
@extend_schema(
    request=UserSerializer,
    responses={201: UserSerializer},
)
class RegisterAccount(APIView):
    """
    User registration
    """

    permission_classes = (AllowAny,)

    # Регистрация методом POST
    def post(self, request, *args, **kwargs):

        # проверяем обязательные аргументы
        if {"first_name", "last_name", "email", "password"}.issubset(request.data):
            # проверяем пароль на сложность
            try:
                validate_password(request.data["password"])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse(
                    {"Status": False, "Errors": {"password": error_array}}
                )
            else:
                # проверяем данные для уникальности имени пользователя
                request.data._mutable = True
                request.data.update({})
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(request.data["password"])
                    user.save()
                    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
                    # для применения celery возвращаем task задачи для возможности контроля ее выполнения
                    send_mail = user_send_massage.send(
                        sender=self.__class__,
                        email=user.email,
                        title=f"Token conformation for {user.email}",
                        massage=token.key,
                    )
                    return JsonResponse(
                        {
                            "Status": True,
                            "task_id": send_mail[0][1]["task_id"],
                            "token": token.key,
                        }
                    )
                else:
                    return JsonResponse(
                        {"Status": False, "Errors": user_serializer.errors}
                    )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


@extend_schema(
    request=UserSerializer,
    responses={201: UserSerializer},
)
class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    permission_classes = (AllowAny,)

    # Подтверждение почтового адреса методом POST
    def post(self, request, *args, **kwargs):

        # проверяем обязательные аргументы
        if {"email", "token"}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(
                user__email=request.data["email"], key=request.data["token"]
            ).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({"Status": True})
            else:
                return JsonResponse(
                    {"Status": False, "Errors": "Неправильно указан токен или email"}
                )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


@extend_schema(
    request=UserSerializer,
    responses={201: UserSerializer},
)
class LoginAccount(APIView):
    """
    Класс для логина пользователей
    """

    permission_classes = (AllowAny,)

    # Login методом POST
    def post(self, request, *args, **kwargs):

        if {"email", "password"}.issubset(request.data):
            user = authenticate(
                request,
                username=request.data["email"],
                password=request.data["password"],
            )

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    login(request, user)
                    send_mail = user_send_massage.send(
                        sender=self.__class__,
                        email=user.email,
                        title=f"Token login for {user.email}",
                        massage=token.key,
                    )
                    return JsonResponse(
                        {
                            "Status": True,
                            "Token": token.key,
                            "task_id": send_mail[0][1]["task_id"],
                        }
                    )
                else:
                    JsonResponse(
                        {"Status": False, "Errors": "User is not active"},
                        status=403,
                    )

            return JsonResponse(
                {"Status": False, "Errors": "Не удалось авторизовать", "User": user},
                status=403,
            )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"},
            status=403,
        )


@extend_schema(
    request=UserSerializer,
    responses={201: UserSerializer},
)
class LogoutAccount(APIView):
    """
    Класс для логаута пользователей
    """

    # Logout методом POST
    def post(self, request):

        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"}, status=403
            )

        request.user.auth_token.delete()
        logout(request)
        cache_clear()

        return JsonResponse({"Status": True})


class DeleteAccount(APIView):
    """
    Класс для удаления пользователей
    """

    # Delete методом DELETE
    def delete(self, request):

        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"}, status=403
            )

        request.user.delete()
        cache_clear()

        return JsonResponse({"Status": True})


@extend_schema(
    request=UserSerializer,
    responses={201: UserSerializer},
)
class UserDetails(APIView):
    """
    Класс для работы с данными пользователя
    """

    # Получение данных методом GET
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"}, status=403
            )

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование методом POST
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"}, status=403
            )
        # проверяем обязательные аргументы
        if "password" in request.data:
            # проверяем пароль на сложность
            try:
                validate_password(request.data["password"])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse(
                    {"Status": False, "Errors": {"password": error_array}}
                )
            else:
                request.user.set_password(request.data["password"])

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            send_mail = user_send_massage.send(
                sender=self.__class__,
                email=request.user.email,
                title="Change details.",
                massage=f"The details was change. New details is {request.data.dict()}",
            )
            cache_clear()
            return JsonResponse(
                {
                    "Status": True,
                    "task_id": send_mail[0][1]["task_id"],
                }
            )
        else:
            return JsonResponse({"Status": False, "Errors": user_serializer.errors})
