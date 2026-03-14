from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - depends on runtime environment
    cv2 = None


@dataclass(frozen=True)
class FaceBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2


class FaceService:
    def __init__(self) -> None:
        self._available = cv2 is not None
        self._cascade = None

        if not self._available:
            return

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            self._available = False
            return

        self._cascade = cascade

    @property
    def available(self) -> bool:
        return self._available and self._cascade is not None

    def detect_largest_face(self, rgb: np.ndarray) -> FaceBox | None:
        if not self.available or rgb.size == 0:
            return None

        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        scale = 1.0

        max_side = max(gray.shape[0], gray.shape[1])
        if max_side > 900:
            scale = 900 / max_side
            gray = cv2.resize(gray, (round(gray.shape[1] * scale), round(gray.shape[0] * scale)))

        faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
        )

        if len(faces) == 0:
            return None

        x, y, w, h = max(faces, key=lambda box: int(box[2]) * int(box[3]))
        inv = 1.0 / scale
        return FaceBox(
            x=int(round(x * inv)),
            y=int(round(y * inv)),
            width=int(round(w * inv)),
            height=int(round(h * inv)),
        )


face_service = FaceService()
