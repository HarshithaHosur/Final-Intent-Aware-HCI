from django.contrib import admin
from django.urls import path, include
from dashboard import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.custom_logout, name='custom_logout'),
    path('face-register/', views.face_register, name='face_register'),
    path('face-verify/', views.face_verify, name='face_verify'),
    path('api/face-status/', views.api_face_status, name='api_face_status'),
    path('', views.dashboard_home, name='dashboard_home'),
    path('gesture-settings/', views.gesture_settings, name='gesture_settings'),
    path('voice-settings/', views.voice_settings, name='voice_settings'),
    
    path('live-nodes/', views.live_nodes, name='live_nodes'),
    path('vault/', views.vault, name='vault'),
    path('cursor-control/', views.cursor_control, name='cursor_control'),
    path('system-controls/', views.system_controls, name='system_controls'),
    path('help-guide/', views.help_guide, name='help_guide'),
    
    # APIs
    path('gestures/', views.api_gestures, name='api_gestures'),
    path('gestures/update/', views.api_gestures_update, name='api_gestures_update'),
    path('voice-commands/', views.api_voice_commands, name='api_voice_commands'),
    path('voice-commands/update/', views.api_voice_update, name='api_voice_update'),
    path('voice/wake-word/', views.api_wake_word, name='api_wake_word'),
    path('api/system-logs/', views.api_system_logs, name='api_system_logs'),
    path('api/recent-commands/', views.api_recent_commands, name='api_recent_commands'),
    path('api/system-status/', views.api_system_status, name='api_system_status'),
    path('api/users/', views.api_registered_users, name='api_registered_users'),
    path('api/signup-face-capture/', views.api_signup_face_capture, name='api_signup_face_capture'),
    path('api/signup-face-status/', views.api_signup_face_status, name='api_signup_face_status'),
    path('api/toggle-module/', views.api_toggle_module, name='api_toggle_module'),
    path('api/modules-state/', views.api_modules_state, name='api_modules_state'),
    path('api/gestures/add/', views.api_add_gesture, name='api_add_gesture'),
    path('api/gestures/delete/<str:gesture_id>/', views.api_delete_gesture, name='api_delete_gesture'),
    path('api/emergency-kill/', views.api_emergency_kill, name='api_emergency_kill'),
]
