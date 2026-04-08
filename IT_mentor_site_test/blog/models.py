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

    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

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
