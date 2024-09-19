import graphene
import graphql_jwt
from celery.result import AsyncResult
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from graphene.types.scalars import Scalar
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required
from rest_framework.authtoken.models import Token

from regloginout.models import ConfirmEmailToken, User
from regloginout.serializers import UserSerializer
from regloginout.signals import user_send_massage
from regloginout.views import cache_clear


class UserModelType(DjangoObjectType):
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
        )


class CeleryType(graphene.ObjectType):
    task_status = graphene.String()
    task_result = graphene.String()


class Query(graphene.ObjectType):
    user = graphene.Field(UserModelType, token=graphene.String(required=True))
    users = graphene.List(UserModelType)
    celery = graphene.Field(CeleryType, task_id=graphene.String(required=True))

    # def resolve_users(self, info, **kwargs):
    #     return User.objects.all()

    def resolve_celery(self, info, task_id):
        try:
            task = AsyncResult(task_id)
            task_status = task.status
            task_result = task.ready()
            return CeleryType(task_status=task_status, task_result=task_result)
        except Exception as err:
            return err

    @login_required
    def resolve_user(self, info, token):
        return User.objects.get(auth_token=token)


# Mutetions
class ObjectField(Scalar):  # to serialize error message from serializer
    @staticmethod
    def serialize(data):
        return data


class ObjectPayload(graphene.ObjectType):
    status = graphene.Int(required=True)
    errors = graphene.List(graphene.String, required=True)
    message = ObjectField()
    query = graphene.Field(Query, required=True)

    def resolve_status(self, info):
        return self.status

    def resolve_errors(self, info):
        return self.errors or []

    def resolve_message(self, info):
        return self.message or []

    def resolve_query(self, info):
        return {}


class UserInput(graphene.InputObjectType):
    email = graphene.String(required=False)
    first_name = graphene.String(required=False)
    last_name = graphene.String(required=False)
    password = graphene.String(required=False)


