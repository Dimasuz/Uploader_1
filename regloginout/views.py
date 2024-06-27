from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from drf_spectacular.utils import (OpenApiExample, OpenApiParameter,
                                   OpenApiResponse, extend_schema)
from rest_framework import status
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
    # the keys have a view: "KEY_PREFIX:VERSION:KEY_BODY", so we need only KEY_BODY
    # key_list = [i.decode().split(':')[-1] for i in key_list_by_prefix] # not so good there could be more ":"
    key_list = [
        i.decode()[len(cache_key_prefix) + len(cache_version) + 2 :]
        for i in key_list_by_prefix
    ]
    cache.delete_many(key_list)

    return not bool(cache._cache.get_client().keys(f"*{cache_key_prefix}*"))


# decorators @extend_schema is for OPEN API
@extend_schema(
    tags=["user/"],
    summary="User registration",
    parameters=[
        OpenApiParameter(
            name="email", location=OpenApiParameter.QUERY, required=True, type=str
        ),
        OpenApiParameter(
            name="password", location=OpenApiParameter.QUERY, required=True, type=str
        ),
        OpenApiParameter(
            name="first_name", location=OpenApiParameter.QUERY, required=False, type=str
        ),
        OpenApiParameter(
            name="last_name", location=OpenApiParameter.QUERY, required=False, type=str
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=dict,
            description="Successful registration",
            examples=[
                OpenApiExample(
                    "Response example",
                    description="User registration response example",
                    value={
                        "Status": True,
                        "Task_id": "celery_task.id",
                        "Token": "token.key",
                    },
                    status_codes=[str(status.HTTP_201_CREATED)],
                ),
            ],
        )
    },
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
                            "Task_id": send_mail[0][1]["task_id"],
                            "Token": token.key,
                        },
                        status=201,
                    )
                else:
                    return JsonResponse(
                        {"Status": False, "Errors": user_serializer.errors}
                    )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


@extend_schema(
    tags=["user/"],
    summary="Confirm email",
    parameters=[
        OpenApiParameter(
            name="email", location=OpenApiParameter.QUERY, required=True, type=str
        ),
        OpenApiParameter(
            name="token", location=OpenApiParameter.QUERY, required=True, type=str
        ),
    ],
    responses={
        204: OpenApiResponse(
            description="Successful confirmation",
        )
    },
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
                return Response(status=204)
            else:
                return JsonResponse(
                    {"Status": False, "Errors": "Неправильно указан токен или email"}
                )

        return JsonResponse(
            {"Status": False, "Errors": "Не указаны все необходимые аргументы"}
        )


@extend_schema(
    tags=["user/"],
    summary="User login",
    parameters=[
        OpenApiParameter(
            name="email", location=OpenApiParameter.QUERY, required=True, type=str
        ),
        OpenApiParameter(
            name="password", location=OpenApiParameter.QUERY, required=True, type=str
        ),
    ],
    responses={
        202: OpenApiResponse(
            response=dict,
            description="Successful login",
            examples=[
                OpenApiExample(
                    "Response example",
                    description="User login response example",
                    value={
                        "Status": True,
                        "Task_id": "celery_task.id",
                        "Token": "token.key",
                    },
                    status_codes=[str(status.HTTP_202_ACCEPTED)],
                ),
            ],
        )
    },
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
                            "Task_id": send_mail[0][1]["task_id"],
                        },
                        status=202,
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
    tags=["user/"],
    summary="User logout",
    parameters=[
        OpenApiParameter(
            name="token", location=OpenApiParameter.HEADER, required=True, type=str
        ),
    ],
    responses={
        204: OpenApiResponse(
            description="Successful logout",
        )
    },
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

        return Response(status=204)


# delete account
@extend_schema(
    tags=["user/"],
    summary="User delete",
    parameters=[
        OpenApiParameter(
            name="token", location=OpenApiParameter.HEADER, required=True, type=str
        ),
    ],
    responses={
        204: OpenApiResponse(
            description="Successful user delete",
        )
    },
)
class DeleteAccount(APIView):
    """
    Класс для удаления пользователей
    """

    # Delete методом DELETE
    def delete(self, request):

        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"},
                status=403,
            )

        request.user.delete()
        cache_clear()

        return Response(status=204)


# user details
class UserDetails(APIView):
    """
    Класс для работы с данными пользователя
    """

    # Получение данных методом GET
    @extend_schema(
        tags=["user/"],
        summary="User details get",
        parameters=[
            OpenApiParameter(
                name="token", location=OpenApiParameter.HEADER, required=True, type=str
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="Successful user details get",
            )
        },
    )
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"Status": False, "Error": "Log in required"}, status=403
            )

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование методом POST
    @extend_schema(
        tags=["user/"],
        summary="User details post",
        parameters=[
            OpenApiParameter(
                name="token", location=OpenApiParameter.HEADER, required=True, type=str
            ),
            OpenApiParameter(
                name="password",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="first_name",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="last_name",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
            ),
        ],
        responses={
            202: OpenApiResponse(
                response=dict,
                description="Successful details change",
                examples=[
                    OpenApiExample(
                        "Response example",
                        description="User change details response example. Changed details will send to the email.",
                        value={
                            "Status": True,
                            "Task_id": "celery_task.id",
                        },
                        status_codes=[str(status.HTTP_202_ACCEPTED)],
                    ),
                ],
            )
        },
    )
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
                },
                status=202,
            )
        else:
            return JsonResponse({"Status": False, "Errors": user_serializer.errors})


# Celery status
@extend_schema(
    tags=["celery_status/"],
    summary="Celery status get",
    parameters=[
        OpenApiParameter(
            name="task_id", location=OpenApiParameter.QUERY, required=True, type=str
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=dict,
            description="Successful celery status get",
            examples=[
                OpenApiExample(
                    "Response example",
                    description="Celery status get response example",
                    value={
                        "Status": "PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED",
                        "Result": True,
                    },
                    status_codes=[str(status.HTTP_200_OK)],
                )
            ],
        )
    },
)
class CeleryStatus(APIView):
    """
    Класс для получения статуса отлооженных задач в Celery
    """

    # Получение сатуса задач Celery методом GET
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        task_id = request.query_params.get("task_id")
        if task_id:
            try:
                task = AsyncResult(task_id)
                task_status = task.status
                task_result = task.ready()
                return JsonResponse(
                    {"Status": task_status, "Result": task_result}, status=200
                )
            except Exception as err:
                return err

        return JsonResponse({"Status": False, "Error": "Task_id required"}, status=400)
