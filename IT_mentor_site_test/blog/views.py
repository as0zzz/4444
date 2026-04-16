from django.shortcuts import render, redirect
import requests
import json
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from .models import (
    Users, Mentors, Interns, Emails_workers,
    Open1, Open3, Event, Review,
    Chat, ChatAttachment, ChatMessage, ChatParticipant
)
from django.contrib import messages
from .forms import ProfileForm, EventForm
from django.templatetags.static import static
from django.db.models import Q

import mimetypes
import os

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth import logout

from django.contrib import messages

from django.db.models import Avg
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@require_POST
def submit_review(request):

    # 1. Проверяем, авторизован ли пользователь
    reviewer_email = request.session.get('user_email')
    if not reviewer_email:
        return JsonResponse({'status': 'error', 'message': 'Вы не авторизованы'}, status=401)
    
    try:
        # Читаем данные, которые прислал JavaScript
        data = json.loads(request.body)
        score = data.get('score')
        comment = data.get('comment')
        target_email = data.get('target_email') # Кого мы оцениваем
        
        # 2. Базовая защита (валидация)
        if not target_email:
            return JsonResponse({'status': 'error', 'message': 'Не указан пользователь для оценки'}, status=400)
            
        if not score or not isinstance(score, int) or not (1 <= score <= 10):
            return JsonResponse({'status': 'error', 'message': 'Оценка должна быть числом от 1 до 10'}, status=400)

        # 3. Сохраняем отзыв в базу данных
        Review.objects.create(
            reviewer_email=reviewer_email,
            target_email=target_email,
            score=score,
            comment=comment
        )

        print(f"✅ Успешно сохранена оценка {score} для {target_email}")

        # (В будущем здесь мы добавим код для пересчета среднего рейтинга target_email)

        return JsonResponse({'status': 'success'})
    except Exception as e:
        print(f"❌ Ошибка при сохранении отзыва: {e}")
        return JsonResponse({'status': 'error', 'message': 'Внутренняя ошибка сервера'}, status=500)
    

def open_1(request):
    print("ФУНКЦИЯ open_1 ВЫЗВАНА")
    print("Метод запроса:", request.method)

    if request.method == 'POST':
        data = {k.lower(): v for k, v in request.POST.items()}
        email = data.get('email')
        password = data.get('pa')

        print(f"Извлечено: email={email}, password={password}")
        # Проверка среди менторов
        try:
            user = Mentors.objects.get(email=email, password=password)
            request.session['user_id'] = user.id
            request.session['role'] = 'mentor'
            request.session['user_email'] = user.email
            request.session['is_authenticated'] = True
            ensure_open1_and_open3(user.email, user.name, user.patronymic, user.surname, user.phone, role='mentor')
            return redirect('home')
        except Mentors.DoesNotExist:
            pass
        # Проверка среди практикантов
        try:
            user = Interns.objects.get(email=email, password=password)
            request.session['user_id'] = user.id
            request.session['role'] = 'intern'
            request.session['user_email'] = user.email
            request.session['is_authenticated'] = True
            ensure_open1_and_open3(user.email, user.name, user.patronymic, user.surname, user.phone, role='intern')
            return redirect('home')
        except Interns.DoesNotExist:
            pass
        return render(request, 'blog/Вход_1.html', {'error': 'Неверные данные'})
    return render(request, 'blog/Вход_1.html')








def open_3(request):
    role = request.GET.get('role')
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

        print(f"Получены данные: {email}, {password}")

        if password != confirm:
            return render(request, 'blog/Вход_3.html', {'error': 'Пароли не совпадают', 'role': role})

        if role == 'mentor':
            if not Emails_workers.objects.filter(email=email).exists():
                return render(request, 'blog/Вход_3.html', {
                    'error': 'Ваша почта не найдена в списке допустимых. Регистрация ментора возможна только для корпоративных адресов.',
                    'role': role
                })

        if (Mentors.objects.filter(email=email).exists() or
            Interns.objects.filter(email=email).exists() or
            Users.objects.filter(email=email).exists()):
            return render(request, 'blog/Вход_3.html', {'error': 'Пользователь с таким email уже существует', 'role': role})

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
            request.session['user_email'] = email
            request.session['is_authenticated'] = True

            ensure_open1_and_open3(email, name, patronymic, surname, phone, role=role)

            return redirect('home')
            
        except Exception as e:
            return render(request, 'blog/Вход_3.html', {'error': f'Ошибка: {str(e)}', 'role': role})
    return render(request, 'blog/Вход_3.html', {'role': role})



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













