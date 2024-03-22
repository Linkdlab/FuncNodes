from typing import Callable, Any, Union, Tuple, List
import json
import base64

VALID_JSON_TYPE = Union[int, float, str, bool, list, dict, type(None)]


class JSONDecoder(json.JSONDecoder):
    decoder: List[Callable[[Any], tuple[Union[VALID_JSON_TYPE, Any], bool]]] = []

    @classmethod
    def add_decoder(
        cls, dec: Callable[[Any], tuple[Union[VALID_JSON_TYPE, Any], bool]]
    ):
        cls.decoder.append(dec)

    def decode(self, s: str):
        res = super().decode(s)
        for dec in JSONDecoder.decoder:
            res, handled = dec(res)
            if handled:
                return res
        return res


class JSONEncoder(json.JSONEncoder):
    encoder: List[Callable[[Any], tuple[Union[VALID_JSON_TYPE, Any], bool]]] = []

    @classmethod
    def add_encoder(
        cls, enc: Callable[[Any], tuple[Union[VALID_JSON_TYPE, Any], bool]]
    ):
        cls.encoder.append(enc)

    @classmethod
    def apply_custom_encoding(cls, obj):
        """
        Recursively apply custom encoding to an object, using the encoders defined in JSONEncoder.
        """
        if isinstance(obj, (int, float, str, bool, type(None))):
            # Base types
            return obj
        elif isinstance(obj, dict):
            # Handle dictionaries
            return {key: cls.apply_custom_encoding(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            # Handle lists
            return [cls.apply_custom_encoding(item) for item in obj]
        elif isinstance(obj, (set, tuple)):
            # Convert sets and tuples to lists
            return [cls.apply_custom_encoding(item) for item in obj]
        else:
            # Attempt to apply custom encodings
            for enc in cls.encoder:
                res, handled = enc(obj)
                if handled:
                    return cls.apply_custom_encoding(res)

        return obj

    def default(self, obj):
        for enc in JSONEncoder.encoder:
            res, handled = enc(obj)
            if handled:
                return res
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def _repr_json_(obj):
    if hasattr(obj, "_repr_json_"):
        return obj._repr_json_(), True
    return obj, False


JSONEncoder.add_encoder(_repr_json_)


def default_encodings(obj):
    if isinstance(obj, (tuple, set)):
        return list(obj), True
    if isinstance(obj, bytes):
        # Convert bytes to base64 string
        return base64.b64encode(obj).decode("utf-8"), True
    if isinstance(obj, Exception):
        return str(obj), True

    return obj, False


JSONEncoder.add_encoder(default_encodings)


# Add image encoding
try:
    import cv2
    from PIL import Image
    import numpy as np

    def cv2_imageHandler(obj: Image.Image):
        if isinstance(obj, Image.Image):
            retval, buffer_cv2 = cv2.imencode(
                ".jpeg",
                cv2.cvtColor(np.array(obj), cv2.COLOR_RGB2BGR),
                [int(cv2.IMWRITE_JPEG_QUALITY), 50],
            )
            return buffer_cv2.tobytes(), True
        return obj, False

    JSONEncoder.add_encoder(cv2_imageHandler)
except ImportError:
    pass

try:
    from PIL import Image
    import io

    def imageHandler(obj: Image.Image):
        if isinstance(obj, Image.Image):
            buffer = io.BytesIO()
            obj.save(
                buffer, format="webp", optimize=True, quality=50
            )  # You can use 'JPEG' or other formats as needed
            buffered_img_bytes = buffer.getvalue()
            return buffered_img_bytes, True
        return obj, False

    JSONEncoder.add_encoder(imageHandler)
except ImportError:
    pass


def stringify_value(v):
    if isinstance(v, (list, tuple)):
        return ", ".join(stringify_value(vv) for vv in v)
    if isinstance(v, dict):
        try:
            return json.dumps(v, indent=2)
        except Exception:
            try:
                return json.dumps(
                    {str(k): stringify_value(vv) for k, vv in v.items()}, indent=2
                )
            except Exception:
                pass
    return str(v)


class MimeTyper:
    encoder: List[Callable[[Any], tuple[str, str, bool]]] = []

    @classmethod
    def add_encoder(cls, enc: Callable[[Any], tuple[str, str, bool]]):
        cls.encoder.append(enc)

    @classmethod
    def encode(cls, obj) -> Tuple[str, str]:
        for enc in cls.encoder:
            res, mim, handled = enc(obj)
            if handled:
                return res, mim
        return json.dumps(obj, indent=2, cls=JSONEncoder), "text/plain"


def ipython_mimer(repr_va) -> Tuple[str, str, bool]:
    if repr_va is None:
        return "null", "text/plain", True

    if hasattr(repr_va, "_repr_html_"):
        return repr_va._repr_html_(), "text/html", True
    elif hasattr(repr_va, "_repr_markdown_"):
        return repr_va._repr_markdown_(), "text/markdown", True
    elif hasattr(repr_va, "_repr_svg_"):
        return repr_va._repr_svg_(), "image/svg+xml", True
    elif hasattr(repr_va, "_repr_png_"):
        return repr_va._repr_png_(), "image/png", True
    elif hasattr(repr_va, "_repr_jpeg_"):
        return repr_va._repr_jpeg_(), "image/jpeg", True
    elif hasattr(repr_va, "_repr_json_"):
        return repr_va._repr_json_(), "application/json", True
    elif hasattr(repr_va, "_repr_pretty_"):
        return repr_va._repr_pretty_(), "text/plain", True

    return None, None, False
