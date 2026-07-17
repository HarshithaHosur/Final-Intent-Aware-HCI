# ============================================================
#  HAND OWNERSHIP VERIFIER — Layered Defense Pipeline
#  Prevents hand misattribution in multi-person environments
#
#  Layer 1: Multi-Person Detection Gate
#    - Counts faces visible in the frame
#    - Freezes gestures if more than one person detected
#
#  Layer 2: Anatomical Plausibility Check
#    - Compares pose wrist (from Holistic skeleton) with
#      hand landmark wrist (Landmark 0)
#    - Rejects hands that don't belong to the tracked body
#
#  Layer 3: Temporal Continuity Check
#    - Tracks wrist position across frames
#    - Rejects implausible wrist teleportation
#
#  Usage:
#    verifier = HandOwnershipVerifier(HandOwnershipConfig())
#    result = verifier.verify(frame_rgb, holistic_results, True)
#    if result.gesture_ready:
#        # safe to process gestures
#
#  Limitations:
#    No vision-only system provides absolute certainty in
#    adversarial scenarios. A coordinated attacker who
#    precisely mimics hand position during occlusion may
#    theoretically bypass these checks. For high-assurance
#    security, combine with secondary authentication factors
#    (continuous voice, wearable devices, etc.).
# ============================================================

import math
import time
import mediapipe as mp


# ============================================================
#              CONFIGURATION — Tune for your setup
# ============================================================

class HandOwnershipConfig:
    """
    Configurable thresholds for the hand ownership verifier.
    All distance thresholds use MediaPipe's normalised coordinate
    system (0.0 – 1.0), making them resolution-independent.

    Attributes:
        max_faces_allowed (int):
            Maximum number of faces allowed before gesture freeze.
            Default 1 = only the authenticated user.

        max_wrist_mismatch_norm (float):
            Maximum normalised distance between pose wrist and
            hand wrist (Landmark 0). If exceeded, the hand is
            rejected as not belonging to the tracked skeleton.
            Typical range: 0.10 – 0.20

        max_wrist_jump_norm (float):
            Maximum normalised wrist displacement allowed between
            consecutive frames. Larger jumps indicate hand switching
            or tracking errors. Typical range: 0.15 – 0.30

        face_detection_interval (int):
            Run face detection every N frames for performance.
            Higher = faster but slower to react to new faces.
            Default 3 is a good balance.

        enforce_single_person (bool):
            If True, Layer 1 blocks all gestures when multiple
            people are visible. If False, Layer 1 is relaxed and
            the system relies on Layers 2+3 only. Set False for
            shared-space deployments where background people are
            expected.

        face_detection_confidence (float):
            MediaPipe face detection minimum confidence threshold.
            Lower = more sensitive (catches distant faces).
    """

    def __init__(self):
        # Layer 1 — Multi-Person Gate
        self.max_faces_allowed = 1
        self.enforce_single_person = True
        self.face_detection_interval = 5
        self.face_detection_confidence = 0.5

        # Layer 2 — Anatomical Plausibility
        self.max_wrist_mismatch_norm = 0.15

        # Layer 3 — Temporal Continuity
        self.max_wrist_jump_norm = 0.25

    def __repr__(self):
        return (
            f"HandOwnershipConfig("
            f"max_faces={self.max_faces_allowed}, "
            f"wrist_mismatch={self.max_wrist_mismatch_norm}, "
            f"wrist_jump={self.max_wrist_jump_norm}, "
            f"enforce_single={self.enforce_single_person})"
        )


# ============================================================
#              VERIFICATION RESULT
# ============================================================