#ЧАТ
CHAT_USER_AVATAR = static("images/1.png")


def get_current_open1_user(request):
    email = request.session.get('user_email')
    if not email:
        return None
    try:
        return Open1.objects.get(email=email)
    except Open1.DoesNotExist:
        return None


def get_open3_map_by_emails(emails):
    if not emails:
        return {}

    profiles = Open3.objects.filter(email__in=emails)
    return {profile.email: profile for profile in profiles}


def get_user_display_name(user, profile_map=None):
    profile_map = profile_map or {}
    profile = profile_map.get(user.email)

    if profile:
        full_name = " ".join(
            part for part in [profile.name, profile.surname] if part
        ).strip()
        if full_name:
            return full_name

    return user.email


def get_user_secondary_label(user, profile_map=None):
    profile_map = profile_map or {}
    profile = profile_map.get(user.email)

    if profile:
        full_name = " ".join(
            part for part in [profile.name, profile.surname] if part
        ).strip()
        if full_name and full_name != user.email:
            return user.email

    return "Пользователь платформы"


def get_user_message_label(user, profile_map=None):
    profile_map = profile_map or {}
    profile = profile_map.get(user.email)

    if profile:
        full_name = " ".join(
            part for part in [profile.surname, profile.name] if part
        ).strip()
        if full_name:
            return full_name

    return get_user_display_name(user, profile_map)


def is_mentor_chat_user(user):
    return bool(user and Mentors.objects.filter(email=user.email).exists())


def get_active_chat_participants(chat):
    return [
        participant
        for participant in chat.participants.all()
        if participant.is_active and not participant.is_hidden
    ]


def is_group_chat(chat):
    return bool(chat and chat.chat_type == Chat.CHAT_TYPE_GROUP)


def can_manage_chat(current_user, chat):
    return bool(
        current_user
        and chat
        and is_mentor_chat_user(current_user)
        and chat.created_by_id == current_user.id
    )


def get_chat_queryset_for_user(current_user):
    return (
        ChatParticipant.objects
        .filter(user=current_user, is_hidden=False)
        .select_related("chat", "user")
        .prefetch_related(
            "chat__messages__attachments",
            "chat__messages__sender",
            "chat__participants__user",
        )
        .order_by("-is_pinned", "-chat__updated_at", "-chat__created_at", "-chat__id")
    )


def get_unread_count_for_participant(participant, current_user):
    last_read_at = participant.last_read_at
    unread_count = 0

    for message in participant.chat.messages.all():
        if message.sender_id == current_user.id:
            continue
        if last_read_at and message.created_at <= last_read_at:
            continue
        unread_count += 1

    return unread_count


def serialize_attachment(attachment):
    content_type = attachment.content_type or mimetypes.guess_type(attachment.original_name)[0] or ""

    return {
        "id": attachment.id,
        "name": attachment.original_name,
        "url": attachment.file.url,
        "contentType": content_type,
        "size": attachment.size,
        "isImage": content_type.startswith("image/"),
    }


def serialize_message(message, current_user, participants, profile_map, show_sender_names=False):
    if message.message_type == ChatMessage.TYPE_SYSTEM:
        return {
            "id": message.id,
            "kind": "system",
            "text": message.text,
            "sentAt": message.created_at.isoformat(),
        }

    return {
        "id": message.id,
        "kind": "message",
        "type": "outgoing" if message.sender_id == current_user.id else "incoming",
        "text": message.text,
        "isForwarded": bool(message.forwarded_from_name),
        "forwardedFromName": message.forwarded_from_name,
        "sentAt": message.created_at.isoformat(),
        "edited": message.is_edited,
        "editedAt": message.edited_at.isoformat() if message.edited_at else None,
        "deleted": message.is_deleted,
        "read": is_message_read_for_current_user(message, current_user, participants),
        "senderDisplayName": (
            get_user_message_label(message.sender, profile_map)
            if show_sender_names and message.sender_id and message.sender_id != current_user.id and message.sender
            else ""
        ),
        "attachments": [serialize_attachment(item) for item in message.attachments.all()],
    }

