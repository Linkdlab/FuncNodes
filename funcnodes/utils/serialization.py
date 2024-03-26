from typing import Callable, Any, Union, Tuple, List, Literal
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


encodertyoe = Callable[
    [Any, bool],
    Union[tuple[Any, Literal[True]], tuple[Any, Literal[False]]],
]


class JSONEncoder(json.JSONEncoder):
    encoder: List[encodertyoe] = []

    default_preview = False

    @classmethod
    def add_encoder(cls, enc: encodertyoe):
        cls.encoder.append(enc)

    @classmethod
    def apply_custom_encoding(cls, obj, preview=False):
        """
        Recursively apply custom encoding to an object, using the encoders defined in JSONEncoder.
        """
        if isinstance(obj, (int, float, str, bool, type(None))):
            # Base types
            return obj
        elif isinstance(obj, dict):
            # Handle dictionaries
            return {key: cls.apply_custom_encoding(value) for key, value in obj.items()}
        elif isinstance(obj, (set, tuple, list)):
            # Handle lists
            obj = list(obj)
            if preview:
                return [cls.apply_custom_encoding(item, preview) for item in obj[:10]]
            return [cls.apply_custom_encoding(item) for item in obj]
        else:
            # Attempt to apply custom encodings
            for enc in cls.encoder:
                res, handled = enc(obj, preview)
                if handled:
                    return cls.apply_custom_encoding(res)

        return obj

    def default(self, obj):
        try:
            return super().default(
                self.apply_custom_encoding(obj, self.default_preview)
            )
        except TypeError:
            return str(obj)


class PreviewJSONEncoder(JSONEncoder):
    default_preview = True


def _repr_json_(obj, preview=False):
    if hasattr(obj, "_repr_json_"):
        return obj._repr_json_(), True
    return obj, False


JSONEncoder.add_encoder(_repr_json_)


def default_encodings(obj, preview=False):
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

    def cv2_imageHandler(obj: Image.Image, preview=False):
        if isinstance(obj, Image.Image):

            if preview:
                obj.thumbnail((200, 200))

            aobj = np.array(obj)

            retval, buffer_cv2 = cv2.imencode(
                ".jpeg",
                cv2.cvtColor(aobj, cv2.COLOR_RGB2BGR),
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

    def imageHandler(obj: Image.Image, preview=False):
        if isinstance(obj, Image.Image):
            if preview:
                obj.thumbnail((200, 200))

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
