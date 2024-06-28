import graphene
from graphene_django import DjangoObjectType
from regloginout.models import User

class UserModelType(DjangoObjectType):
    class Meta:
        model = User

class Query(graphene.ObjectType):
    users = graphene.List(UserModelType)

    def resolve_users(self, info, **kwargs):
        return User.objects.all()

schema = graphene.Schema(query=Query, auto_camelcase=False)
