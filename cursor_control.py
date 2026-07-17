# ============================================================
#  CURSOR CONTROL MODULE — System-Level Virtual Mouse
#  Uses MediaPipe hand tracking to control OS mouse globally
#
#  Features:
#    - Index finger (landmark 8) → cursor position
#    - Thumb+Index pinch → left click
#    - Thumb+Middle pinch → right click
#    - Hold pinch → drag and drop
#    - Exponential smoothing for stable movement
#    - Dead zone to prevent micro-jitter
#    - Mirror correction (move hand right → cursor right)
#    - Full screen mapping from camera to monitor resolution
#
#  Integration:
#    - Only active when  mode == "cursor"
#    - Call cursor_controller.update(landmarks, img) each frame
#    - Call cursor_controller.release() when exiting cursor mode
# ============================================================

import math
import time
import pyautogui
import cv2

# ── Prevent pyautogui from failing at screen edges ──
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # Minimal delay for responsive cursor


# ============================================================
#         CONFIGURATION — Tune these for your setup
# ============================================================

# Screen resolution (auto-detected)
SCREEN_W, SCREEN_H = pyautogui.size()

# Camera resolution (must match your cv2 capture settings)
CAM_W = 640
CAM_H = 480

# ── Mapping Region ──
# We don't use the full camera frame for mapping — the edges are
# unreliable. Instead we map a central region of the camera to
# the full screen. This makes it easier to reach all corners.
# Values are fractions of the camera frame (0.0 – 1.0).
MAP_X_MIN = 0.28   # left 28% ignored
MAP_X_MAX = 0.72   # right 28% ignored
MAP_Y_MIN = 0.28   # top 28% ignored
MAP_Y_MAX = 0.72   # bottom 28% ignored

# ── Smoothing ──
# Exponential smoothing factor (0.0 = max smooth, 1.0 = no smooth)
# Lower = smoother but more latency; higher = faster but jitterier
SMOOTHING_FACTOR = 0.55

# ── Dead Zone ──
# Ignore cursor movements smaller than this many pixels on screen
DEAD_ZONE_PX = 4

# ── Click / Pinch Detection ──
# Distance threshold (in normalised landmark units) for pinch
# Typical value: 0.045 – 0.06 depending on hand size / distance
PINCH_THRESHOLD = 0.055

# Right-click pinch threshold (thumb + middle finger)
RIGHT_PINCH_THRESHOLD = 0.055

# ── Gesture Stability ──
# Every cursor action (click, drag) must be held for this many seconds
PINCH_STABILITY_TIME = 0.8

# ── Click Cooldown ──
# Minimum time (seconds) after an action before the next can trigger
# ── Drag Detection ──
# How many consecutive "pinch held" frames before we enter drag mode
DRAG_ENTRY_FRAMES = 4

CLICK_COOLDOWN = 0.4



# ============================================================
#               SMOOTHING HELPER
# ============================================================

class Smoother:
    """Exponential moving average for (x, y) screen coordinates."""

    def __init__(self, alpha=SMOOTHING_FACTOR):
        self.alpha = alpha      # smoothing factor
        self.sx = None          # smoothed x
        self.sy = None          # smoothed y

    def update(self, raw_x, raw_y):
        """Feed a new raw position; returns the smoothed position."""
        if self.sx is None:
            # First frame — initialise directly
            self.sx = raw_x
            self.sy = raw_y
        else:
            self.sx = self.alpha * raw_x + (1 - self.alpha) * self.sx
            self.sy = self.alpha * raw_y + (1 - self.alpha) * self.sy
        return int(self.sx), int(self.sy)

    def reset(self):
        self.sx = None
        self.sy = None


# ============================================================
#           COORDINATE MAPPER  (Camera → Screen)
# ============================================================

def map_to_screen(norm_x, norm_y):
    """
    Convert normalised hand coordinates (0–1 from MediaPipe)
    to absolute screen pixel coordinates.

    Applies:
      1. Mirror correction  (MediaPipe gives mirrored x after flip)
      2. Clamping to the mapping sub-region
      3. Linear interpolation to full screen size
    """
    # Clamp to mapping region
    cx = max(MAP_X_MIN, min(norm_x, MAP_X_MAX))
    cy = max(MAP_Y_MIN, min(norm_y, MAP_Y_MAX))

    # Normalise within the mapping region (0 – 1)
    rx = (cx - MAP_X_MIN) / (MAP_X_MAX - MAP_X_MIN)
    ry = (cy - MAP_Y_MIN) / (MAP_Y_MAX - MAP_Y_MIN)

    # Scale to screen pixels
    screen_x = int(rx * SCREEN_W)
    screen_y = int(ry * SCREEN_H)

    # Safety clamp
    screen_x = max(0, min(screen_x, SCREEN_W - 1))
    screen_y = max(0, min(screen_y, SCREEN_H - 1))

    return screen_x, screen_y