def is_message_read_for_current_user(message, current_user, participants):
    current_participant = next(
        (
            item for item in participants
            if item.user_id == current_user.id and item.is_active and not item.is_hidden
        ),
        None
    )

    if not current_participant:
        return False

    if message.sender_id == current_user.id:
        other_participants = [
            item for item in participants
            if item.user_id != current_user.id and item.is_active and not item.is_hidden
        ]

        if not other_participants:
            return False

        return all(
            item.last_read_at and item.last_read_at >= message.created_at
            for item in other_participants
        )

    if not current_participant.last_read_at:
        return False

    return current_participant.last_read_at >= message.created_at

def serialize_chat(participant, current_user, profile_map):
    chat = participant.chat
    unread_count = get_unread_count_for_participant(participant, current_user)
    participants = list(chat.participants.all())
    active_participants = [
        item for item in participants
        if item.is_active and not item.is_hidden
    ]
    participant_count = len(active_participants)
    is_group = is_group_chat(chat)
    is_direct_chat = not is_group
    show_sender_names = is_group
    active_user_ids = [item.user_id for item in active_participants]
    other_participant = next(
        (item for item in active_participants if item.user_id != current_user.id),
        None,
    )

    if is_direct_chat and other_participant:
        title = get_user_display_name(other_participant.user, profile_map)
        subtitle = get_user_secondary_label(other_participant.user, profile_map)
    elif is_group:
        title = chat.title
        subtitle = f"Участников: {participant_count}"
    else:
        title = chat.title
        subtitle = chat.subtitle

    return {
        "id": chat.id,
        "title": title,
        "subtitle": subtitle,
        "unread": unread_count,
        "pinned": participant.is_pinned,
        "hidden": participant.is_hidden,
        "avatar": CHAT_USER_AVATAR,
        "participantCount": participant_count,
        "participantIds": active_user_ids,
        "isDirect": is_direct_chat,
        "isGroup": is_group,
        "showSenderNames": show_sender_names,
        "canManage": can_manage_chat(current_user, chat),
        "canAddMembers": can_manage_chat(current_user, chat) and is_group,
        "messages": [
            serialize_message(message, current_user, participants, profile_map, show_sender_names)
            for message in chat.messages.all()
        ],
    }


def get_chat_state_payload(current_user):
    participant_links = list(get_chat_queryset_for_user(current_user))
    emails = {current_user.email}

    for link in participant_links:
        for chat_participant in link.chat.participants.all():
            emails.add(chat_participant.user.email)

    profile_map = get_open3_map_by_emails(emails)
    chats = [serialize_chat(link, current_user, profile_map) for link in participant_links]
    unread_count = sum(chat["unread"] for chat in chats)

    return {
        "chats": chats,
        "unreadCount": unread_count,
    }


def get_chat_picker_payload(current_user):
    if not is_mentor_chat_user(current_user):
        return []

    intern_emails = Interns.objects.values_list("email", flat=True)
    users = list(
        Users.objects
        .filter(email__in=intern_emails)
        .exclude(id=current_user.id)
        .order_by("email")
    )
    profile_map = get_open3_map_by_emails([user.email for user in users])

    return [
        {
            "id": user.id,
            "name": get_user_display_name(user, profile_map),
            "role": get_user_secondary_label(user, profile_map),
            "avatar": CHAT_USER_AVATAR,
        }
        for user in users
    ]



def build_chat_response(current_user, **extra):
    payload = {
        "ok": True,
        **get_chat_state_payload(current_user),
    }
    payload.update(extra)
    return JsonResponse(payload)


