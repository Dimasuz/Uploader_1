from django.urls import path

from app_auth0.views import (callback, index, login, logout, private,
                             private_scoped, public)

app_name = "app_auth0"

# for auth0 api
urlpatterns = [
    # for Auth0 api
    path("api/v1/auth0/public", public),
    path("api/v1/auth0/private", private),
    path("api/v1/auth0/private-scoped", private_scoped),
    # for Auth0 web
    path("auth0/", index, name="auth0_index"),
    path("auth0/login", login, name="auth0_login"),
    path("auth0/logout/", logout, name="auth0_logout"),
    path("auth0/callback", callback, name="auth0_callback"),
]
