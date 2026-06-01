"""TransNetV2 shot boundary detection backend for VAClip.

Provides GPU-accelerated (CUDA) and CPU fallback shot detection
using the TransNetV2 model. Returns a list of shot boundaries as
(start_time, end_time) tuples in seconds.

Agent Instructions:
    - Implement the TODO sections in ShotDetector.detect()
    - Use torch.hub or local file to load TransNetV2 model
    - Process video in batches to avoid OOM
    - Return list[tuple[float, float]] for shot boundaries
    - Log via structlog with get_logger()
    - See docs/agents/segmentation_agent.md for full implementation guide
"""
from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore
    OPENCV_AVAILABLE = False

import numpy as np
import torch

from vaclip.logging.setup import get_logger
from vaclip.utils.exceptions import VaClipSegmentationError

if TYPE_CHECKING:

    from vaclip.config.settings import Settings

log = get_logger(__name__)


class ShotDetector:
    """GPU-accelerated shot detection backend using TransNetV2 + CUDA.

    Targets RTX 3060 (12GB VRAM) with TransNetV2 model.
    Downloads model weights on first use to the configured models directory.

    Attributes:
        MODEL_NAME: Default TransNetV2 model identifier.
        DEVICE: Compute device ("cuda" or "cpu").
        INPUT_SIZE: Expected input frame size for the model.
        THRESHOLD: Threshold for shot boundary prediction.

    Example::

        detector = ShotDetector()
        shots = detector.detect(Path("cache/video/abc123.mp4"))
        print(len(shots))  # number of shots
    """

    MODEL_NAME: str = "transnetv2-pytorch"
    DEVICE: str = "cuda"
    INPUT_SIZE: tuple[int, int] = (256, 256)  # Height, Width
    THRESHOLD: float = 0.5
    MODELS_DIR: str = "models"

    def __init__(self, model_name: Optional[str] = None) -> None:
        """Initialize the shot detector.

        Args:
            model_name: Override the default model identifier.
        """
        self._model_name = model_name or self.MODEL_NAME
        self._model = None  # lazy-loaded on first detect call
        self._device = torch.device(self.DEVICE if torch.cuda.is_available() else "cpu")
        if self._device.type == "cpu":
            log.warning(
                "shot_detector.cuda_unavailable",
                fallback="cpu",
                note="Install PyTorch with CUDA support for better performance",
            )

    def _load_model(self) -> None:
        """Lazy-load the TransNetV2 model to avoid startup delay.

        Raises:
            VaClipSegmentationError: If the model fails to load.
        """
        if self._model is not None:
            return
        log.info(
            "shot_detector.model_loading",
            model=self._model_name,
            device=self._device.type,
        )
        try:
            from vaclip.config.settings import get_settings
            settings = get_settings()
            model_dir = settings.paths.models_dir / "transnetv2"
            model_def_path = model_dir / "model.py"
            model_weights_path = model_dir / "transnetv2_weights.pth"
            if not model_def_path.exists():
                raise VaClipSegmentationError(
                    f"TransNetV2 model definition not found at {model_def_path}. "
                    "Please ensure the model definition is present."
                )
            if not model_weights_path.exists():
                raise VaClipSegmentationError(
                    f"TransNetV2 model weights not found at {model_weights_path}. "
                    "Please ensure the model weights are present."
                )
            # Import the model from the given file
            spec = importlib.util.spec_from_file_location("transnetv2_model", model_def_path)
            model_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(model_module)
            # Assume the model class is named TransNetV2
            model_class = getattr(model_module, "TransNetV2")
            model = model_class()
            # Load weights
            state_dict = torch.load(model_weights_path, map_location=self._device)
            model.load_state_dict(state_dict)
            model.to(self._device)
            model.eval()
            self._model = model
        except Exception as exc:
            log.error("shot_detector.model_load_failed", model=self._model_name, error=str(exc))
            raise VaClipSegmentationError(f"Failed to load TransNetV2 model: {exc}") from exc

    def _extract_frames(self, video_path: str, target_fps: float) -> tuple[list[np.ndarray], float]:
        """Extract frames from video at specified FPS.
        
        Args:
            video_path: Path to video file
            target_fps: Target frames per second to extract
            
        Returns:
            Tuple of (list of frames as numpy arrays, actual video FPS)
        """
        if not OPENCV_AVAILABLE:
            raise VaClipSegmentationError(
                "OpenCV is required for shot detection but is not installed. "
                "Please install opencv-python to use the TransNetV2 shot detector."
            )

        video_capture = cv2.VideoCapture(video_path)
        if not video_capture.isOpened():
            raise VaClipSegmentationError(f"Could not open video file: {video_path}")

        video_fps = video_capture.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = 30.0  # fallback default when FPS cannot be determined

        # Calculate frame interval to achieve target FPS from source video
        frame_interval = max(1, int(round(video_fps / target_fps)))

        frames = []
        frame_count = 0

        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                # OpenCV loads images in BGR format, convert to RGB for model
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)

            frame_count += 1

        video_capture.release()
        return frames, video_fps

    def _apply_threshold_and_nms(self, predictions: np.ndarray, threshold: float, video_fps: float) -> list[tuple[float, float]]:
        """Apply threshold and non-maximum suppression to get shot boundaries.
        
        Args:
            predictions: Array of shot probabilities for each frame
            threshold: Threshold for shot detection
            video_fps: Frames per second of the video
            
        Returns:
            List of (start_time, end_time) tuples in seconds
        """
        # Find frames where prediction exceeds threshold (potential shot boundaries)
        shot_frames = np.where(predictions > threshold)[0]

        if len(shot_frames) == 0:
            return []

        # Group consecutive frames into continuous shot segments
        shots = []
        current_shot_start = shot_frames[0]
        current_shot_end = shot_frames[0]

        for i in range(1, len(shot_frames)):
            if shot_frames[i] == shot_frames[i-1] + 1:
                # Frames are consecutive, part of the same shot
                current_shot_end = shot_frames[i]
            else:
                # Gap detected, current shot has ended
                shots.append((current_shot_start, current_shot_end))
                current_shot_start = shot_frames[i]
                current_shot_end = shot_frames[i]

        # Don't forget to add the last shot segment
        shots.append((current_shot_start, current_shot_end))

        # Convert frame indices to time values and ensure minimum shot length
        shot_boundaries = []
        min_frames = max(1, int(round(video_fps * 0.5)))  # Minimum 0.5 second shot

        for start_frame, end_frame in shots:
            # Extend shot boundaries slightly to include transition frames
            extended_start = max(0, start_frame - 1)
            extended_end = min(len(predictions) - 1, end_frame + 1)

            # Ensure minimum shot length by centering and extending if needed
            if (extended_end - extended_start) < min_frames:
                # Center the shot and extend to minimum length
                center = (start_frame + end_frame) // 2
                half_min = min_frames // 2
                extended_start = max(0, center - half_min)
                extended_end = min(len(predictions) - 1, center + half_min)

            start_time = extended_start / video_fps
            end_time = (extended_end + 1) / video_fps  # +1 because end frame is inclusive

            shot_boundaries.append((start_time, end_time))

        return shot_boundaries

    def detect(self, video_path: str, run_id: str) -> list[tuple[float, float]]:
        """Detect shot boundaries in a video file.

        Implementations must:
        1. Load or reuse the TransNetV2 model
        2. Extract frames from the video at the required fps (TransNetV2 uses 25 fps)
        3. Process frames in batches to avoid OOM
        4. Apply the model to get shot boundary probabilities
        5. Apply threshold and NMS to get final shot boundaries
        6. Return list of (start, end) tuples in seconds
        7. Log model name, device, and duration
        8. Handle CUDA errors gracefully

        Args:
            video_path: Path to the video file.
            run_id: Run identifier for artifact grouping.

        Returns:
            List of (start, end) tuples representing shot boundaries in seconds.
        """

        log.info(
            "shot_detector.start",
            run_id=run_id,
            video_path=video_path,
            backend=self._device.type,
            model=self._model_name,
        )

        self._load_model()
        assert self._model is not None, "Model should be loaded by _load_model"

        fps = 25.0
        frames, video_fps = self._extract_frames(video_path, fps)

        if not frames:
            log.warning(
                "shot_detector.no_frames_extracted",
                run_id=run_id,
                video_path=video_path,
            )
            return []

        batch_size = 16
        all_predictions = []

        for start_idx in range(0, len(frames), batch_size):
            end_idx = min(start_idx + batch_size, len(frames))
            batch_frames = frames[start_idx:end_idx]

            if len(batch_frames) < batch_size:
                padding_needed = batch_size - len(batch_frames)
                padding_frames = [batch_frames[-1]] * padding_needed
                batch_frames.extend(padding_frames)

            processed_batch = np.array([
                cv2.resize(frame, self.INPUT_SIZE[::-1]).astype(np.float32) / 255.0
                for frame in batch_frames
            ])

            input_tensor = torch.from_numpy(processed_batch).unsqueeze(0).to(self._device)

            with torch.no_grad():
                model_output = self._model(input_tensor)
                shot_probabilities = model_output[:, :, 1].cpu().numpy()[0]

                actual_batch_size = end_idx - start_idx
                all_predictions.extend(shot_probabilities[:actual_batch_size])

        shot_boundaries = self._apply_threshold_and_nms(
            np.array(all_predictions),
            self.THRESHOLD,
            video_fps
        )

        log.info(
            "shot_detector.detection_complete",
            run_id=run_id,
            num_frames=len(frames),
            num_shots=len(shot_boundaries),
            video_fps=video_fps,
        )

        return shot_boundaries


def get_shot_detector(
    settings: Optional[Settings] = None,
) -> ShotDetector:
    """Return the shot detector for the current hardware.

    Auto-detects CUDA availability and returns ShotDetector accordingly.

    Args:
        settings: Optional settings object. Loads from config if None.

    Returns:
        An initialized shot detector ready for use.
    """
    if settings is None:
        from vaclip.config.settings import get_settings
        settings = get_settings()

    # We don't have different backends for CPU/GPU in this wrapper because
    # the model loading already handles device placement via torch.device.
    # However, we could have different model precisions if needed.
    return ShotDetector()
