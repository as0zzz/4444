from django.db import models


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