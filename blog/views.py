from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import logout
from django.contrib import messages
from django.templatetags.static import static
from django.db.models import Q, Avg
from django.db import transaction
from django.views.decorators.http import require_POST
from django.utils import timezone
import json
import mimetypes
import requests

from .models import (
    Users, Mentors, Interns, Emails_workers,
    Open1, Open3, Event, Review,
    Chat, ChatAttachment, ChatMessage, ChatParticipant
)
from .forms import ProfileForm, EventForm



def get_current_user(request):
    """Возвращает объект Mentors или Interns по данным сессии."""
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

def get_current_open1_user(request):
    """Возвращает объект Open1, соответствующий текущему авторизованному пользователю."""
    email = request.session.get('user_email')
    if not email:
        return None
    try:
        return Open1.objects.get(email=email)
    except Open1.DoesNotExist:
        return None

def get_current_open3_user(request):
    """Возвращает объект Open3, соответствующий текущему авторизованному пользователю."""
    email = request.session.get('user_email')
    if not email:
        return None
    try:
        return Open3.objects.get(email=email)
    except Open3.DoesNotExist:
        return None

def ensure_open1_and_open3(email, name="", patronymic="", surname="", phone=""):
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
    # Добавить создание Users
    role = 'mentor' if 'mentor' in str(open1) else 'intern'  # или передавать role параметром
    Users.objects.get_or_create(email=email, defaults={'role': role})
    return open1, open3



def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_authenticated'):
            return redirect('open_1')
        return view_func(request, *args, **kwargs)
    return wrapper



def open_1(request):
    if request.method == 'POST':
        data = {k.lower(): v for k, v in request.POST.items()}
        email = data.get('email')
        password = data.get('pa')

        # Проверка среди менторов
        try:
            user = Mentors.objects.get(email=email, password=password)
            request.session['user_id'] = user.id
            request.session['role'] = 'mentor'
            request.session['user_email'] = user.email
            request.session['is_authenticated'] = True
            ensure_open1_and_open3(user.email, user.name, user.patronymic, user.surname, user.phone)
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
            ensure_open1_and_open3(user.email, user.name, user.patronymic, user.surname, user.phone)
            return redirect('home')
        except Interns.DoesNotExist:
            pass

        return render(request, 'blog/Вход_1.html', {'error': 'Неверные данные'})

    return render(request, 'blog/Вход_1.html')

def open_2(request):
    return render(request, 'blog/Вход_2.html')

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

        if password != confirm:
            return render(request, 'blog/Вход_3.html', {'error': 'Пароли не совпадают', 'role': role})

        # Проверка для ментора
        if role == 'mentor':
            if not Emails_workers.objects.filter(email=email).exists():
                return render(request, 'blog/Вход_3.html', {
                    'error': 'Ваша почта не найдена в списке допустимых. Регистрация ментора возможна только для корпоративных адресов.',
                    'role': role
                })

        # Проверка уникальности email
        if (Mentors.objects.filter(email=email).exists() or
            Interns.objects.filter(email=email).exists() or
            Users.objects.filter(email=email).exists()):
            return render(request, 'blog/Вход_3.html', {'error': 'Пользователь с таким email уже существует', 'role': role})

        # Создание профиля (Mentors или Interns)
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

            # Автоматический вход
            request.session['user_id'] = new_profile.id
            request.session['role'] = role
            request.session['user_email'] = email
            request.session['is_authenticated'] = True


            ensure_open1_and_open3(email, name, patronymic, surname, phone)

            return redirect('home')
        except Exception as e:
            return render(request, 'blog/Вход_3.html', {'error': f'Ошибка: {str(e)}', 'role': role})

    return render(request, 'blog/Вход_3.html', {'role': role})


@login_required
def home(request):
    # Получаем пользователя из модели Users (для совместимости с чатом и мероприятиями)
    users_user = get_current_users_user(request)
    if not users_user:
        return redirect('open_1')

    # Мероприятия
    events = Event.objects.all()
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

    # Топ специалистов (из Open3)
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

    return render(request, 'blog/Главная страница.html', {
        'user': users_user,   # теперь передаём объект Users
        'events_json': events_list,
        'top_specialists': top_specialists
    })

