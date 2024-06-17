from django.dispatch import Signal, receiver
from django_rest_passwordreset.signals import reset_password_token_created

from regloginout.models import ConfirmEmailToken
from uploader_1.tasks import send_email

new_user_registered: Signal = Signal("user_id")


@receiver(new_user_registered)
def new_user_registered_signal(user_id, **kwargs):
    # send an e-mail to the user
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)
    async_result = send_email.delay(
        token.user.email, f"Password Token for {token.user.email}", token.key
    )
    return {
        "task_id": async_result.task_id,
        "token": token.key,
    }


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправляем письмо с токеном для сброса пароля
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param kwargs:
    :return:
    """
    # send an e-mail to the user
    async_result = send_email.delay(
        reset_password_token.user.email,
        f"Password Reset Token for {reset_password_token.user}",
        reset_password_token.key,
    )
    return {
        "task_id": async_result.task_id,
        "email": reset_password_token.user.email,
        "user": reset_password_token.user,
        "token": reset_password_token.key,
    }