# ============================================================
#           PINCH DISTANCE HELPER
# ============================================================

def landmark_distance(lm_a, lm_b):
    """Euclidean distance between two MediaPipe landmarks (normalised)."""
    return math.sqrt(
        (lm_a.x - lm_b.x) ** 2 +
        (lm_a.y - lm_b.y) ** 2 +
        (lm_a.z - lm_b.z) ** 2
    )


# ============================================================
#              MAIN CURSOR CONTROLLER CLASS
# ============================================================

class CursorController:
    """
    System-level virtual mouse driven by hand tracking.

    All click / drag actions require a 3-second pinch hold before
    executing.  After execution a 1-second cooldown is enforced.

    Usage each frame (when mode == "cursor"):
        controller.update(hand_landmarks, frame_image)

    When leaving cursor mode:
        controller.release()
    """

    def __init__(self):
        # ── Smoothing ──
        self.smoother = Smoother(alpha=SMOOTHING_FACTOR)

        # ── Previous cursor position (for dead zone) ──
        self.prev_x = None
        self.prev_y = None

        # ── Tap & Drag State ──
        self.z_history = []
        self.tap_count = 0
        self.last_tap_time = 0
        self.drag_active = False

        # ── Click states (with 3-second hold verification) ──
        self.left_click_time = 0          # last execution timestamp
        self.right_click_time = 0         # last execution timestamp
        self.left_pinching = False
        self.right_pinching = False
        self.pinch_hold_frames = 0

        # ── 3-second stability tracking for pinch actions ──
        self.left_pinch_start = None      # timestamp when left pinch first detected
        self.left_pinch_fired = False     # True once the 3 s hold has triggered
        self.right_pinch_start = None     # timestamp when right pinch first detected
        self.right_pinch_fired = False    # True once the 3 s hold has triggered

    # ────────────────────────────────────────────────────
    #  PUBLIC API
    # ────────────────────────────────────────────────────

    def update(self, landmarks, img, context='default'):
        info = {
            'cursor_pos': (0, 0),
            'left_click': False,
            'right_click': False,
            'dragging': False,
            'deactivate_cursor': False,
            'left_dist': 1.0,
            'right_dist': 1.0,
        }

        if landmarks is None:
            return info

        # ── 1. Get index fingertip position (landmark 8) ──
        index_tip = landmarks[8]
        index_mcp = landmarks[5]

        # ── 2. Detect Peace Sign (Deactivate Cursor) ──
        index_up = index_tip.y < landmarks[6].y
        middle_up = landmarks[12].y < landmarks[10].y
        ring_down = landmarks[16].y > landmarks[14].y
        pinky_down = landmarks[20].y > landmarks[18].y
        
        peace_sign = index_up and middle_up and ring_down and pinky_down
        if peace_sign:
            info['deactivate_cursor'] = True
            if self.drag_active:
                pyautogui.mouseUp(button='left', _pause=False)
                self.drag_active = False
            # Reset pinch hold trackers on peace sign
            self.left_pinch_start = None
            self.left_pinch_fired = False
            self.right_pinch_start = None
            self.right_pinch_fired = False
            self.pinch_hold_frames = 0
            return info

        # ── 3. Map to screen & Smoothing ──
        raw_x, raw_y = map_to_screen(index_tip.x, index_tip.y)
        smooth_x, smooth_y = self.smoother.update(raw_x, raw_y)

        if self.prev_x is not None:
            dx = abs(smooth_x - self.prev_x)
            dy = abs(smooth_y - self.prev_y)
            if dx < DEAD_ZONE_PX and dy < DEAD_ZONE_PX:
                smooth_x = self.prev_x
                smooth_y = self.prev_y

        self.prev_x = smooth_x
        self.prev_y = smooth_y
        info['cursor_pos'] = (smooth_x, smooth_y)

        # Move the OS cursor
        import ctypes
        ctypes.windll.user32.SetCursorPos(smooth_x, smooth_y)

        now = time.time()

        # ── 4. Pinch distances ──
        thumb_tip = landmarks[4]
        left_dist = landmark_distance(thumb_tip, index_tip)
        info['left_dist'] = left_dist

        middle_tip = landmarks[12]
        right_dist = landmark_distance(thumb_tip, middle_tip)
        info['right_dist'] = right_dist

        if context == 'browser':
            # ════════════════════════════════════════════════
            #  BROWSER MODE: 3-second pinch hold verification
            # ════════════════════════════════════════════════
            STABILITY_TIME = 3.0

            # LEFT CLICK
            if left_dist < PINCH_THRESHOLD:
                if self.left_pinch_start is None:
                    self.left_pinch_start = now
                    self.left_pinch_fired = False
                elif not self.left_pinch_fired:
                    elapsed = now - self.left_pinch_start
                    if elapsed >= STABILITY_TIME:
                        if now - self.left_click_time > CLICK_COOLDOWN:
                            pyautogui.click(_pause=False)
                            self.left_click_time = now
                            info['left_click'] = True
                        self.left_pinch_fired = True
            else:
                self.left_pinch_start = None
                self.left_pinch_fired = False
                if self.drag_active:
                    pyautogui.mouseUp(button='left', _pause=False)
                    self.drag_active = False

            # RIGHT CLICK
            if right_dist < RIGHT_PINCH_THRESHOLD:
                if self.right_pinch_start is None:
                    self.right_pinch_start = now
                    self.right_pinch_fired = False
                elif not self.right_pinch_fired:
                    elapsed = now - self.right_pinch_start
                    if elapsed >= STABILITY_TIME:
                        if now - self.right_click_time > CLICK_COOLDOWN:
                            pyautogui.rightClick(_pause=False)
                            self.right_click_time = now
                            info['right_click'] = True
                        self.right_pinch_fired = True
            else:
                self.right_pinch_start = None
                self.right_pinch_fired = False

        else:
            # ════════════════════════════════════════════════
            #  NON-BROWSER MODE: Immediate Actions (Instant Click & Drag)
            # ════════════════════════════════════════════════
            self.left_pinch_fired = False
            self.right_pinch_start = None
            self.right_pinch_fired = False

            # Handle immediate left click and drag (time-based check)
            if left_dist < PINCH_THRESHOLD:
                if not self.left_pinching:
                    self.left_pinching = True
                    self.left_pinch_start = now
                elif not self.drag_active:
                    elapsed = now - (self.left_pinch_start or now)
                    if elapsed >= 0.35:  # 0.35 seconds to enter drag mode
                        self.drag_active = True
                        pyautogui.mouseDown(button='left', _pause=False)
            else:
                if self.left_pinching:
                    if self.drag_active:
                        pyautogui.mouseUp(button='left', _pause=False)
                        self.drag_active = False
                    else:
                        # Quick tap -> trigger click immediately on release
                        if now - self.left_click_time > CLICK_COOLDOWN:
                            pyautogui.click(_pause=False)
                            self.left_click_time = now
                            info['left_click'] = True
                    self.left_pinching = False
                    self.left_pinch_start = None
                    self.pinch_hold_frames = 0

            # Handle immediate right click
            if right_dist < RIGHT_PINCH_THRESHOLD:
                if not self.right_pinching:
                    self.right_pinching = True
                    if now - self.right_click_time > CLICK_COOLDOWN:
                        pyautogui.rightClick(_pause=False)
                        self.right_click_time = now
                        info['right_click'] = True
            else:
                self.right_pinching = False

        info['dragging'] = self.drag_active

        # Visual Feedback
        if img is not None:
            self._draw_feedback(img, landmarks, info, left_dist, right_dist, context)

        return info

    def release(self):
        """
        Call when exiting cursor mode to ensure mouse buttons
        are released and internal state is clean.
        """
        if self.drag_active:
            pyautogui.mouseUp(button='left', _pause=False)
            self.drag_active = False

        self.left_pinching = False
        self.right_pinching = False
        self.pinch_hold_frames = 0
        self.smoother.reset()
        self.prev_x = None
        self.prev_y = None
        self.z_history.clear()
        self.tap_count = 0

        # Reset 3-second pinch hold trackers
        self.left_pinch_start = None
        self.left_pinch_fired = False
        self.right_pinch_start = None
        self.right_pinch_fired = False

    # ────────────────────────────────────────────────────
    #  VISUAL FEEDBACK (draws on the camera frame)
    # ────────────────────────────────────────────────────

    def _draw_feedback(self, img, landmarks, info, left_dist, right_dist, context='default'):
        """Draw cursor info, pinch indicators, and status on frame."""
        h, w = img.shape[:2]
        now = time.time()

        # ── Draw index fingertip circle ──
        ix = int(landmarks[8].x * w)
        iy = int(landmarks[8].y * h)
        cv2.circle(img, (ix, iy), 14, (0, 255, 255), 2)    # cyan ring
        cv2.circle(img, (ix, iy), 4,  (0, 255, 255), -1)   # filled dot

        # ── Status labels ──
        sx, sy = info['cursor_pos']

        # Cursor coordinates
        cv2.putText(img, f"Cursor: ({sx}, {sy})", (10, h - 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 2, cv2.LINE_AA)

        # Gesture status
        cv2.putText(img, f"Dragging: {'ON' if info.get('dragging') else 'OFF'}", (10, h - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 255, 180), 2, cv2.LINE_AA)

        # ── Pinch hold progress bar (shows 3-second countdown only in browser) ──
        pinch_label = None
        pinch_progress = 0.0
        stability_time = 3.0 if context == 'browser' else PINCH_STABILITY_TIME
        if self.left_pinch_start is not None and not self.left_pinch_fired:
            elapsed = now - self.left_pinch_start
            pinch_progress = min(elapsed / stability_time, 1.0)
            pinch_label = "LEFT CLICK"
        elif self.right_pinch_start is not None and not self.right_pinch_fired:
            elapsed = now - self.right_pinch_start
            pinch_progress = min(elapsed / stability_time, 1.0)
            pinch_label = "RIGHT CLICK"

        if pinch_label and pinch_progress > 0:
            bar_x1, bar_x2 = w // 2 - 80, w // 2 + 80
            bar_y1, bar_y2 = h // 2 + 60, h // 2 + 76
            fill = int(pinch_progress * (bar_x2 - bar_x1))
            bar_col = (0, 200, 255) if pinch_progress < 1.0 else (0, 255, 0)
            cv2.rectangle(img, (bar_x1, bar_y1), (bar_x2, bar_y2), (40, 40, 40), -1)
            cv2.rectangle(img, (bar_x1, bar_y1), (bar_x1 + fill, bar_y2), bar_col, -1)
            cv2.rectangle(img, (bar_x1, bar_y1), (bar_x2, bar_y2), (100, 100, 100), 1)
            pct_text = f"{pinch_label} {int(pinch_progress * 100)}%"
            cv2.putText(img, pct_text, (bar_x1, bar_y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, bar_col, 2, cv2.LINE_AA)

        # ── Flash "CLICK" / "RIGHT CLICK" / "DRAGGING" ──
        if info.get('left_click'):
            cv2.putText(img, "LEFT CLICK", (w // 2 - 80, h // 2),
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)

        if info.get('right_click'):
            cv2.putText(img, "RIGHT CLICK", (w // 2 - 90, h // 2 + 40),
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 165, 255), 2, cv2.LINE_AA)

        if info.get('dragging'):
            cv2.putText(img, "DRAGGING", (w // 2 - 65, h // 2 - 40),
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 200, 255), 2, cv2.LINE_AA)

        # ── "CURSOR MODE" badge ──
        badge = "  CURSOR MODE  "
        (bw, bh), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        bx = w - bw - 14
        by = h - 70
        cv2.rectangle(img, (bx - 4, by - bh - 4), (bx + bw + 4, by + 6),
                      (0, 120, 200), -1)
        cv2.rectangle(img, (bx - 4, by - bh - 4), (bx + bw + 4, by + 6),
                      (0, 200, 255), 1)
        cv2.putText(img, badge, (bx, by),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

        # ── Mapping region rectangle (shows usable area on camera) ──
        rx1 = int(MAP_X_MIN * w)
        ry1 = int(MAP_Y_MIN * h)
        rx2 = int(MAP_X_MAX * w)
        ry2 = int(MAP_Y_MAX * h)
        cv2.rectangle(img, (rx1, ry1), (rx2, ry2), (60, 60, 60), 1)
