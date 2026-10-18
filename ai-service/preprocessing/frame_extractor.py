import cv2
import numpy as np
from typing import List
from utils.logging_utils import logger

class FrameExtractor:
    """
    OpenCV video frame extraction tool for temporal deepfake sequence analysis.
    """
    def extract_uniform_frames(self, video_path: str, max_frames: int = 16) -> List[np.ndarray]:
        """
        Extract up to max_frames uniformly sampled frames from a video file.
        """
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"FrameExtractor unable to open video stream at: {video_path}")
            return frames

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            logger.warning("Video file reported 0 total frames.")
            cap.release()
            return frames

        # Calculate sample step interval
        step = max(1, total_frames // max_frames)
        current_frame = 0

        while cap.isOpened() and len(frames) < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            
            frames.append(frame)
            current_frame += step

        cap.release()
        logger.info(f"FrameExtractor extracted {len(frames)} frames from total {total_frames} video frames.")
        return frames

frame_extractor = FrameExtractor()