def parse_request_json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def build_default_chat_title(selected_users, profile_map):
    if len(selected_users) == 1:
        user = selected_users[0]
        return (
            get_user_display_name(user, profile_map),
            get_user_secondary_label(user, profile_map),
        )

    first_names = []
    for user in selected_users:
        display_name = get_user_display_name(user, profile_map)
        first_names.append(display_name.split(" ")[0])

    return (
        f"Чат: {', '.join(first_names)}",
        f"Участников: {len(selected_users) + 1}",
    )


def create_system_message(chat, text, sender=None):
    message = ChatMessage.objects.create(
        chat=chat,
        sender=sender,
        message_type=ChatMessage.TYPE_SYSTEM,
        text=text,
    )
    chat.updated_at = timezone.now()
    chat.save(update_fields=["updated_at"])
    return message


def add_attachments_to_message(message, uploaded_files):
    for uploaded_file in uploaded_files:
        content_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or ""
        ChatAttachment.objects.create(
            message=message,
            file=uploaded_file,
            original_name=uploaded_file.name,
            content_type=content_type,
            size=uploaded_file.size or 0,
        )


def clone_attachments_to_message(source_message, target_message):
    for attachment in source_message.attachments.all():
        if not attachment.file:
            continue

        attachment.file.open("rb")
        try:
            file_bytes = attachment.file.read()
        finally:
            attachment.file.close()

        cloned_attachment = ChatAttachment(
            message=target_message,
            original_name=attachment.original_name,
            content_type=attachment.content_type,
            size=attachment.size,
        )
        cloned_attachment.file.save(
            os.path.basename(attachment.file.name) or attachment.original_name,
            ContentFile(file_bytes),
            save=True,
        )







# ВСЕ СТРАНИЦЫ

@login_required
def index(request):
    user = get_current_open1_user(request)
    return render(request, 'blog/index.html', {'user': user})

def open_2(request):
    user = request.session.get('user', {})
    return render(request, 'blog/Вход_2.html', {'user': user})
    

@login_required
def home(request):
    user = get_current_open1_user(request)

    if not user:
        email = request.session.get('user_email')
        if email:
            user, _ = Open1.objects.get_or_create(email=email)
        else:
            return redirect('open_1')

    # 2. Ранний код
    events = Event.objects.all() # все мероприятия
    events_list = []
    for event in events:
        events_list.append({
            'id': event.id,
            'image': event.image.url if event.image else '/static/images/4.png',
            'title': event.event_name,
            'filters': {
                'direction': 'events',
                'language': event.language if hasattr(event, 'language') else 'russian',
                'organization': event.organization_of_work,
                'field': event.field_of_work,
            }
        })

    # 3. Мой код с рейтингом
    all_specialists = Open3.objects.all()
    specialists_data = []
    
    for spec in all_specialists:
        avg_rating = Review.objects.filter(target_email=spec.email).aggregate(Avg('score'))['score__avg']
        display_rating = round(avg_rating, 1) if avg_rating is not None else 0.0
        
        specialists_data.append({
            'name': spec.name,
            'surname': spec.surname,
            'initial': spec.name[0] if spec.name else '?',
            'rating': display_rating,
            'email': spec.email
        })
    
    top_specialists = sorted(specialists_data, key=lambda x: x['rating'], reverse=True)[:8]

    # 4. ОБЩИЙ РЕНДЕР (склеили его events_json и наши top_specialists)
    return render(request, 'blog/Главная страница.html', {
        'user': user,
        'events_json': events_list,
        'top_specialists': top_specialists
    })

@login_required
def profile(request):
    """Защищенная страница — только для авторизованных"""
    try:
        user = Open3.objects.get(email=request.session['user_email'])
        role = request.session.get('role')
        return render(request, 'blog/ЛК.html', {'user': user, 'role': role})
    except Open3.DoesNotExist:
        return redirect('home')

