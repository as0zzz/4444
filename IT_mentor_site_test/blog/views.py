from django.shortcuts import render, redirect
from django.http import HttpResponse
import requests
import json
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .models import Open1, Open3
from django.contrib import messages


def open_1(request):
    print("ФУНКЦИЯ open_1 ВЫЗВАНА")
    print("Метод запроса:", request.method)

    if request.method == 'POST':
        print("Оригинальные POST данные:", dict(request.POST))

        normalized_post = {}
        for key, value in request.POST.items():
            normalized_post[key.lower()] = value

        print("Нормализованные POST данные:", normalized_post)

        email = normalized_post.get('email')
        password = normalized_post.get('pa')

        print(f"Извлечено: email={email}, password={password}")

        if email and password:
            try:
                user = Open1.objects.get(email=email, pa=password)

                request.session['user_id'] = user.id
                request.session['is_authenticated'] = True

                print(f"✅ Успешный вход! ID: {user.id}")
                print("Сессия:", dict(request.session))

                return redirect('home')
            except Open1.DoesNotExist:
                print("❌ Пользователь не найден")
                return render(request, 'blog/Вход_1.html', {'error': 'Неверные данные'})
        else:
            print("❌ Email или пароль не найдены")
            return render(request, 'blog/Вход_1.html', {'error': 'Заполните все поля'})

    return render(request, 'blog/Вход_1.html')








def open_3(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        name = request.POST.get('name')
        patronymic = request.POST.get('patronymic')
        surname = request.POST.get('surname')
        phone = request.POST.get('phone')
        password = request.POST.get('pa')

        print(f"Получены данные: {email}, {password}")

        result = check_user_in_nocodb_2(email, name, patronymic, surname, phone, password)

        if result:
            request.session['user_id'] = result['id']
            request.session['user_email'] = result['email']
            request.session['user_name'] = result.get('name', '')
            request.session['user_patronymic'] = result.get('patronymic', '')
            request.session['user_surname'] = result.get('surname', '')
            request.session['user_phone'] = result.get('phone', '')
            request.session['is_authenticated_2'] = True
            request.session.modified = True

            if result['found_in'] == 'open1':
                return render(request, 'blog/Вход_1.html', {
                    'error': 'Пользователь уже зарегистрирован в системе'
                })
            else:
                return render(request, 'blog/Главная страница.html')
        else:
            return render(request, 'blog/Вход_3.html', {
                'error': 'Ошибка регистрации. Проверьте данные.'
            })

    return render(request, 'blog/Вход_3.html')


def check_user_in_nocodb(email, pa, request=None):
    """Проверка пользователя в таблице Open1"""
    try:
        user = Open1.objects.get(email=email, pa=pa)

        if request:
            request.session['user_id'] = user.id
            request.session['user_email'] = user.email
            request.session['user_name'] = user.name
            request.session['user_patronymic'] = user.patronymic
            request.session['user_surname'] = user.surname
            request.session['user_phone'] = user.phone
            request.session['is_authenticated'] = True

        return {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'patronymic': user.patronymic,
            'pa': user.pa
        }

    except Open1.DoesNotExist:
        return None





def check_user_in_nocodb_2(email, name, patronymic, surname=None, phone=None, pa=None, request=None):
    """Проверка в open_1, если нет - в open_3, если нет - создает в open_3"""

    print("\n" + "=" * 60)
    print("check_user_in_nocodb_2 ВЫЗВАНА")
    print(f"Параметры:")
    print(f"  email: {repr(email)}")
    print(f"  name: {repr(name)}")
    print(f"  patronymic: {repr(patronymic)}")
    print(f"  surname: {repr(surname)}")
    print(f"  phone: {repr(phone)}")
    print(f"  pa: {repr(pa)}")
    print(f"  request: {request is not None}")
    print("=" * 60)

    if not email:
        print("❌ Ошибка: email не передан или пустой!")
        print(f"   email = {repr(email)}")
        return None

    if not name:
        print("❌ Ошибка: name не передан или пустой!")
        return None

    if not patronymic:
        print("⚠️ Предупреждение: patronymic не передан, используем пустую строку")
        patronymic = ""

    try:
        user = Open1.objects.get(email=email)
        print(f"✅ Найден в Open1: {user.email}")

        if request:
            request.session['user_id'] = user.id
            request.session['user_email'] = user.email
            request.session['is_authenticated'] = True

        return {
            'found_in': 'open1',
            'id': user.id,
            'email': user.email,
            'pa': user.pa
        }
    except Open1.DoesNotExist:
        print("❌ Не найден в Open1")

    try:
        temp_user = Open3.objects.get(email=email)
        print(f"✅ Найден в Open3: {temp_user.email}")

        return {
            'found_in': 'open3',
            'id': temp_user.id,
            'email': temp_user.email,
            'name': temp_user.name,
            'patronymic': temp_user.patronymic,
            'surname': temp_user.surname,
            'phone': temp_user.phone,
            'pa': temp_user.pa
        }
    except Open3.DoesNotExist:
        print("❌ Не найден в Open3")

    try:
        print(f"Создаем нового пользователя:")
        print(f"   email: {email}")
        print(f"   name: {name}")
        print(f"   patronymic: {patronymic}")
        print(f"   pa: {pa or ''}")

        new_user = Open3.objects.create(
            email=email,
            name=name,
            patronymic=patronymic or '',
            pa=pa,
            surname=surname,
            phone=phone
        )
        new_user2 = Open1.objects.create(
            email=email,
            pa=pa
        )
        print(f"✅ Создан пользователь с ID: {new_user.id}")
        print(f"✅ Создан пользователь с ID: {new_user2.id}")

        return {
            'found_in': 'created',
            'id': new_user.id,
            'email': new_user.email,
            'name': new_user.name,
            'patronymic': new_user.patronymic,
            'surname': new_user.surname,
            'phone': new_user.phone,
            'pa': new_user.pa
        }
    except Exception as e:
        print(f"❌ Ошибка при создании: {e}")
        return None









# ДЕКОРАТОР


def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        print("=== LOGIN_REQUIRED ===")
        print("Сессия:", dict(request.session))

        if not request.session.get('is_authenticated'):
            print("Нет авторизации, редирект на login")
            return redirect('open_1')

        print("Авторизация есть, показываем страницу")
        return view_func(request, *args, **kwargs)

    return wrapper









# ВСЕ СТРАНИЦЫ

@login_required
def index(request):
    user = Open1.objects.get(id=request.session['user_id'])
    return render(request, 'blog/index.html', {'user': user})


def open_2(request):
    user = request.session.get('user', {})
    return render(request, 'blog/Вход_2.html', {'user': user})


@login_required
def home(request):
    user = Open1.objects.get(id=request.session['user_id'])
    return render(request, 'blog/Главная страница.html', {'user': user})

@login_required
def profile(request):
    """Защищенная страница — только для авторизованных"""
    user = Open3.objects.get(id=request.session['user_id'])
    return render(request, 'blog/ЛК.html', {'user': user})


@login_required
def form_1(request):
    user = Open1.objects.get(id=request.session['user_id'])
    return render(request, 'blog/Форма_1.html', {'user': user})

@login_required
def form_2(request):
    user = Open1.objects.get(id=request.session['user_id'])
    return render(request, 'blog/Форма_2.html', {'user': user})

@login_required
def profile_test(request):
    user = Open1.objects.get(id=request.session['user_id'])
    return render(request, 'blog/ЛК_тест.html', {'user': user})








def logout_view(request):
    request.session.flush()
    return redirect('open_1')