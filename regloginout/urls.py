from django.urls import path
from django_rest_passwordreset.views import (
    reset_password_confirm,
    reset_password_request_token,
)
from django.views.decorators.cache import cache_page
from regloginout.views import (
    ConfirmAccount,
    DeleteAccount,
    LoginAccount,
    LogoutAccount,
    RegisterAccount,
    UserDetails,
)

app_name = "regloginout"

urlpatterns = [
    path("user/register/", RegisterAccount.as_view(), name="user_register"),
    path("user/register/confirm/", ConfirmAccount.as_view(), name="user_confirm"),
    path("user/login/", LoginAccount.as_view(), name="user_login"),
    path(
        "user/details/", cache_page(60 * 15)(UserDetails.as_view()), name="user_details"
    ),
    path("user/logout/", LogoutAccount.as_view(), name="user_logout"),
    path("user/delete/", DeleteAccount.as_view(), name="user_delete"),
    path("user/password_reset/", reset_password_request_token, name="password-reset"),
    path(
        "user/password_reset/confirm/",
        reset_password_confirm,
        name="password-reset-confirm",
    ),
]