@login_required
def chat_page(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return redirect('home')
    chat_state = get_chat_state_payload(current_user)
    context = {
        'chat_unread_count': chat_state["unreadCount"],
        'chat_bootstrap': chat_state["chats"],
        'chat_picker_users': get_chat_picker_payload(current_user),
        'chat_current_user': {
            'role': request.session.get('role', ''),
            'isMentor': is_mentor_chat_user(current_user),
        },
    }
    return render(request, 'blog/chat.html', context)


@login_required
def form_1(request, event_id=None):
    if event_id is None:
        user = get_current_open1_user(request)
        return render(request, 'blog/Форма_1.html', {'user': user})

    try:
        event = Event.objects.get(id=event_id)
        role = request.session.get('role')
        return render(request, 'blog/Форма_1.html', {'event': event, 'role': role})
    except Event.DoesNotExist:
        return redirect('home')

    

@login_required
def form_2(request):
    print("=== FORM_2 ВЫЗВАН ===")
    print("Метод:", request.method)
    print("POST данные:", request.POST)
    user = get_current_users_user(request)

    if not user:
        return redirect('home')

    if request.method == 'POST':
        event = Event.objects.create(
            user=user,                        
            event_name=request.POST.get('event_name'),
            event_phone=request.POST.get('event_phone'),
            event_email=request.POST.get('event_email'),
            fio=request.POST.get('fio'),
            field_of_work=request.POST.get('field_of_work'),
            organization_of_work=request.POST.get('organization_of_work'),
            event_description=request.POST.get('event_description'),
            language='russian',
            image=request.FILES.get('event_image')
        )

        return redirect('home')  # или другую страницу

    return render(request, 'blog/Форма_2.html')

@login_required
def form_3(request, event_id):
    user = get_current_users_user(request)
    if not user:
        return redirect('home')

    try:
        # event = Event.objects.get(id=event_id, user_id=user_id)
        event = Event.objects.get(id=event_id, user=user)
    except Event.DoesNotExist:
        return redirect('home')

    if request.method == 'POST':
        event.event_name = request.POST.get('event_name')
        event.event_phone = request.POST.get('event_phone')
        event.event_email = request.POST.get('event_email')
        event.fio = request.POST.get('fio')
        event.field_of_work = request.POST.get('field_of_work')
        event.organization_of_work = request.POST.get('organization_of_work')
        event.event_description = request.POST.get('event_description')
        if request.FILES.get('event_image'):
            event.image = request.FILES['event_image']
        event.save()
        return redirect('form_1', event_id=event.id)  # ← возврат на просмотр

    return render(request, 'blog/Форма_3.html', {'event': event})

@login_required
def profile_test(request):
    # 1. Проверяем, есть ли email в URL (например: ?email=test_mentor@mail.com)
    target_email = request.GET.get('email')
    
    # 2. Получаем текущего авторизованного пользователя (для шапки сайта)
    current_user = get_current_open1_user(request)

    if target_email:
        # Если кликнули из рейтинга — ищем данные этого специалиста
        try:
            # Ищем в Open3, так как там лежат Имя, Фамилия, Телефон и т.д.
            profile_data = Open3.objects.get(email=target_email)
        except Open3.DoesNotExist:
            # Если кто-то ввел кривую ссылку, просто возвращаем на главную
            return redirect('home')
    else:
        # Если просто нажали кнопку "Профиль" в шапке сайта — показываем свои данные
        try:
            profile_data = Open3.objects.get(email=request.session['user_email'])
        except Open3.DoesNotExist:
            # Если профиль в Open3 еще не заполнен
            profile_data = current_user

    # Передаем profile_data под ключом 'user', чтобы твой HTML шаблон (ЛК_тест.html) 
    # ничего не заметил и продолжал выводить {{ user.name }}, {{ user.surname }} и т.д.
    return render(request, 'blog/ЛК.html', {
        'user': profile_data,
        'current_user': current_user
    })


@login_required
def edit_profile(request):
    # Получаем профиль текущего пользователя
    user = get_current_open1_user(request)
    profile = user.profile if hasattr(user, 'profile') else None

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('form_1')  # страница просмотра
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'Форма_2.html', {'form': form})


@login_required
def view_profile(request):
    user = get_current_open1_user(request)
    profile = user.profile if hasattr(user, 'profile') else None

    return render(request, 'Форма_1.html', {
        'user': user,
        'profile': profile,
    })



def create_event(request):
    return form_2(request)


@login_required
def delete_event(request, event_id):
    user = get_current_users_user(request)
    if not user:
        return redirect('open_1')

    try:
        event = Event.objects.get(id=event_id, user=user)
        event.delete()
    except Event.DoesNotExist:
        pass

    return redirect('home')




