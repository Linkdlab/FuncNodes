from .serialization import JSONEncoder
import base64


class databytes(bytes):
    """
    A subclass of bytes that is not fully encoded in preview.
    """

    pass


def databytes_handler(obj, preview=False):
    """
    Encodes bytes objects to base64 strings.
    """
    if isinstance(obj, databytes):
        # Convert bytes to base64 string

        return f"databytes({len(obj)})", True
        # return base64.b64encode(obj).decode("utf-8"), True
    return obj, False


JSONEncoder.add_encoder(databytes_handler, enc_cls=[databytes])
