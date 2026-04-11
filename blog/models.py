from django.db import models
# venv\Scripts\Activate.ps1
class Users(models.Model):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20)

    class Meta:
        db_table = 'users'   # новая таблица

class Emails_workers(models.Model):
    email = models.EmailField(unique=True)

    class Meta:
        db_table = 'emails_workers'

class Mentors(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    patronymic = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100)
    phone = models.CharField(max_length=12)
    password = models.CharField(max_length=255)

    class Meta:
        db_table = 'mentors'

class Interns(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    patronymic = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100)
    phone = models.CharField(max_length=12)
    password = models.CharField(max_length=255)

    class Meta:
        db_table = 'interns'

