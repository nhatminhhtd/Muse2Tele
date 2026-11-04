# -*- coding: utf-8 -*-
"""
Ma QR chuyen khoan VietQR (chuan EMVCo / NAPAS 247), tao ngay tren may: app ngan hang nao cung quet duoc.
img.vietqr.io chi tra ve SVG nen Telegram khong gui lam anh duoc.
"""

import io

import qrcode
from qrcode.image.pure import PyPNGImage

BANK_BIN = {"VIB": "970441"}


def _tlv(tag, value):
    return f"{tag}{len(value):02d}{value}"


def _crc16(data):
    crc = 0xFFFF  # CRC-16/CCITT-FALSE
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def payload(bank, account, amount, info):
    """Chuoi VietQR: chuyen amount dong toi account (ngan hang bank), noi dung info."""
    beneficiary = _tlv("00", BANK_BIN[bank]) + _tlv("01", account)
    merchant = _tlv("00", "A000000727") + _tlv("01", beneficiary) + _tlv("02", "QRIBFTTA")
    data = (_tlv("00", "01") + _tlv("01", "12") + _tlv("38", merchant) + _tlv("53", "704")
            + _tlv("54", str(int(amount))) + _tlv("58", "VN") + _tlv("62", _tlv("08", info)) + "6304")
    return data + _crc16(data)


def png(bank, account, amount, info):
    """Anh PNG cua ma QR (bytes)."""
    img = qrcode.make(payload(bank, account, amount, info), box_size=10, border=4,
                      image_factory=PyPNGImage)  # PNG thuan Python, khong can Pillow
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue()
