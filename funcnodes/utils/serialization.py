from typing import Callable, Any, Union, Tuple, List, Literal, Dict, Optional
import json
import base64


VALID_JSON_TYPE = Union[int, float, str, bool, list, dict, type(None)]


class JSONDecoder(json.JSONDecoder):
    """
    Custom JSON decoder that uses a list of decoders to decode JSON objects.

    Args:
      object_hook (Callable): A function that will be called with the result of any object literal decoded (a dict). The return value of object_hook will be used instead of the dict. This feature can be used to implement custom decoders (e.g. JSON-RPC class hinting).

    Examples:
      >>> JSONDecoder().decode('{"__complex__": true}', object_hook=complex_decoder)
      (1+2j)
    """

    decoder: List[Callable[[VALID_JSON_TYPE], tuple[Any, bool]]] = []

    def __init__(self, *args, **kwargs) -> None:
        """
        Initializes a new JSONDecoder object.
        """
        kwargs["object_hook"] = JSONDecoder._object_hook
        super().__init__(*args, **kwargs)

    @classmethod
    def add_decoder(cls, dec: Callable[[VALID_JSON_TYPE], tuple[Any, bool]]):
        """
        Adds a new decoder to the list of decoders.

        Args:
          dec (Callable[[VALID_JSON_TYPE], tuple[Any, bool]]): A function that takes in a valid JSON type and returns a tuple containing the decoded object and a boolean indicating whether or not the object was decoded.

        Examples:
          >>> JSONDecoder.add_decoder(complex_decoder)
        """
        cls.decoder.append(dec)

    @classmethod
    def _object_hook(cls, obj: VALID_JSON_TYPE):
        """"""
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                obj[key] = cls._object_hook(obj[key])
            return obj
        elif isinstance(obj, list):
            obj = [cls._object_hook(item) for item in obj]
            return obj

        for dec in JSONDecoder.decoder:
            res, handled = dec(obj)
            if handled:
                return res
        return obj


encodertype = Callable[
    [Any, bool],
    tuple[Any, bool],
]


class JSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that uses a list of encoders to encode JSON objects.
    """

    encoder_registry: Dict[type, List[encodertype]] = {}

    default_preview = False

    @classmethod
    def add_encoder(cls, enc: encodertype, enc_cls: Optional[List[type]] = None):
        """
        Adds a new encoder to the list of encoders.

        Args:
          enc (encodertyoe): A function that takes in an object and a boolean indicating whether or not to use a default preview and returns a tuple containing the encoded object and a boolean indicating whether or not the object was encoded.

        Examples:
          >>> def complex_encoder(obj, preview=False):
          ...     if isinstance(obj, complex):
          ...         return {"__complex__": True}, True
          ...     return obj, False
          >>> JSONEncoder.add_encoder(complex_encoder)
        """
        if enc_cls is None:
            enc_cls = [object]
        for _enc_cls in enc_cls:
            if _enc_cls not in cls.encoder_registry:
                cls.encoder_registry[_enc_cls] = []
            cls.encoder_registry[_enc_cls].append(enc)

    @classmethod
    def prepend_encoder(cls, enc: encodertype, enc_cls: Optional[List[type]] = None):
        """
        Adds a new encoder to the list of encoders.

        Args:
          enc (encodertyoe): A function that takes in an object and a boolean indicating whether or not to use a default preview and returns a tuple containing the encoded object and a boolean indicating whether or not the object was encoded.

        Examples:
          >>> def complex_encoder(obj, preview=False):
          ...     if isinstance(obj, complex):
          ...         return {"__complex__": True}, True
          ...     return obj, False
          >>> JSONEncoder.add_encoder(complex_encoder)
        """
        if enc_cls is None:
            enc_cls = [object]
        for _enc_cls in enc_cls:
            if _enc_cls not in cls.encoder_registry:
                cls.encoder_registry[_enc_cls] = []
            cls.encoder_registry[_enc_cls].insert(0, enc)

    @classmethod
    def apply_custom_encoding(cls, obj, preview=False):
        """
        Recursively apply custom encoding to an object, using the encoders defined in JSONEncoder.
        """
        # Attempt to apply custom encodings
        obj_type = type(obj)
        for base in obj_type.__mro__:
            encoders = cls.encoder_registry.get(base)
            if encoders:
                for enc in encoders:
                    try:
                        res, handled = enc(obj, preview)
                        if handled:
                            return cls.apply_custom_encoding(res, preview=preview)
                    except Exception as e:
                        pass
        if isinstance(obj, (int, float, bool, type(None))):
            # convert nan to None
            if isinstance(obj, float) and obj != obj:
                return None
            # Base types
            return obj
        elif isinstance(obj, str):
            # if preview and len(obj) > 1000:
            #     return obj[:1000] + "..."
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

        # Fallback to string representation
        return str(obj)

    def default(self, obj):
        """
        Applies custom encoding to an object.

        Args:
          obj (Any): The object to be encoded.

        Returns:
          Any: The encoded object.

        Examples:
          >>> JSONEncoder.default(obj)
        """
        return self.apply_custom_encoding(obj, self.default_preview)


def _repr_json_(obj, preview=False) -> Tuple[Any, bool]:
    """
    Encodes objects that have a _repr_json_ method.
    """
    if hasattr(obj, "_repr_json_"):
        return obj._repr_json_(), True
    return obj, False


JSONEncoder.add_encoder(_repr_json_)


def bytes_handler(obj, preview=False):
    """
    Encodes bytes objects to base64 strings.
    """
    if isinstance(obj, bytes):
        # Convert bytes to base64 string
        if preview:
            return base64.b64encode(obj).decode("utf-8"), True
        return base64.b64encode(obj).decode("utf-8"), True
    return obj, False


JSONEncoder.add_encoder(bytes_handler)