@login_required
@require_POST
def chat_open_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    chat_id = payload.get("chat_id")

    participant = get_object_or_404(
        ChatParticipant,
        chat_id=chat_id,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )
    participant.last_read_at = timezone.now()
    participant.save(update_fields=["last_read_at"])

    return build_chat_response(current_user, activeChatId=participant.chat_id)


@login_required
@require_POST
def chat_create_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    if not is_mentor_chat_user(current_user):
        return JsonResponse({"ok": False, "error": "Создавать чаты может только ментор."}, status=403)
    payload = parse_request_json(request)
    participant_ids = payload.get("participant_ids") or []

    try:
        participant_ids = sorted({int(item) for item in participant_ids if int(item) != current_user.id})
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Некорректный список участников."}, status=400)

    if not participant_ids:
        return JsonResponse({"ok": False, "error": "Выберите хотя бы одного участника."}, status=400)

    intern_emails = Interns.objects.values_list("email", flat=True)
    selected_users = list(
        Users.objects
        .filter(id__in=participant_ids, email__in=intern_emails)
        .order_by("id")
    )
    if len(selected_users) != len(participant_ids):
        return JsonResponse({"ok": False, "error": "Можно добавлять только существующих стажёров."}, status=404)

    emails = [user.email for user in selected_users] + [current_user.email]
    profile_map = get_open3_map_by_emails(emails)
    title, subtitle = build_default_chat_title(selected_users, profile_map)

    with transaction.atomic():
        chat = Chat.objects.create(
            title=title,
            subtitle=subtitle,
            chat_type=Chat.CHAT_TYPE_DIRECT if len(selected_users) == 1 else Chat.CHAT_TYPE_GROUP,
            created_by=current_user,
        )

        ChatParticipant.objects.create(
            chat=chat,
            user=current_user,
            last_read_at=timezone.now(),
        )

        ChatParticipant.objects.bulk_create([
            ChatParticipant(chat=chat, user=user)
            for user in selected_users
        ])

        if len(selected_users) > 1:
            create_system_message(chat, f"Ментор создал группу «{title}»", sender=current_user)

    return build_chat_response(current_user, activeChatId=chat.id)


@login_required
@require_POST
def chat_send_message_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    chat_id = request.POST.get("chat_id")
    text = (request.POST.get("text") or "").strip()
    uploaded_files = request.FILES.getlist("attachments")

    if not chat_id:
        return JsonResponse({"ok": False, "error": "Чат не указан."}, status=400)

    participant = get_object_or_404(
        ChatParticipant,
        chat_id=chat_id,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )

    if not text and not uploaded_files:
        return JsonResponse({"ok": False, "error": "Сообщение пустое."}, status=400)

    if len(uploaded_files) > 10:
        return JsonResponse(
            {"ok": False, "error": "К одному сообщению можно прикрепить максимум 10 файлов."},
            status=400,
        )

    with transaction.atomic():
        message = ChatMessage.objects.create(
            chat=participant.chat,
            sender=current_user,
            message_type=ChatMessage.TYPE_USER,
            text=text,
        )
        add_attachments_to_message(message, uploaded_files)
        participant.chat.updated_at = timezone.now()
        participant.chat.save(update_fields=["updated_at"])
        ChatParticipant.objects.filter(chat=participant.chat, user=current_user).update(last_read_at=timezone.now())

    return build_chat_response(current_user, activeChatId=participant.chat_id)


@login_required
@require_POST
def chat_toggle_pin_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    chat_id = payload.get("chat_id")

    participant = get_object_or_404(
        ChatParticipant,
        chat_id=chat_id,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )
    participant.is_pinned = not participant.is_pinned
    participant.save(update_fields=["is_pinned"])

    return build_chat_response(current_user, activeChatId=participant.chat_id)


