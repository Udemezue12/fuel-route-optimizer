import gzip
import json


def compress_data(data: dict) -> bytes:
    return gzip.compress(json.dumps(data).encode("utf-8"))


def decompress_data(data: bytes) -> dict:
    return json.loads(gzip.decompress(data).decode("utf-8"))