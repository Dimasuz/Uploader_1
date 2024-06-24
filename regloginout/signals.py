from django.dispatch import Signal, receiver
from django_rest_passwordreset.signals import reset_password_token_created

from uploader_1.tasks import send_email

user_send_massage: Signal = Signal()


@receiver(user_send_massage)
def user_send_massage_signal(email, title, massage, **kwargs):
    # send an e-mail to the user
    async_result = send_email.delay(
        email,
        title,
        massage,
    )
    return {
        "task_id": async_result.task_id,
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