@login_required
@require_POST
def chat_rename_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    chat_id = payload.get("chat_id")
    title = (payload.get("title") or "").strip()

    if not title:
        return JsonResponse({"ok": False, "error": "Введите новое название чата."}, status=400)

    participant = get_object_or_404(
        ChatParticipant,
        chat_id=chat_id,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )
    if not can_manage_chat(current_user, participant.chat):
        return JsonResponse({"ok": False, "error": "Переименовывать чат может только ментор."}, status=403)

    participant.chat.title = title
    participant.chat.updated_at = timezone.now()
    participant.chat.save(update_fields=["title", "updated_at"])

    return build_chat_response(current_user, activeChatId=participant.chat_id)


@login_required
@require_POST
def chat_add_participants_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    chat_id = payload.get("chat_id")
    participant_ids = payload.get("participant_ids") or []

    try:
        participant_ids = sorted({int(item) for item in participant_ids if int(item) != current_user.id})
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Некорректный список участников."}, status=400)

    if not participant_ids:
        return JsonResponse({"ok": False, "error": "Выберите хотя бы одного стажёра."}, status=400)

    participant = get_object_or_404(
        ChatParticipant,
        chat_id=chat_id,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )
    if not can_manage_chat(current_user, participant.chat):
        return JsonResponse({"ok": False, "error": "Добавлять в чат может только ментор."}, status=403)

    if not is_group_chat(participant.chat):
        return JsonResponse({"ok": False, "error": "Добавлять участников можно только в группу."}, status=400)

    intern_emails = Interns.objects.values_list("email", flat=True)
    selected_users = list(
        Users.objects
        .filter(id__in=participant_ids, email__in=intern_emails)
        .order_by("id")
    )
    if len(selected_users) != len(participant_ids):
        return JsonResponse({"ok": False, "error": "Можно добавлять только существующих стажёров."}, status=404)

    existing_links = {
        item.user_id: item
        for item in ChatParticipant.objects.filter(chat=participant.chat, user_id__in=participant_ids)
    }
    added_users = []

    with transaction.atomic():
        for user in selected_users:
            existing_link = existing_links.get(user.id)

            if existing_link:
                if existing_link.is_active and not existing_link.is_hidden:
                    continue

                existing_link.is_hidden = False
                existing_link.is_active = True
                existing_link.is_pinned = False
                existing_link.save(update_fields=["is_hidden", "is_active", "is_pinned"])
            else:
                ChatParticipant.objects.create(chat=participant.chat, user=user)

            added_users.append(user)

        if added_users:
            profile_map = get_open3_map_by_emails([item.email for item in added_users])
            added_names = ", ".join(
                get_user_display_name(item, profile_map)
                for item in added_users
            )
            create_system_message(participant.chat, f"Ментор добавил в чат: {added_names}", sender=current_user)
        else:
            participant.chat.updated_at = timezone.now()
            participant.chat.save(update_fields=["updated_at"])

    return build_chat_response(current_user, activeChatId=participant.chat_id)


@login_required
@require_POST
def chat_update_message_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    message_id = payload.get("message_id")
    text = (payload.get("text") or "").strip()

    if not text:
        return JsonResponse({"ok": False, "error": "Текст сообщения пустой."}, status=400)

    message = get_object_or_404(
        ChatMessage,
        id=message_id,
        sender=current_user,
        message_type=ChatMessage.TYPE_USER,
        is_deleted=False,
    )

    if message.text == text:
        return build_chat_response(current_user, activeChatId=message.chat_id)

    with transaction.atomic():
        message.text = text
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save(update_fields=["text", "is_edited", "edited_at"])

        message.chat.updated_at = timezone.now()
        message.chat.save(update_fields=["updated_at"])
        ChatParticipant.objects.filter(chat=message.chat, user=current_user).update(last_read_at=timezone.now())

    return build_chat_response(current_user, activeChatId=message.chat_id)


@login_required
@require_POST
def chat_delete_message_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    message_id = payload.get("message_id")

    message = get_object_or_404(
        ChatMessage,
        id=message_id,
        sender=current_user,
        message_type=ChatMessage.TYPE_USER,
        is_deleted=False,
    )

    chat_id = message.chat_id

    with transaction.atomic():
        for attachment in message.attachments.all():
            if attachment.file:
                attachment.file.delete(save=False)

        message.delete()
        message.chat.updated_at = timezone.now()
        message.chat.save(update_fields=["updated_at"])
        ChatParticipant.objects.filter(chat_id=chat_id, user=current_user).update(last_read_at=timezone.now())

    return build_chat_response(current_user, activeChatId=chat_id)


