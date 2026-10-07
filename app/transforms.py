"""Transformaciones invertibles sobre bytes usadas por los retos y el modelo local."""

import base64


def _shift_letters(data: bytes, k: int) -> bytes:
    out = bytearray()
    for b in data:
        if 65 <= b <= 90:
            out.append((b - 65 + k) % 26 + 65)
        elif 97 <= b <= 122:
            out.append((b - 97 + k) % 26 + 97)
        else:
            out.append(b)
    return bytes(out)


def _atbash(data: bytes) -> bytes:
    return bytes(155 - b if 65 <= b <= 90 else 219 - b if 97 <= b <= 122 else b for b in data)


def apply(op: str, p: int, data: bytes) -> bytes:
    match op:
        case "base64": return base64.b64encode(data)
        case "base32": return base64.b32encode(data)
        case "hex": return data.hex().encode()
        case "rot13": return _shift_letters(data, 13)
        case "caesar": return _shift_letters(data, p)
        case "atbash": return _atbash(data)
        case "reverse": return data[::-1]
        case "xor": return bytes(b ^ p for b in data)
    raise ValueError(op)


def invert(op: str, p: int, data: bytes) -> bytes:
    match op:
        case "base64": return base64.b64decode(data)
        case "base32": return base64.b32decode(data)
        case "hex": return bytes.fromhex(data.decode())
        case "caesar": return _shift_letters(data, -p)
        case "rot13" | "atbash" | "reverse" | "xor": return apply(op, p, data)
    raise ValueError(op)
