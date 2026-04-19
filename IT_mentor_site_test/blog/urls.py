from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.open_1, name='open_1'),
    path('open_1/', views.open_1, name='open_1'),
    path('logout/', views.logout_view, name='logout'),  # Выход

    path('rating/', views.submit_review, name='review'),
    path('test-review/', views.test_review_page, name='test_review_page'),

    path('open_3/', views.open_3, name='open_3'),
    path('home/', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('chat/', views.chat_page, name='chat_page'),
    path('chat/api/open/', views.chat_open_api, name='chat_open_api'),
    path('chat/api/create/', views.chat_create_api, name='chat_create_api'),
    path('chat/api/send/', views.chat_send_message_api, name='chat_send_message_api'),
    path('chat/api/toggle-pin/', views.chat_toggle_pin_api, name='chat_toggle_pin_api'),
    path('chat/api/rename/', views.chat_rename_api, name='chat_rename_api'),
    path('chat/api/add-participants/', views.chat_add_participants_api, name='chat_add_participants_api'),
    path('chat/api/delete/', views.chat_delete_api, name='chat_delete_api'),
    path('chat/api/message/forward/', views.chat_forward_message_api, name='chat_forward_message_api'),
    path('chat/api/message/update/', views.chat_update_message_api, name='chat_update_message_api'),
    path('chat/api/message/delete/', views.chat_delete_message_api, name='chat_delete_message_api'),
    path('form_1/', views.form_1, name='form_1'),
    path('form_2/', views.form_2, name='form_2'),
    path('profile_test/', views.profile_test, name='profile_test'),
    path('event/<int:event_id>/', views.form_1, name='form_1'),
    path('form_3/<int:event_id>/', views.form_3, name='form_3'),
    path('verify_code/', views.verify_code, name='verify_code'),

    path('profile/view/', views.view_profile, name='view_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('event/create/', views.create_event, name='create_event'),
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
