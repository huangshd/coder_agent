"""
OCR Model Wrapper
Provides unified interface for OCR models (PaddleOCR, EasyOCR, etc.)
"""

from typing import List, Optional, Tuple, Dict, Any


class OCRModel:
    """
    Wrapper for OCR (Optical Character Recognition) models.
    Supports: PaddleOCR, EasyOCR, Tesseract, etc.
    """

    def __init__(self, model_type: str = "paddleocr", language: str = "en",
                 device: str = "cpu", use_gpu: bool = False):
        """
        Initialize OCR model.

        Args:
            model_type: OCR library to use ("paddleocr", "easyocr", etc.)
            language: Language code(s) for OCR
            device: Device to use ("cpu", "cuda", etc.)
            use_gpu: Whether to use GPU
        """
        self.model_type = model_type
        self.language = language
        self.device = device
        self.use_gpu = use_gpu
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the OCR model"""
        if self.model_type == "paddleocr":
            try:
                from paddleocr import PaddleOCR
                self.model = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.language,
                    use_gpu=self.use_gpu,
                )
            except ImportError:
                raise ImportError("Please install paddleocr: pip install paddleocr")

        elif self.model_type == "easyocr":
            try:
                import easyocr
                self.model = easyocr.Reader(
                    [self.language],
                    gpu=self.use_gpu
                )
            except ImportError:
                raise ImportError("Please install easyocr: pip install easyocr")
        else:
            raise ValueError(f"Unsupported OCR model: {self.model_type}")

    def extract_text(self, image_path: str) -> str:
        """
        Extract text from image.

        Args:
            image_path: Path to image file

        Returns:
            Extracted text
        """
        result = self.extract_text_with_boxes(image_path)
        return "\n".join([text for _, text in result])

    def extract_text_with_boxes(self, image_path: str) -> List[Tuple[List, str]]:
        """
        Extract text with bounding box information.

        Args:
            image_path: Path to image file

        Returns:
            List of (bounding_box, text) tuples
        """
        if self.model_type == "paddleocr":
            results = self.model.ocr(image_path, cls=True)
            # PaddleOCR returns nested list structure
            formatted_results = []
            for line in results:
                for box_info in line:
                    box, (text, confidence) = box_info
                    formatted_results.append((box, text))
            return formatted_results

        elif self.model_type == "easyocr":
            results = self.model.readtext(image_path)
            # EasyOCR returns list of (box, text, confidence) tuples
            formatted_results = []
            for box, text, confidence in results:
                formatted_results.append((box, text))
            return formatted_results

    def extract_text_with_confidence(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Extract text with confidence scores.

        Args:
            image_path: Path to image file

        Returns:
            List of dicts with text, confidence, and bounding box
        """
        if self.model_type == "paddleocr":
            results = self.model.ocr(image_path, cls=True)
            formatted_results = []
            for line in results:
                for box_info in line:
                    box, (text, confidence) = box_info
                    formatted_results.append({
                        "text": text,
                        "confidence": confidence,
                        "box": box
                    })
            return formatted_results

        elif self.model_type == "easyocr":
            results = self.model.readtext(image_path)
            formatted_results = []
            for box, text, confidence in results:
                formatted_results.append({
                    "text": text,
                    "confidence": confidence,
                    "box": box
                })
            return formatted_results

    def batch_extract_text(self, image_paths: List[str]) -> List[str]:
        """
        Extract text from multiple images.

        Args:
            image_paths: List of image file paths

        Returns:
            List of extracted text strings
        """
        results = []
        for image_path in image_paths:
            text = self.extract_text(image_path)
            results.append(text)
        return results

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the OCR model"""
        return {
            "type": self.model_type,
            "language": self.language,
            "device": self.device,
            "gpu_enabled": self.use_gpu
        }
