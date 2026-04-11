from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import logout
from .models import Users, Mentors, Interns, Emails_workers


def get_current_user(request):
    """Возвращает объект пользователя (Mentors или Interns) по данным сессии."""
    user_id = request.session.get('user_id')
    role = request.session.get('role')
    if not user_id or not role:
        return None
    if role == 'mentor':
        try:
            return Mentors.objects.get(id=user_id)
        except Mentors.DoesNotExist:
            return None
    elif role == 'intern':
        try:
            return Interns.objects.get(id=user_id)
        except Interns.DoesNotExist:
            return None
    return None


def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_authenticated'):
            return redirect('open_1')
        return view_func(request, *args, **kwargs)
    return wrapper


def open_1(request):
    if request.method == 'POST':
        # Нормализуем ключи (Email → email, Pa → password)
        data = {k.lower(): v for k, v in request.POST.items()}
        email = data.get('email')
        password = data.get('pa')   # поле в форме называется "Pa"

        # Проверяем среди менторов
        try:
            user = Mentors.objects.get(email=email, password=password)
            request.session['user_id'] = user.id
            request.session['role'] = 'mentor'
            request.session['is_authenticated'] = True
            return redirect('home')
        except Mentors.DoesNotExist:
            pass

        # Проверяем среди практикантов
        try:
            user = Interns.objects.get(email=email, password=password)
            request.session['user_id'] = user.id
            request.session['role'] = 'intern'
            request.session['is_authenticated'] = True
            return redirect('home')
        except Interns.DoesNotExist:
            pass

        # Если не найден
        return render(request, 'blog/Вход_1.html', {'error': 'Неверные данные'})

    return render(request, 'blog/Вход_1.html')


def open_2(request):

    return render(request, 'blog/Вход_2.html')


def open_3(request):
    role = request.GET.get('role')   # 'mentor' или 'intern'
    if not role or role not in ['mentor', 'intern']:
        return redirect('open_2')

    role_map = {'mentor': 'ментор', 'intern': 'практикант'}
    role_ru = role_map.get(role)

    if request.method == 'POST':
        email = request.POST.get('email')
        name = request.POST.get('name')
        patronymic = request.POST.get('patronymic')
        surname = request.POST.get('surname')
        phone = request.POST.get('phone')
        password = request.POST.get('pa')
        confirm = request.POST.get('confirm')

        if password != confirm:
            return render(request, 'blog/Вход_3.html', {'error': 'Пароли не совпадают', 'role': role})

        # --- НОВАЯ ПРОВЕРКА ДЛЯ МЕНТОРА ---
        if role == 'mentor':
            if not Emails_workers.objects.filter(email=email).exists():
                return render(request, 'blog/Вход_3.html', {
                    'error': 'Ваша почта не найдена в списке допустимых. Регистрация ментора возможна только для корпоративных адресов.',
                    'role': role
                })


        # Проверка существования email в любой из трёх таблиц
        if (Mentors.objects.filter(email=email).exists() or
            Interns.objects.filter(email=email).exists() or
            Users.objects.filter(email=email).exists()):
            return render(request, 'blog/Вход_3.html', {'error': 'Пользователь с таким email уже существует', 'role': role})

        # Создание профиля
        Model = Mentors if role == 'mentor' else Interns
        try:
            new_profile = Model.objects.create(
                email=email,
                name=name,
                patronymic=patronymic or '',
                surname=surname,
                phone=phone,
                password=password
            )
            Users.objects.create(email=email, role=role_ru)

            request.session['user_id'] = new_profile.id
            request.session['role'] = role
            request.session['is_authenticated'] = True
            return redirect('home')
        except Exception as e:
            return render(request, 'blog/Вход_3.html', {'error': f'Ошибка: {str(e)}', 'role': role})

    return render(request, 'blog/Вход_3.html', {'role': role})


@login_required
def home(request):
    user = get_current_user(request)
    return render(request, 'blog/Главная страница.html', {'user': user})

@login_required
def profile(request):
    user = get_current_user(request)
    role = request.session.get('role')  # 'mentor' или 'intern'
    return render(request, 'blog/ЛК.html', {'user': user, 'role': role})

@login_required
def form_1(request):
    user = get_current_user(request)
    role = request.session.get('role')  # 'mentor' или 'intern'
    return render(request, 'blog/Форма_1.html', {'user': user, 'role': role})

@login_required
def form_2(request):
    user = get_current_user(request)
    return render(request, 'blog/Форма_2.html', {'user': user})

@login_required
def profile_test(request):
    user = get_current_user(request)
    return render(request, 'blog/ЛК_тест.html', {'user': user})



def logout_view(request):
    request.session.flush()
    return redirect('open_1')



def index(request):
    return redirect('open_1')