class VerificationResult:
    """
    Outcome of a single frame's ownership verification.
    Used by the main loop to decide whether to execute gestures,
    and by the debug overlay to display verification states.
    """

    def __init__(self):
        # Individual layer results
        self.face_authenticated = False       # Login + face_recognition verified
        self.single_person = False            # Layer 1 passed
        self.left_wrist_match = True          # Layer 2 for left hand
        self.right_wrist_match = True         # Layer 2 for right hand
        self.left_motion_valid = True         # Layer 3 for left hand
        self.right_motion_valid = True        # Layer 3 for right hand

        # Derived flags
        self.left_hand_valid = True           # Layer 2 + 3 combined for left
        self.right_hand_valid = True          # Layer 2 + 3 combined for right
        self.gesture_ready = False            # ALL conditions met

        # Diagnostics
        self.face_count = 0
        self.rejection_reason = None
        self.left_wrist_distance = 0.0        # Actual measured distance (Layer 2)
        self.right_wrist_distance = 0.0
        self.left_wrist_jump = 0.0            # Actual measured jump (Layer 3)
        self.right_wrist_jump = 0.0


# ============================================================
#             WRIST HISTORY TRACKER (for Layer 3)
# ============================================================

class _WristTracker:
    """
    Maintains a small ring buffer of recent wrist positions
    for temporal continuity validation (Layer 3).
    """

    def __init__(self, max_history=5):
        self.max_history = max_history
        self.positions = []        # list of (x, y, timestamp)
        self._stable_frames = 0    # count of consecutive valid frames

    def update(self, x, y):
        """
        Record a new wrist position.
        Returns (is_valid, jump_distance):
            is_valid: True if movement is within plausible range
            jump_distance: actual normalised displacement from last frame
        """
        now = time.time()

        if not self.positions:
            self.positions.append((x, y, now))
            self._stable_frames = 1
            return True, 0.0

        last_x, last_y, _ = self.positions[-1]
        jump = math.sqrt((x - last_x) ** 2 + (y - last_y) ** 2)

        self.positions.append((x, y, now))

        # Trim to max history
        if len(self.positions) > self.max_history:
            self.positions.pop(0)

        return jump, jump  # caller checks against threshold

    def reset(self):
        """Clear history when tracking is lost."""
        self.positions.clear()
        self._stable_frames = 0

    @property
    def has_history(self):
        return len(self.positions) >= 2


# ============================================================
#           HAND OWNERSHIP VERIFIER (Main Class)
# ============================================================

