import graphene
import graphql_jwt
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from graphene.types.scalars import Scalar
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from regloginout.models import User
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


class Query(graphene.ObjectType):
    user = graphene.Field(UserModelType, token=graphene.String(required=True))
    users = graphene.List(UserModelType)

    def resolve_users(self, info, **kwargs):
        return User.objects.all()

    @login_required
    def resolve_user(self, info, token):
        return User.objects.get(auth_token=token)


# Mutetions
class ObjectField(Scalar):  # to serialize error message from serializer
    @staticmethod
    def serialize(data):
        return data


class MutationPayload(graphene.ObjectType):
    status = graphene.Int(required=True)
    errors = graphene.List(graphene.String, required=True)
    message = ObjectField()
    query = graphene.Field(Query, required=True)

    def resolve_status(self, info):
        # return len(self.errors or []) == 0
        return self.status

    def resolve_errors(self, info):
        return self.errors or []

    def resolve_message(self, info):
        return self.message or []

    def resolve_query(self, info):
        return {}


class UpdateUserInput(graphene.InputObjectType):
    email = graphene.String(required=False)
    first_name = graphene.String(required=False)
    last_name = graphene.String(required=False)
    password = graphene.String(required=False)


class UserMutation(MutationPayload, graphene.Mutation):
    class Arguments:
        input = UpdateUserInput(required=True)
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

        # if not info.context.user.is_authenticated:
        #     errors.append('not_authenticated')
        #
        # if user != info.context.user:
        #     errors.append('wrong_user')

        if input.password:
            try:
                validate_password(input.password)
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                errors.append(error_array)
                return cls(status=False, errors=errors)
            else:
                user.password = input.password

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
            msg = user_serializer.errors
            # перевести в message errors?
            return cls(status=403, message=msg)


class Mutation(graphene.ObjectType):
    user_update = UserMutation.Field()
    # проверить как работают:
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()


schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)


# Mutations can also accept files, that’s how it will work with different integrations:
# class UploadFile(graphene.ClientIDMutation):
# class Input:
# pass
# # nothing needed for uploading file
# # your return fields
# success = graphene.String()
# @classmethod
# def mutate_and_get_payload(cls, root, info, **input):
# # When using it in Django, context will be the request
# files = info.context.FILES
# # Or, if used in Flask, context will be the flask global request
# # files = context.files
# # do something with files
# return UploadFile(success=True)
