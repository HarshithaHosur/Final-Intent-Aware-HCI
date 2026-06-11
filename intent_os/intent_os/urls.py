from django.contrib import admin
from django.urls import path, include
from dashboard import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.custom_logout, name='custom_logout'),
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
]
