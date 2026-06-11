from django.shortcuts import render
from django.http import JsonResponse
import json
import sys
import os

# Add parent directory to path to import db.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import gestures_collection, voice_collection, settings_collection, logs_collection

from django.contrib.auth.decorators import login_required
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

@receiver(user_logged_in)
def set_logged_in(sender, user, request, **kwargs):
    settings_collection.update_one({"key": "session_state"}, {"$set": {"logged_in": True, "username": user.username}}, upsert=True)

@receiver(user_logged_out)
def set_logged_out(sender, user, request, **kwargs):
    settings_collection.update_one({"key": "session_state"}, {"$set": {"logged_in": False}}, upsert=True)

# Initial Data for Database Seeding
INITIAL_STATE = {
    'gestures': [
        {
            'id': 'swipe_right',
            'name': 'Swipe Right',
            'type': 'System Trigger',
            'action': 'Next Slide',
            'description': 'Transition between active node canvases or workspaces. Swipe horizontally with a flat palm.',
            'icon': 'swipe_right'
        },
        {
            'id': 'swipe_left',
            'name': 'Swipe Left',
            'type': 'System Trigger',
            'action': 'Previous Slide',
            'description': 'Transition between active node canvases or workspaces. Swipe horizontally with a flat palm.',
            'icon': 'swipe_left'
        },
        {
            'id': 'pinch',
            'name': 'Two Finger Pinch',
            'type': 'Cursor Trigger',
            'action': 'Select / Click',
            'description': 'Micro-scale adjustment or selection. Bring index finger and thumb together.',
            'icon': 'pinch'
        },
        {
            'id': 'fist',
            'name': 'Impact Fist',
            'type': 'System Trigger',
            'action': 'Confirm Primary',
            'description': 'Engagement gesture for high-priority modal confirmation. Close all fingers tight.',
            'icon': 'fist'
        },
        {
            'id': 'palm',
            'name': 'System Wave',
            'type': 'System Trigger',
            'action': 'Clear All HUD',
            'description': 'Macro command for clearing notifications or waking UI. Hold open palm steady.',
            'icon': 'palm'
        },
        {
            'id': 'peace',
            'name': 'Peace Sign',
            'type': 'System Trigger',
            'action': 'Deactivate Cursor',
            'description': 'Disengages active cursor tracking. Extend index and middle finger only.',
            'icon': 'peace'
        },
        {
            'id': 'thumbs_up',
            'name': 'Thumbs Up',
            'type': 'System Trigger',
            'action': 'Volume Up',
            'description': 'Increase system volume. Point thumb upwards with closed fist.',
            'icon': 'thumbs_up'
        },
        {
            'id': 'thumbs_down',
            'name': 'Thumbs Down',
            'type': 'System Trigger',
            'action': 'Volume Down',
            'description': 'Decrease system volume. Point thumb downwards with closed fist.',
            'icon': 'thumbs_down'
        },
        {
            'id': 'index_cursor',
            'name': 'Index Point',
            'type': 'Cursor Mode',
            'action': 'Cursor Tracking',
            'description': 'Activate fine cursor control. Point index finger forward.',
            'icon': 'index_cursor'
        }
    ],
    'voice_commands': [
        {'id': 'open_chrome', 'command': 'open chrome', 'action': 'Launch Chrome', 'tips': ['Speak clearly', 'Use the wake word first']},
        {'id': 'open_browser', 'command': 'open browser', 'action': 'Launch Chrome', 'tips': ['Speak clearly']},
        {'id': 'open_notepad', 'command': 'open notepad', 'action': 'Launch Notepad', 'tips': ['Speak clearly']},
        {'id': 'open_calculator', 'command': 'open calculator', 'action': 'Launch Calculator', 'tips': ['Speak clearly']},
        {'id': 'open_file_explorer', 'command': 'open file explorer', 'action': 'Launch File Explorer', 'tips': ['Speak clearly']},
        {'id': 'open_settings', 'command': 'open settings', 'action': 'Launch Settings', 'tips': ['Speak clearly']},
        {'id': 'open_spotify', 'command': 'open spotify', 'action': 'Launch Spotify', 'tips': ['Speak clearly']},
        {'id': 'open_whatsapp', 'command': 'open whatsapp', 'action': 'Launch WhatsApp', 'tips': ['Speak clearly']},
        {'id': 'open_word', 'command': 'open word', 'action': 'Launch Word', 'tips': ['Speak clearly']},
        {'id': 'open_excel', 'command': 'open excel', 'action': 'Launch Excel', 'tips': ['Speak clearly']},
        {'id': 'open_powerpoint', 'command': 'open powerpoint', 'action': 'Launch PowerPoint', 'tips': ['Speak clearly']},
        {'id': 'open_vscode', 'command': 'open vs code', 'action': 'Launch VS Code', 'tips': ['Speak clearly']},
        {'id': 'open_visual_studio', 'command': 'open visual studio', 'action': 'Launch VS Code', 'tips': ['Speak clearly']},
        {'id': 'open_command_prompt', 'command': 'open command prompt', 'action': 'Launch Command Prompt', 'tips': ['Speak clearly']},
        {'id': 'open_terminal', 'command': 'open terminal', 'action': 'Launch Command Prompt', 'tips': ['Speak clearly']},
        {'id': 'open_task_manager', 'command': 'open task manager', 'action': 'Launch Task Manager', 'tips': ['Speak clearly']},
        {'id': 'search_drive_d', 'command': 'search drive d', 'action': 'Open Drive D:', 'tips': ['Speak clearly']},
        {'id': 'close_window', 'command': 'close window', 'action': 'Close Window', 'tips': ['Speak clearly']},
        {'id': 'minimize_window', 'command': 'minimize window', 'action': 'Minimize Window', 'tips': ['Speak clearly']},
        {'id': 'maximize_window', 'command': 'maximize window', 'action': 'Maximize Window', 'tips': ['Speak clearly']},
        {'id': 'switch_window', 'command': 'switch window', 'action': 'Switch Window', 'tips': ['Speak clearly']},
        {'id': 'show_desktop', 'command': 'show desktop', 'action': 'Show Desktop', 'tips': ['Speak clearly']},
        {'id': 'snap_left', 'command': 'snap left', 'action': 'Snap Window Left', 'tips': ['Speak clearly']},
        {'id': 'snap_right', 'command': 'snap right', 'action': 'Snap Window Right', 'tips': ['Speak clearly']},
        {'id': 'new_tab', 'command': 'new tab', 'action': 'New Tab', 'tips': ['Speak clearly']},
        {'id': 'close_tab', 'command': 'close tab', 'action': 'Close Tab', 'tips': ['Speak clearly']},
        {'id': 'reopen_tab', 'command': 'reopen tab', 'action': 'Reopen Tab', 'tips': ['Speak clearly']},
        {'id': 'play', 'command': 'play', 'action': 'Play/Pause', 'tips': ['Speak clearly']},
        {'id': 'pause', 'command': 'pause', 'action': 'Play/Pause', 'tips': ['Speak clearly']},
        {'id': 'play_pause', 'command': 'play pause', 'action': 'Play/Pause', 'tips': ['Speak clearly']},
        {'id': 'next_song', 'command': 'next song', 'action': 'Next Song', 'tips': ['Speak clearly']},
        {'id': 'previous_song', 'command': 'previous song', 'action': 'Previous Song', 'tips': ['Speak clearly']},
        {'id': 'volume_up', 'command': 'volume up', 'action': 'Increase Volume', 'tips': ['Speak clearly']},
        {'id': 'volume_down', 'command': 'volume down', 'action': 'Decrease Volume', 'tips': ['Speak clearly']},
        {'id': 'mute', 'command': 'mute', 'action': 'Mute Volume', 'tips': ['Speak clearly']},
        {'id': 'unmute', 'command': 'unmute', 'action': 'Unmute Volume', 'tips': ['Speak clearly']},
        {'id': 'take_screenshot', 'command': 'take screenshot', 'action': 'Take Screenshot', 'tips': ['Speak clearly']},
        {'id': 'screenshot', 'command': 'screenshot', 'action': 'Take Screenshot', 'tips': ['Speak clearly']},
        {'id': 'lock_screen', 'command': 'lock screen', 'action': 'Lock Screen', 'tips': ['Speak clearly']},
        {'id': 'search', 'command': 'search', 'action': 'Search Windows', 'tips': ['Speak clearly']},
        {'id': 'select_all', 'command': 'select all', 'action': 'Select All', 'tips': ['Speak clearly']},
        {'id': 'copy', 'command': 'copy', 'action': 'Copy', 'tips': ['Speak clearly']},
        {'id': 'paste', 'command': 'paste', 'action': 'Paste', 'tips': ['Speak clearly']},
        {'id': 'cut', 'command': 'cut', 'action': 'Cut', 'tips': ['Speak clearly']},
        {'id': 'undo', 'command': 'undo', 'action': 'Undo', 'tips': ['Speak clearly']},
        {'id': 'redo', 'command': 'redo', 'action': 'Redo', 'tips': ['Speak clearly']},
        {'id': 'save', 'command': 'save', 'action': 'Save', 'tips': ['Speak clearly']},
        {'id': 'find', 'command': 'find', 'action': 'Find', 'tips': ['Speak clearly']},
        {'id': 'start_presentation', 'command': 'start presentation', 'action': 'Start Presentation', 'tips': ['Speak clearly']},
        {'id': 'start_slideshow', 'command': 'start slideshow', 'action': 'Start Slideshow', 'tips': ['Speak clearly']},
        {'id': 'end_presentation', 'command': 'end presentation', 'action': 'End Presentation', 'tips': ['Speak clearly']},
        {'id': 'next_slide', 'command': 'next slide', 'action': 'Next Slide', 'tips': ['Works best in PowerPoint context']},
        {'id': 'previous_slide', 'command': 'previous slide', 'action': 'Previous Slide', 'tips': ['Speak clearly']},
        {'id': 'scroll_up', 'command': 'scroll up', 'action': 'Scroll Up', 'tips': ['Speak clearly']},
        {'id': 'scroll_down', 'command': 'scroll down', 'action': 'Scroll Down', 'tips': ['Speak clearly']},
        {'id': 'page_up', 'command': 'page up', 'action': 'Page Up', 'tips': ['Speak clearly']},
        {'id': 'page_down', 'command': 'page down', 'action': 'Page Down', 'tips': ['Speak clearly']}
    ],
    'wake_word': 'System'
}

