from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from regloginout.models import ConfirmEmailToken
from regloginout.serializers import UserSerializer
from regloginout.signals import new_user_registered


def index(request):
    return render(request, "regloginout/index.html")


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
                    # для применения celery возвращаем task задачи для возможности контроля ее выполнения
                    send_mail = new_user_registered.send(
                        sender=self.__class__, user_id=user.id
                    )
                    return JsonResponse(
                        {
                            "Status": True,
                            "task_id": send_mail[0][1]["task_id"],
                            "token": send_mail[0][1]["token"],
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
                    return JsonResponse({"Status": True, "Token": token.key})
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
            return JsonResponse({"Status": True})
        else:
            return JsonResponse({"Status": False, "Errors": user_serializer.errors})
