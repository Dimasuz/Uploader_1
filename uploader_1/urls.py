from debug_toolbar import urls as debug_urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)

from regloginout.views import CeleryStatus, index
from uploader_1.settings import API_VERTION

from graphene_django.views import GraphQLView
from . import schema

api_vertion = API_VERTION

urlpatterns = [
    path("", index, name="index"),
    path("admin/", admin.site.urls),
    path("__debug__/", include(debug_urls)),  # debug toolbar URLS
    path(f"api/{api_vertion}/", include("regloginout.urls", namespace="regloginout")),
    path(f"api/{api_vertion}/", include("uploader.urls", namespace="uploader")),
    path(
        f"api/{api_vertion}/",
        include("uploader_mongo.urls", namespace="uploader_mongo"),
    ),
    path(
        f"api/{api_vertion}/celery_status/",
        CeleryStatus.as_view(),
        name="celery_status",
    ),
    # for allauth
    path("accounts/", include("allauth.urls")),
    # for auth0
    path("", include("app_auth0.urls", namespace="app_auth0")),
    path("", include("social_django.urls")),
    # for django-silk
    path("silk/", include("silk.urls", namespace="silk")),
    # доступ к описанию проекта из API
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",),

    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # graphene. Given that schema path is defined in GRAPHENE['SCHEMA'] in your settings.py
    path(f"api/{api_vertion}/graphql/", GraphQLView.as_view(graphiql=True)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