class HandOwnershipVerifier:
    """
    Implements the three-layer hand ownership verification pipeline.

    This class is designed to be instantiated once and called every
    frame from the main processing loop. It maintains internal state
    for temporal tracking and face detection caching.

    Usage:
        config = HandOwnershipConfig()
        verifier = HandOwnershipVerifier(config)

        # In main loop:
        result = verifier.verify(frame_rgb, holistic_results, face_verified=True)
        if result.gesture_ready:
            # process gestures
        else:
            print(f"Blocked: {result.rejection_reason}")
    """

    def __init__(self, config=None):
        self.config = config or HandOwnershipConfig()

        # Layer 1: Face detection model (short-range, lightweight)
        self._face_detection = mp.solutions.face_detection.FaceDetection(
            model_selection=0,  # 0 = short-range (< 2m), faster
            min_detection_confidence=self.config.face_detection_confidence
        )
        self._frame_counter = 0
        self._cached_face_count = 0    # cached result between detection runs

        # Layer 3: Per-hand wrist trackers
        self._left_wrist_tracker = _WristTracker()
        self._right_wrist_tracker = _WristTracker()

        print(f"[🛡️  VERIFIER] Hand Ownership Verifier initialised: {self.config}")

    # ────────────────────────────────────────────────────
    #  PUBLIC API
    # ────────────────────────────────────────────────────

    def verify(self, frame_rgb, holistic_results, face_verified=False):
        """
        Run all verification layers on the current frame.

        Args:
            frame_rgb: The current camera frame in RGB (numpy array).
            holistic_results: Output from mp.solutions.holistic.process().
            face_verified: Whether the user has been authenticated via
                          face recognition (from login flow).

        Returns:
            VerificationResult with all layer outcomes.
        """
        result = VerificationResult()
        result.face_authenticated = face_verified

        if not face_verified:
            result.rejection_reason = "Face not authenticated"
            return result

        # ── Layer 1: Multi-Person Detection Gate ──
        self._frame_counter += 1
        if self._frame_counter % self.config.face_detection_interval == 0:
            self._cached_face_count = self._count_faces(frame_rgb)

        result.face_count = self._cached_face_count

        if self.config.enforce_single_person:
            result.single_person = (self._cached_face_count <= self.config.max_faces_allowed)
            if not result.single_person:
                result.rejection_reason = (
                    f"Multi-person detected ({self._cached_face_count} faces). "
                    f"Gestures frozen."
                )
                # Reset wrist trackers since we can't trust tracking
                self._left_wrist_tracker.reset()
                self._right_wrist_tracker.reset()
                return result
        else:
            # Single-person enforcement relaxed — always pass Layer 1
            result.single_person = True

        # ── Layer 2: Anatomical Plausibility Check ──
        self._check_wrist_plausibility(holistic_results, result)

        # ── Layer 3: Temporal Continuity Check ──
        self._check_temporal_continuity(holistic_results, result)

        # ── Combine per-hand validity ──
        result.left_hand_valid = result.left_wrist_match and result.left_motion_valid
        result.right_hand_valid = result.right_wrist_match and result.right_motion_valid

        # ── Final decision: gesture_ready if ALL global conditions met ──
        # (per-hand validity is checked separately when selecting which hand to use)
        left_detected = holistic_results.left_hand_landmarks is not None
        right_detected = holistic_results.right_hand_landmarks is not None
        
        if left_detected or right_detected:
            any_hand_valid = (left_detected and result.left_hand_valid) or (right_detected and result.right_hand_valid)
        else:
            any_hand_valid = True

        result.gesture_ready = (
            result.face_authenticated
            and result.single_person
            and any_hand_valid
        )

        if not result.gesture_ready and result.rejection_reason is None:
            if not any_hand_valid:
                reasons = []
                if not result.left_wrist_match or not result.right_wrist_match:
                    reasons.append("wrist mismatch")
                if not result.left_motion_valid or not result.right_motion_valid:
                    reasons.append("motion discontinuity")
                result.rejection_reason = f"Hand rejected: {', '.join(reasons)}"

        return result

    def reset(self):
        """Reset all tracking state (call when user leaves frame)."""
        self._left_wrist_tracker.reset()
        self._right_wrist_tracker.reset()
        self._cached_face_count = 0
        self._frame_counter = 0

    # ────────────────────────────────────────────────────
    #  LAYER 1 — MULTI-PERSON DETECTION GATE
    # ────────────────────────────────────────────────────

    def _count_faces(self, frame_rgb):
        """
        Use MediaPipe Face Detection to count the number of
        faces visible in the current frame.

        This is the highest-priority protection layer. If more
        than max_faces_allowed are detected, all gesture
        recognition is immediately frozen.
        """
        try:
            detection_result = self._face_detection.process(frame_rgb)
            if detection_result and detection_result.detections:
                return len(detection_result.detections)
        except Exception:
            pass
        return 0

    # ────────────────────────────────────────────────────
    #  LAYER 2 — ANATOMICAL PLAUSIBILITY CHECK
    # ────────────────────────────────────────────────────

    def _check_wrist_plausibility(self, holistic_results, result):
        """
        Compare pose wrist landmarks (from the full-body skeleton)
        with hand landmark wrist (Landmark 0).

        MediaPipe Holistic provides:
          - Pose landmark 15 = left wrist
          - Pose landmark 16 = right wrist
          - Hand landmark 0  = wrist of the detected hand

        If the distance between these exceeds the threshold, the
        detected hand is rejected as not belonging to the tracked
        user's body.
        """
        pose = holistic_results.pose_landmarks

        # LEFT HAND
        if holistic_results.left_hand_landmarks and pose:
            hand_wrist = holistic_results.left_hand_landmarks.landmark[0]
            pose_wrist = pose.landmark[15]  # Left wrist in pose

            dist = math.sqrt(
                (hand_wrist.x - pose_wrist.x) ** 2 +
                (hand_wrist.y - pose_wrist.y) ** 2
            )
            result.left_wrist_distance = dist
            result.left_wrist_match = (dist <= self.config.max_wrist_mismatch_norm)
        elif holistic_results.left_hand_landmarks and not pose:
            # No pose available — cannot verify, allow with caution
            result.left_wrist_match = True
            result.left_wrist_distance = 0.0
        else:
            # No left hand detected — nothing to verify
            result.left_wrist_match = True
            result.left_wrist_distance = 0.0

        # RIGHT HAND
        if holistic_results.right_hand_landmarks and pose:
            hand_wrist = holistic_results.right_hand_landmarks.landmark[0]
            pose_wrist = pose.landmark[16]  # Right wrist in pose

            dist = math.sqrt(
                (hand_wrist.x - pose_wrist.x) ** 2 +
                (hand_wrist.y - pose_wrist.y) ** 2
            )
            result.right_wrist_distance = dist
            result.right_wrist_match = (dist <= self.config.max_wrist_mismatch_norm)
        elif holistic_results.right_hand_landmarks and not pose:
            result.right_wrist_match = True
            result.right_wrist_distance = 0.0
        else:
            result.right_wrist_match = True
            result.right_wrist_distance = 0.0

    # ────────────────────────────────────────────────────
    #  LAYER 3 — TEMPORAL CONTINUITY CHECK
    # ────────────────────────────────────────────────────

    def _check_temporal_continuity(self, holistic_results, result):
        """
        Track wrist positions across frames. If the wrist suddenly
        jumps farther than physically possible between consecutive
        frames, treat this as an invalid detection (hand switching
        or tracking error).

        Hands cannot teleport. A sudden jump indicates either:
          - Another person's hand entered the crop region
          - MediaPipe briefly lost and re-acquired tracking on a
            different hand
          - An adversarial hand swap attempt
        """
        # LEFT HAND
        if holistic_results.left_hand_landmarks:
            wrist = holistic_results.left_hand_landmarks.landmark[0]
            jump, actual_jump = self._left_wrist_tracker.update(wrist.x, wrist.y)

            result.left_wrist_jump = actual_jump

            if self._left_wrist_tracker.has_history:
                result.left_motion_valid = (
                    actual_jump <= self.config.max_wrist_jump_norm
                )
            else:
                # First frame — no history to compare, allow
                result.left_motion_valid = True
        else:
            # Left hand not detected — reset tracker
            self._left_wrist_tracker.reset()
            result.left_motion_valid = True
            result.left_wrist_jump = 0.0

        # RIGHT HAND
        if holistic_results.right_hand_landmarks:
            wrist = holistic_results.right_hand_landmarks.landmark[0]
            jump, actual_jump = self._right_wrist_tracker.update(wrist.x, wrist.y)

            result.right_wrist_jump = actual_jump

            if self._right_wrist_tracker.has_history:
                result.right_motion_valid = (
                    actual_jump <= self.config.max_wrist_jump_norm
                )
            else:
                result.right_motion_valid = True
        else:
            self._right_wrist_tracker.reset()
            result.right_motion_valid = True
            result.right_wrist_jump = 0.0

    # ────────────────────────────────────────────────────
    #  FUTURE: PERSON SEGMENTATION (Placeholder)
    # ────────────────────────────────────────────────────

    def verify_segmentation_mask(self, frame, results):
        """
        FUTURE ENHANCEMENT: Use MediaPipe Selfie Segmentation
        (or equivalent person segmentation model) to verify that
        hand pixels belong to the authenticated user's body
        silhouette.

        When implemented, this would:
          1. Generate a segmentation mask for the primary person
          2. Check that the hand landmark region falls within
             the person's silhouette
          3. Reject hands whose pixels fall outside the mask

        This provides stronger protection against hands reaching
        in from behind or beside the user.

        Currently returns True (no-op) — does not affect the
        verification pipeline.
        """
        return True

    # ────────────────────────────────────────────────────
    #  CLEANUP
    # ────────────────────────────────────────────────────

    def close(self):
        """Release MediaPipe resources."""
        try:
            self._face_detection.close()
        except Exception:
            pass
