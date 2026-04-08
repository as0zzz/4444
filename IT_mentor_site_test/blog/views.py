import json
import mimetypes

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_POST

import requests
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .models import (
    Chat,
    ChatAttachment,
    ChatMessage,
    ChatParticipant,
    Open1,
    Open3,
)
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
            expects_json = (
                request.path.startswith('/chat/api/')
                or request.headers.get('x-requested-with') == 'XMLHttpRequest'
                or 'application/json' in request.headers.get('Accept', '')
            )

            if expects_json:
                return JsonResponse({
                    "ok": False,
                    "error": "Сессия истекла. Войдите снова.",
                    "code": "AUTH_REQUIRED",
                    "redirect": "/open_1/",
                }, status=401)

            return redirect('open_1')

        print("Авторизация есть, показываем страницу")
        return view_func(request, *args, **kwargs)

    return wrapper


CHAT_USER_AVATAR = static("images/1.png")


def get_current_open1_user(request):
    return Open1.objects.get(id=request.session["user_id"])


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


def serialize_message(message, current_user):
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
        "sentAt": message.created_at.isoformat(),
        "edited": message.is_edited,
        "editedAt": message.edited_at.isoformat() if message.edited_at else None,
        "deleted": message.is_deleted,
        "attachments": [serialize_attachment(item) for item in message.attachments.all()],
    }


def serialize_chat(participant, current_user, profile_map):
    chat = participant.chat
    unread_count = get_unread_count_for_participant(participant, current_user)

    return {
        "id": chat.id,
        "title": chat.title,
        "subtitle": chat.subtitle,
        "unread": unread_count,
        "pinned": participant.is_pinned,
        "hidden": participant.is_hidden,
        "avatar": CHAT_USER_AVATAR,
        "messages": [serialize_message(message, current_user) for message in chat.messages.all()],
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
    users = list(Open1.objects.exclude(id=current_user.id).order_by("email"))
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


def get_unread_chat_count_for_user(current_user):
    return get_chat_state_payload(current_user)["unreadCount"]


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
    return render(request, 'blog/Главная страница.html', {
        'user': user,
        'chat_unread_count': get_unread_chat_count_for_user(user),
    })

@login_required
def profile(request):
    """Защищенная страница — только для авторизованных"""
    auth_user = get_current_open1_user(request)
    user = Open3.objects.filter(email=auth_user.email).first()

    return render(request, 'blog/ЛК.html', {
        'user': user or auth_user,
        'chat_unread_count': get_unread_chat_count_for_user(auth_user),
    })

@login_required
def chat_page(request):
    user = get_current_open1_user(request)
    chat_state = get_chat_state_payload(user)
    context = {
        'chat_unread_count': chat_state["unreadCount"],
        'chat_bootstrap': chat_state["chats"],
        'chat_picker_users': get_chat_picker_payload(user),
    }
    return render(request, 'blog/chat.html', context)

@login_required
def form_1(request):
    user = get_current_open1_user(request)
    return render(request, 'blog/Форма_1.html', {'user': user})

@login_required
def form_2(request):
    user = get_current_open1_user(request)
    return render(request, 'blog/Форма_2.html', {'user': user})

@login_required
def profile_test(request):
    user = get_current_open1_user(request)
    return render(request, 'blog/ЛК_тест.html', {'user': user})


@login_required
@require_POST
def chat_open_api(request):
    current_user = get_current_open1_user(request)
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
    current_user = get_current_open1_user(request)
    payload = parse_request_json(request)
    participant_ids = payload.get("participant_ids") or []

    try:
        participant_ids = sorted({int(item) for item in participant_ids if int(item) != current_user.id})
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Некорректный список участников."}, status=400)

    if not participant_ids:
        return JsonResponse({"ok": False, "error": "Выберите хотя бы одного участника."}, status=400)

    selected_users = list(Open1.objects.filter(id__in=participant_ids).order_by("id"))
    if len(selected_users) != len(participant_ids):
        return JsonResponse({"ok": False, "error": "Некоторые участники не найдены."}, status=404)

    emails = [user.email for user in selected_users] + [current_user.email]
    profile_map = get_open3_map_by_emails(emails)
    title, subtitle = build_default_chat_title(selected_users, profile_map)

    with transaction.atomic():
        chat = Chat.objects.create(
            title=title,
            subtitle=subtitle,
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

        create_system_message(chat, f"Ментор создал группу «{title}»", sender=current_user)

    return build_chat_response(current_user, activeChatId=chat.id)


@login_required
@require_POST
def chat_send_message_api(request):
    current_user = get_current_open1_user(request)
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
    current_user = get_current_open1_user(request)
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
    current_user = get_current_open1_user(request)
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

    participant.chat.title = title
    participant.chat.updated_at = timezone.now()
    participant.chat.save(update_fields=["title", "updated_at"])

    return build_chat_response(current_user, activeChatId=participant.chat_id)


@login_required
@require_POST
def chat_delete_api(request):
    current_user = get_current_open1_user(request)
    payload = parse_request_json(request)
    chat_id = payload.get("chat_id")

    participant = get_object_or_404(
        ChatParticipant,
        chat_id=chat_id,
        user=current_user,
        is_hidden=False,
        is_active=True,
    )

    display_name = get_user_display_name(current_user, get_open3_map_by_emails([current_user.email]))

    with transaction.atomic():
        create_system_message(participant.chat, f"{display_name} вышел из чата", sender=current_user)
        participant.is_hidden = True
        participant.is_active = False
        participant.is_pinned = False
        participant.last_read_at = timezone.now()
        participant.save(update_fields=["is_hidden", "is_active", "is_pinned", "last_read_at"])

    return build_chat_response(current_user)


@login_required
@require_POST
def chat_update_message_api(request):
    current_user = get_current_open1_user(request)
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
    current_user = get_current_open1_user(request)
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
def chat_delete_api(request):
    current_user = get_current_open1_user(request)
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









def logout_view(request):
    request.session.flush()
    return redirect('open_1')