@login_required
def profile(request):
    user = get_current_user(request)      # Mentors или Interns
    role = request.session.get('role')
    # Убедимся, что Open3 существует
    email = request.session.get('user_email')
    if email:
        ensure_open1_and_open3(email)
    return render(request, 'blog/ЛК.html', {'user': user, 'role': role})

@login_required
def form_1(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return redirect('home')
    role = request.session.get('role')
    return render(request, 'blog/Форма_1.html', {'event': event, 'role': role})

@login_required
def form_2(request):
    users_user = get_current_users_user(request)
    if not users_user:
        return redirect('home')

    if request.method == 'POST':
        event = Event.objects.create(
            user=users_user,   # теперь передаётся объект Users
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
        return redirect('home')
    return render(request, 'blog/Форма_2.html')

@login_required
def form_3(request, event_id):
    users_user = get_current_users_user(request)
    if not users_user:
        return redirect('home')

    try:
        event = Event.objects.get(id=event_id, user=users_user)  # проверка, что мероприятие принадлежит текущему пользователю
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
        return redirect('form_1', event_id=event.id)
    return render(request, 'blog/Форма_3.html', {'event': event})

@login_required
def delete_event(request, event_id):
    users_user = get_current_users_user(request)
    if not users_user:
        return redirect('open_1')
    try:
        event = Event.objects.get(id=event_id, user=users_user)
        event.delete()
    except Event.DoesNotExist:
        pass
    return redirect('home')

@login_required
def profile_test(request):
    user = get_current_user(request)
    return render(request, 'blog/ЛК_тест.html', {'user': user})



@require_POST
def submit_review(request):
    reviewer_email = request.session.get('user_email')
    if not reviewer_email:
        return JsonResponse({'status': 'error', 'message': 'Вы не авторизованы'}, status=401)

    try:
        data = json.loads(request.body)
        score = data.get('score')
        comment = data.get('comment')
        target_email = data.get('target_email')

        if not target_email:
            return JsonResponse({'status': 'error', 'message': 'Не указан пользователь для оценки'}, status=400)
        if not score or not isinstance(score, int) or not (1 <= score <= 10):
            return JsonResponse({'status': 'error', 'message': 'Оценка должна быть числом от 1 до 10'}, status=400)

        Review.objects.create(
            reviewer_email=reviewer_email,
            target_email=target_email,
            score=score,
            comment=comment
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



CHAT_USER_AVATAR = static("images/1.png")

def get_open3_map_by_emails(emails):
    if not emails:
        return {}
    profiles = Open3.objects.filter(email__in=emails)
    return {profile.email: profile for profile in profiles}

def get_user_display_name(user, profile_map=None):
    profile_map = profile_map or {}
    profile = profile_map.get(user.email)
    if profile:
        full_name = " ".join(part for part in [profile.name, profile.surname] if part).strip()
        if full_name:
            return full_name
    return user.email

def get_user_secondary_label(user, profile_map=None):
    profile_map = profile_map or {}
    profile = profile_map.get(user.email)
    if profile:
        full_name = " ".join(part for part in [profile.name, profile.surname] if part).strip()
        if full_name and full_name != user.email:
            return user.email
    return "Пользователь платформы"

def get_chat_queryset_for_user(current_user):
    return (ChatParticipant.objects.filter(user=current_user, is_hidden=False)
            .select_related("chat", "user")
            .prefetch_related("chat__messages__attachments", "chat__messages__sender", "chat__participants__user")
            .order_by("-is_pinned", "-chat__updated_at", "-chat__created_at", "-chat__id"))

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
    return {"chats": chats, "unreadCount": unread_count}

def get_chat_picker_payload(current_user):
    users = list(Users.objects.exclude(id=current_user.id).order_by("email"))
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
    payload = {"ok": True, **get_chat_state_payload(current_user)}
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
        return (get_user_display_name(user, profile_map), get_user_secondary_label(user, profile_map))
    first_names = []
    for user in selected_users:
        display_name = get_user_display_name(user, profile_map)
        first_names.append(display_name.split(" ")[0])
    return (f"Чат: {', '.join(first_names)}", f"Участников: {len(selected_users) + 1}")

def create_system_message(chat, text, sender=None):
    message = ChatMessage.objects.create(
        chat=chat, sender=sender, message_type=ChatMessage.TYPE_SYSTEM, text=text
    )
    chat.updated_at = timezone.now()
    chat.save(update_fields=["updated_at"])
    return message

def add_attachments_to_message(message, uploaded_files):
    for uploaded_file in uploaded_files:
        content_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or ""
        ChatAttachment.objects.create(
            message=message, file=uploaded_file, original_name=uploaded_file.name,
            content_type=content_type, size=uploaded_file.size or 0
        )

def get_current_users_user(request):
    email = request.session.get('user_email')
    if not email:
        return None
    role = request.session.get('role', 'intern')
    user, _ = Users.objects.get_or_create(email=email, defaults={'role': role})
    return user

# ---------- ЧАТ (исправлен для работы с Users) ----------

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
    }
    return render(request, 'blog/chat.html', context)

@login_required
@require_POST
def chat_open_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    chat_id = payload.get("chat_id")
    participant = get_object_or_404(ChatParticipant, chat_id=chat_id, user=current_user, is_hidden=False, is_active=True)
    participant.last_read_at = timezone.now()
    participant.save(update_fields=["last_read_at"])
    return build_chat_response(current_user, activeChatId=participant.chat_id)

@login_required
@require_POST
def chat_create_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    participant_ids = payload.get("participant_ids") or []
    try:
        participant_ids = sorted({int(item) for item in participant_ids if int(item) != current_user.id})
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Некорректный список участников."}, status=400)
    if not participant_ids:
        return JsonResponse({"ok": False, "error": "Выберите хотя бы одного участника."}, status=400)
    selected_users = list(Users.objects.filter(id__in=participant_ids).order_by("id"))
    if len(selected_users) != len(participant_ids):
        return JsonResponse({"ok": False, "error": "Некоторые участники не найдены."}, status=404)
    emails = [user.email for user in selected_users] + [current_user.email]
    profile_map = get_open3_map_by_emails(emails)
    title, subtitle = build_default_chat_title(selected_users, profile_map)
    with transaction.atomic():
        chat = Chat.objects.create(title=title, subtitle=subtitle, created_by=current_user)
        ChatParticipant.objects.create(chat=chat, user=current_user, last_read_at=timezone.now())
        ChatParticipant.objects.bulk_create([ChatParticipant(chat=chat, user=user) for user in selected_users])
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
    participant = get_object_or_404(ChatParticipant, chat_id=chat_id, user=current_user, is_hidden=False, is_active=True)
    if not text and not uploaded_files:
        return JsonResponse({"ok": False, "error": "Сообщение пустое."}, status=400)
    if len(uploaded_files) > 10:
        return JsonResponse({"ok": False, "error": "К одному сообщению можно прикрепить максимум 10 файлов."}, status=400)
    with transaction.atomic():
        message = ChatMessage.objects.create(chat=participant.chat, sender=current_user, message_type=ChatMessage.TYPE_USER, text=text)
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
    participant = get_object_or_404(ChatParticipant, chat_id=chat_id, user=current_user, is_hidden=False, is_active=True)
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
    participant = get_object_or_404(ChatParticipant, chat_id=chat_id, user=current_user, is_hidden=False, is_active=True)
    participant.chat.title = title
    participant.chat.updated_at = timezone.now()
    participant.chat.save(update_fields=["title", "updated_at"])
    return build_chat_response(current_user, activeChatId=participant.chat_id)

@login_required
@require_POST
def chat_delete_api(request):
    current_user = get_current_users_user(request)
    if not current_user:
        return JsonResponse({"ok": False, "error": "Не авторизован"}, status=401)
    payload = parse_request_json(request)
    chat_id = payload.get("chat_id")
    participant = get_object_or_404(ChatParticipant, chat_id=chat_id, user=current_user, is_hidden=False, is_active=True)
    display_name = get_user_display_name(current_user, get_open3_map_by_emails([current_user.email]))
    with transaction.atomic():
        create_system_message(participant.chat, f"{display_name} вышел из чата", sender=current_user)
        participant.is_hidden = True
        participant.is_active = False
        participant.is_pinned = False
        participant.last_read_at = timezone.now()
        participant.save(update_fields=["is_hidden", "is_active", "is_pinned", "last_read_at"])
    return build_chat_response(current_user)



def logout_view(request):
    request.session.flush()
    return redirect('open_1')

def index(request):
    return redirect('open_1')