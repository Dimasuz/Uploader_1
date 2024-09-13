import graphene

import regloginout.schema as regloginout_schema
import uploader.schema as uploader_schema
import uploader_mongo.schema as uploader_mongo_schema


class Query(
    regloginout_schema.schema.Query,
    uploader_schema.schema.Query,
    uploader_mongo_schema.schema.Query,
    graphene.ObjectType,
):
    # Inherits all classes and methods from app-specific queries, so no need
    # to include additional code here.
    pass


class Mutation(
    regloginout_schema.schema.Mutation,
    uploader_schema.schema.Mutation,
    uploader_mongo_schema.schema.Mutation,
    graphene.ObjectType,
):
    # Inherits all classes and methods from app-specific mutations, so no need
    # to include additional code here.
    pass


schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)