def init_db():
    try:
        if gestures_collection.count_documents({}) == 0:
            gestures_collection.insert_many([dict(g) for g in INITIAL_STATE['gestures']])
        if voice_collection.count_documents({}) == 0:
            voice_collection.insert_many([dict(c) for c in INITIAL_STATE['voice_commands']])
        if settings_collection.count_documents({"key": "wake_word"}) == 0:
            settings_collection.insert_one({"key": "wake_word", "value": INITIAL_STATE['wake_word']})
    except Exception as e:
        print(f"MongoDB connection error: {e}")

init_db()

from .forms import CustomSignupForm
from django.contrib.auth import logout
from django.shortcuts import redirect

def signup(request):
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomSignupForm()
    return render(request, 'registration/signup.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard_home(request):
    return render(request, 'dashboard.html')

@login_required
def gesture_settings(request):
    return render(request, 'gesture_settings.html')

@login_required
def voice_settings(request):
    return render(request, 'voice_settings.html')

@login_required
def live_nodes(request):
    return render(request, 'live_nodes.html')

@login_required
def vault(request):
    return render(request, 'vault.html')

@login_required
def cursor_control(request):
    return render(request, 'cursor_control.html')

@login_required
def system_controls(request):
    return render(request, 'system_controls.html')

@login_required
def help_guide(request):
    return render(request, 'help_guide.html')

def api_gestures(request):
    if request.method == 'GET':
        gestures = list(gestures_collection.find({}, {'_id': False}))
        return JsonResponse({'status': 'success', 'gestures': gestures})

def api_gestures_update(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            gesture_id = data.get('id')
            new_action = data.get('action')
            result = gestures_collection.update_one({'id': gesture_id}, {'$set': {'action': new_action}})
            if result.matched_count > 0:
                return JsonResponse({'status': 'success', 'message': 'Updated successfully'})
            return JsonResponse({'status': 'error', 'message': 'Gesture not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

def api_voice_commands(request):
    if request.method == 'GET':
        commands = list(voice_collection.find({}, {'_id': False}))
        return JsonResponse({'status': 'success', 'commands': commands})

def api_voice_update(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cmd_id = data.get('id')
            new_action = data.get('action')
            result = voice_collection.update_one({'id': cmd_id}, {'$set': {'action': new_action}})
            if result.matched_count > 0:
                return JsonResponse({'status': 'success', 'message': 'Updated successfully'})
            return JsonResponse({'status': 'error', 'message': 'Command not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

def api_wake_word(request):
    if request.method == 'GET':
        ww_doc = settings_collection.find_one({"key": "wake_word"})
        return JsonResponse({'status': 'success', 'wake_word': ww_doc['value'] if ww_doc else 'System'})
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_wake_word = data.get('wake_word')
            if new_wake_word:
                settings_collection.update_one({"key": "wake_word"}, {"$set": {"value": new_wake_word}}, upsert=True)
                return JsonResponse({'status': 'success', 'message': 'Wake word updated'})
            return JsonResponse({'status': 'error', 'message': 'Invalid wake word'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

def api_system_logs(request):
    if request.method == 'GET':
        try:
            logs = list(logs_collection.find({}, {'_id': False}).sort([("timestamp", -1)]).limit(50))
            return JsonResponse({'status': 'success', 'logs': logs})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

def api_recent_commands(request):
    if request.method == 'GET':
        try:
            commands = list(logs_collection.find({"event_type": {"$in": ["voice", "gesture"]}}, {'_id': False}).sort([("timestamp", -1)]).limit(10))
            return JsonResponse({'status': 'success', 'commands': commands})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

def api_system_status(request):
    """Returns real-time status of backend subsystems by checking MongoDB for recent activity."""
    if request.method == 'GET':
        try:
            import datetime
            now = datetime.datetime.utcnow()
            threshold = now - datetime.timedelta(seconds=30)
            threshold_iso = threshold.isoformat() + "Z"

            # Check for recent gesture logs (means camera + hand tracking is alive)
            gesture_alive = logs_collection.count_documents({
                "event_type": {"$in": ["gesture", "system"]},
                "timestamp": {"$gte": threshold_iso}
            }) > 0

            # Check for recent voice logs or system logs (means voice engine is alive)
            voice_alive = logs_collection.count_documents({
                "event_type": {"$in": ["voice", "system"]},
                "timestamp": {"$gte": threshold_iso}
            }) > 0

            # MongoDB is alive if we got this far without exception
            db_alive = True

            return JsonResponse({
                'status': 'success',
                'gestures_online': gesture_alive,
                'voice_online': voice_alive,
                'database_online': db_alive
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'gestures_online': False,
                'voice_online': False,
                'database_online': False,
                'message': str(e)
            })