class UserMutation(ObjectPayload, graphene.Mutation):
    class Arguments:
        input = UserInput(required=True)
        token = graphene.String(required=True)

    user = graphene.Field(UserModelType)

    @classmethod
    @login_required
    def mutate(cls, root, info, token, input):
        errors = []
        try:
            user = User.objects.get(auth_token=token)
        except ObjectDoesNotExist:
            errors.append("Log in required")
            return cls(status=404, errors=errors)

        if not info.context.user.is_authenticated:
            errors.append("not_authenticated")
            return cls(status=404, errors=errors)

        # if user != info.context.user:
        #     errors.append('wrong_user')
        #     return cls(status=404, errors=errors)

        if input.password:
            try:
                validate_password(input.password)
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                errors.append(error_array)
                return cls(status=400, errors=errors)
            else:
                user.set_password(input.password)

        user_serializer = UserSerializer(user, data=input, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            send_mail = user_send_massage.send(
                sender=cls.__class__,
                email=user.email,
                title="Change details.",
                massage=f"The details was change. New details is {input}",
            )
            cache_clear()
            task_id = {"task_id": send_mail[0][1]["task_id"]}
            return cls(user=user, status=202, message=task_id)
        else:
            errors.append(user_serializer.errors)
            return cls(status=403, errors=errors)


class UserCreate(ObjectPayload, graphene.Mutation):
    class Arguments:
        input = UserInput(required=True)

    user = graphene.Field(UserModelType)

    @classmethod
    def mutate(cls, root, info, input):
        errors = []
        if {"first_name", "last_name", "email", "password"}.issubset(input):
            # проверяем пароль на сложность
            try:
                validate_password(input.password)
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                errors.append(error_array)
                return cls(status=400, errors=errors)
            else:
                # проверяем данные для уникальности имени пользователя
                input._mutable = True
                input.update({})
                user_serializer = UserSerializer(data=input)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(input.password)
                    user.save()
                    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
                    # для применения celery возвращаем task задачи для возможности контроля ее выполнения
                    send_mail = user_send_massage.send(
                        sender=cls.__class__,
                        email=user.email,
                        title=f"Token conformation for {user.email}",
                        massage=token.key,
                    )
                    cache_clear()
                    message = {
                        "task_id": send_mail[0][1]["task_id"],
                        "token": token.key,
                    }
                    return cls(user=user, status=202, message=message)
                else:
                    errors.append(user_serializer.errors)
                    return cls(status=403, errors=errors)
        else:
            errors.append("Не указаны все необходимые аргументы")
            return cls(status=403, errors=errors)


class UserConfirm(ObjectPayload, graphene.Mutation):
    class Arguments:
        input = UserInput(required=True)
        token = graphene.String(required=True)

    # user = graphene.Field(UserModelType)

    @classmethod
    def mutate(cls, root, info, token, input):
        errors = []

        if token and input.email:

            token_confirm = ConfirmEmailToken.objects.filter(
                user__email=input.email,
                key=token,
            ).first()

            if token_confirm:
                token_confirm.user.is_active = True
                token_confirm.user.save()
                token_confirm.delete()
                return cls(status=204)
            else:
                errors.append(["Wrong token or email"])
                return cls(status=404, errors=errors)

        else:
            errors.append("Не указаны все необходимые аргументы")
            return cls(status=404, errors=errors)


class UserLogin(ObjectPayload, graphene.Mutation):
    class Arguments:
        input = UserInput(required=True)

    user = graphene.Field(UserModelType)

    @classmethod
    def mutate(cls, root, info, input):
        errors = []
        if {"email", "password"}.issubset(input):
            user = authenticate(
                username=input.email,
                password=input.password,
            )

            if user is not None:

                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    login(info.context, user)
                    send_mail = user_send_massage.send(
                        sender=cls.__class__,
                        email=user.email,
                        title=f"Token login for {user.email}",
                        massage=token.key,
                    )
                    message = {
                        "task_id": send_mail[0][1]["task_id"],
                        "token": token.key,
                    }
                    return cls(status=202, message=message)
                else:
                    errors.append("User is not active")
                    return cls(status=403, errors=errors)

            else:
                errors.append("Не удалось авторизовать")
                return cls(status=403, errors=errors)

        else:
            errors.append("Не указаны все необходимые аргументы")
            return cls(status=403, errors=errors)


class UserLogout(ObjectPayload, graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)

    user = graphene.Field(UserModelType)

    @classmethod
    @login_required
    def mutate(cls, root, info, token):
        errors = []

        try:
            user = User.objects.get(auth_token=token)
        except ObjectDoesNotExist:
            errors.append("Log in required")
            return cls(status=404, errors=errors)

        if not info.context.user.is_authenticated:
            errors.append("not_authenticated")
            return cls(status=404, errors=errors)

        # if user != info.context.user:
        #     errors.append('wrong_user')
        #     return cls(status=404, errors=errors)

        user.auth_token.delete()
        logout(info.context)
        cache_clear()

        return cls(status=204)


class UserDelete(ObjectPayload, graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)

    user = graphene.Field(UserModelType)

    @classmethod
    @login_required
    def mutate(cls, root, info, token):
        errors = []

        try:
            user = User.objects.get(auth_token=token)
        except ObjectDoesNotExist:
            errors.append("Log in required")
            return cls(status=404, errors=errors)

        if not info.context.user.is_authenticated:
            errors.append("not_authenticated")
            return cls(status=404, errors=errors)

        # if user != info.context.user:
        #     errors.append('wrong_user')
        #     return cls(status=404, errors=errors)

        user.delete()
        cache_clear()

        return cls(status=204)


class Mutation(graphene.ObjectType):
    user_update = UserMutation.Field()
    user_create = UserCreate.Field()
    user_confirm = UserConfirm.Field()
    user_login = UserLogin.Field()
    user_logout = UserLogout.Field()
    user_delete = UserDelete.Field()
    # проверить как работают:
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()


schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)