@login_required
@require_POST
def chat_forward_message_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    message_id = payload.get("message_id")
    target_chat_id = payload.get("target_chat_id")

    source_message = get_object_or_404(
        ChatMessage.objects.prefetch_related("attachments"),
        id=message_id,
        message_type=ChatMessage.TYPE_USER,
        is_deleted=False,
    )

    get_object_or_404(
        ChatParticipant,
        chat=source_message.chat,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )
    target_participant = get_object_or_404(
        ChatParticipant,
        chat_id=target_chat_id,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )

    if source_message.chat_id == target_participant.chat_id:
        return JsonResponse({"ok": False, "error": "Нельзя переслать сообщение в этот же чат."}, status=400)

    forwarded_from_name = ""
    if source_message.sender:
        forwarded_from_name = get_user_message_label(
            source_message.sender,
            get_open3_map_by_emails([source_message.sender.email]),
        )

    with transaction.atomic():
        forwarded_message = ChatMessage.objects.create(
            chat=target_participant.chat,
            sender=current_user,
            message_type=ChatMessage.TYPE_USER,
            text=source_message.text,
            forwarded_from_name=forwarded_from_name,
        )
        clone_attachments_to_message(source_message, forwarded_message)
        target_participant.chat.updated_at = timezone.now()
        target_participant.chat.save(update_fields=["updated_at"])
        ChatParticipant.objects.filter(
            chat=target_participant.chat,
            user=current_user,
        ).update(last_read_at=timezone.now())

    return build_chat_response(current_user, activeChatId=target_participant.chat_id)


@login_required
@require_POST
def chat_delete_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    chat_id = payload.get("chat_id")

    participant = get_object_or_404(
        ChatParticipant,
        chat_id=chat_id,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )

    display_name = get_user_display_name(
        current_user,
        get_open3_map_by_emails([current_user.email])
    )

    chat = participant.chat

    with transaction.atomic():
        participant.is_hidden = True
        participant.is_active = False
        participant.is_pinned = False
        participant.last_read_at = timezone.now()
        participant.save(update_fields=["is_hidden", "is_active", "is_pinned", "last_read_at"])

        has_active_participants = ChatParticipant.objects.filter(
            chat=chat,
            is_active=True,
            is_hidden=False,
        ).exists()

        if has_active_participants:
            create_system_message(chat, f"{display_name} вышел из чата", sender=current_user)
        else:
            for attachment in ChatAttachment.objects.filter(message__chat=chat):
                if attachment.file:
                    attachment.file.delete(save=False)

            chat.delete()

    return build_chat_response(current_user)

def get_current_user(request):
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

def get_current_open3_user(request):
    email = request.session.get('user_email')
    if not email:
        return None
    try:
        return Open3.objects.get(email=email)
    except Open3.DoesNotExist:
        return None

def ensure_open1_and_open3(email, name="", patronymic="", surname="", phone="", role="intern"):
    """Создаёт/получает Open1, Open3, Users для совместимости."""
    open1, _ = Open1.objects.get_or_create(email=email, defaults={'pa': ''})
    open3, _ = Open3.objects.get_or_create(
        email=email,
        defaults={
            'name': name,
            'patronymic': patronymic,
            'surname': surname,
            'phone': phone,
            'pa': ''
        }
    )
    Users.objects.get_or_create(email=email, defaults={'role': role})
    return open1, open3

def get_current_users_user(request):
    email = request.session.get('user_email')
    if not email:
        return None
    role = request.session.get('role', 'intern')
    user, _ = Users.objects.get_or_create(email=email, defaults={'role': role})
    return user


def logout_view(request):
    request.session.flush()
    return redirect('open_1')


@login_required
def test_review_page(request):
    # Получаем всех специалистов из базы данных
    specialists = Open3.objects.all()
    
    # Передаем их в шаблон под ключом 'specialists'
    return render(request, 'blog/Оценка.html', {'specialists': specialists})
