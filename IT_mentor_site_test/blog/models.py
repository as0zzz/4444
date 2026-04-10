from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

import os
import uuid

from django.db import models
from django.utils import timezone



class Open1(models.Model):
    email = models.EmailField(unique=True)
    pa = models.CharField(max_length=255)

    class Meta:
        db_table = 'open_1'


class Open3(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    patronymic = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100)
    phone = models.CharField(max_length=12)
    pa = models.CharField(max_length=255)

    class Meta:
        db_table = 'open_3'









def chat_attachment_upload_to(instance, filename):
    extension = os.path.splitext(filename)[1]
    return f"chat_attachments/{timezone.now():%Y/%m/%d}/{uuid.uuid4().hex}{extension}"


class Chat(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        Open1,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_chats",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat"
        ordering = ["-updated_at", "-created_at", "-id"]


class ChatParticipant(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(Open1, on_delete=models.CASCADE, related_name="chat_participants")
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "chat_participant"
        unique_together = ("chat", "user")


class ChatMessage(models.Model):
    TYPE_USER = "user"
    TYPE_SYSTEM = "system"
    TYPE_CHOICES = [
        (TYPE_USER, "Пользовательское"),
        (TYPE_SYSTEM, "Системное"),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        Open1,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_chat_messages",
    )
    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_USER)
    text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at", "id"]


class ChatAttachment(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=chat_attachment_upload_to)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255, blank=True, default="")
    size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_attachment"
        ordering = ["id"]















class UserData(models.Model):
    user = models.OneToOneField(Open3, on_delete=models.CASCADE, related_name='extra_data')

    event_phone = models.CharField(max_length=12)
    fio = models.CharField(max_length=100)
    event_email = models.EmailField(unique=True)
    event_name = models.TextField(blank=True, verbose_name='Название мероприятия')
    field_of_work = models.TextField(blank=True, verbose_name='Область работы')
    organization_of_work = models.TextField(blank=True, verbose_name='Организация работы')
    event_description = models.TextField(blank=True, verbose_name='Описание мероприятия')

    def __str__(self):
        return f"Данные пользователя {self.user.name}"

    class Meta:
        db_table = 'user_data'




class Event(models.Model):
    user = models.ForeignKey(Open3, on_delete=models.CASCADE, related_name='events')

    # Данные из формы
    event_name = models.CharField(max_length=200, verbose_name='Название мероприятия')
    event_phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    event_email = models.EmailField(blank=True, verbose_name='Email')
    fio = models.CharField(max_length=200, verbose_name='ФИО')
    field_of_work = models.CharField(max_length=100, verbose_name='Сфера деятельности')
    organization_of_work = models.CharField(max_length=200, verbose_name='Организация')

    # Для карточки на главной
    image = models.ImageField(upload_to='images/4.png', blank=True, null=True, verbose_name='Фото')

    language = models.CharField(max_length=20, default='russian', verbose_name='Язык')

    created_at = models.DateTimeField(auto_now_add=True)

    event_description = models.TextField(verbose_name='Описание мероприятия')

    def __str__(self):
        return self.event_name

    class Meta:
        db_table = 'events'
