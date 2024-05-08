"""Frontend for working with data"""

from funcnodes import Node, NodeInput, NodeOutput
from funcnodes.lib import module_to_shelf
import sys
import requests


class FileDownloadNode(Node):
    """
    Downloads a file from a given URL and returns the file's content as bytes.
    """

    node_id = "file_dload"
    node_name = "File Download"

    url = NodeInput(id="url", type="str")
    timeout = NodeInput(id="timeout", type="float", default=10)

    data = NodeOutput(id="data", type=bytes)

    async def func(self, url: str, timeout: float) -> None:
        """
        Downloads a file from a given URL and sets the "data" output to the file's content as bytes.

        Args:
          url (str): The URL of the file to download.
          timeout (float): The timeout in seconds for the download request.
        """
        response = requests.get(url, timeout=timeout)
        self.outputs["data"].value = response.content


class BytesToStringNode(Node):
    """
    Converts bytes to a string using the specified encoding.

    Args:
      data (bytes): The bytes to convert to a string.
      encoding (str): The encoding to use for the conversion. Defaults to "utf-8".
    """

    node_id = "bytes_to_str"
    node_name = "Bytes to String"

    data = NodeInput(id="data", type=bytes)
    encoding = NodeInput(
        id="encoding",
        type=str,
        default="utf-8",
        value_options=[
            "ascii",
            "big5",
            "big5hkscs",
            "cp037",
            "cp273",
            "cp424",
            "cp437",
            "cp500",
            "cp720",
            "cp737",
            "cp775",
            "cp850",
            "cp852",
            "cp855",
            "cp856",
            "cp857",
            "cp858",
            "cp860",
            "cp861",
            "cp862",
            "cp863",
            "cp864",
            "cp865",
            "cp866",
            "cp869",
            "cp874",
            "cp875",
            "cp932",
            "cp949",
            "cp950",
            "cp1006",
            "cp1026",
            "cp1125",
            "cp1140",
            "cp1250",
            "cp1251",
            "cp1252",
            "cp1253",
            "cp1254",
            "cp1255",
            "cp1256",
            "cp1257",
            "cp1258",
            "euc_jp",
            "euc_jis_2004",
            "euc_jisx0213",
            "euc_kr",
            "gb2312",
            "gbk",
            "gb18030",
            "hz",
            "iso2022_jp",
            "iso2022_jp_1",
            "iso2022_jp_2",
            "iso2022_jp_2004",
            "iso2022_jp_3",
            "iso2022_jp_ext",
            "iso2022_kr",
            "latin_1",
            "iso8859_2",
            "iso8859_3",
            "iso8859_4",
            "iso8859_5",
            "iso8859_6",
            "iso8859_7",
            "iso8859_8",
            "iso8859_9",
            "iso8859_10",
            "iso8859_11",
            "iso8859_13",
            "iso8859_14",
            "iso8859_15",
            "iso8859_16",
            "johab",
            "koi8_r",
            "koi8_t",
            "koi8_u",
            "kz1048",
            "mac_cyrillic",
            "mac_greek",
            "mac_iceland",
            "mac_latin2",
            "mac_roman",
            "mac_turkish",
            "ptcp154",
            "shift_jis",
            "shift_jis_2004",
            "shift_jisx0213",
            "utf_32",
            "utf_32_be",
            "utf_32_le",
            "utf_16",
            "utf_16_be",
            "utf_16_le",
            "utf_7",
            "utf_8",
            "utf_8_sig",
        ],
    )
    string = NodeOutput(id="string", type=str)

    async def func(self, data: bytes, encoding: str) -> None:
        """
        Converts bytes to a string using the specified encoding and sets the "string" output to the result.

        Args:
          data (bytes): The bytes to convert to a string.
          encoding (str): The encoding to use for the conversion.
        """
        self.outputs["string"].value = data.decode(encoding, errors="replace")


NODE_SHELF = module_to_shelf(sys.modules[__name__], name="files")
