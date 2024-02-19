from typing import Callable, Any, Union, Tuple, List
import json

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
        return obj.decode(), True
    if isinstance(obj, Exception):
        return str(obj), True

    return obj, False


JSONEncoder.add_encoder(default_encodings)

try:
    import numpy as np

    def from_np(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist(), True
        return obj, False

    JSONEncoder.add_encoder(from_np)
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
