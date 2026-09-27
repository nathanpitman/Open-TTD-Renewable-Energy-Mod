#!/usr/bin/env python3
"""
Minimal reader for 8bpp sprites in a compiled GRF (container version 2),
enough to pull base-set sprites such as OpenGFX's out of `ogfx1_base.grf`.

Only what the vanilla comparison needs is supported: normal-zoom (1x),
8bpp palette sprites, both plain and "chunked" (transparency) encodings.
Sprite numbers are positions in the GRF's data section, which for a base
set are the base sprite numbers OpenTTD uses.
"""

import struct

from PIL import Image

MAGIC_V2 = b"\x00\x00GRF\x82\x0d\x0a\x1a\x0a"
INFO_PAL = 0x04
INFO_CHUNKED = 0x08


class Sprite:
    def __init__(self, image, xoff, yoff):
        self.image, self.xoff, self.yoff = image, xoff, yoff


def _lz77(data, pos, size):
    """GRF (LZ77-like) decompression of `size` output bytes."""
    out = bytearray()
    while len(out) < size:
        code = data[pos]
        pos += 1
        if code & 0x80:
            length = 16 - ((code >> 3) & 0x0F)  # -(signed code >> 3)
            offset = ((code & 7) << 8) | data[pos]
            pos += 1
            start = len(out) - offset
            for k in range(length):
                out.append(out[start + k])
        else:
            length = code or 0x80
            out += data[pos:pos + length]
            pos += length
    return bytes(out[:size])


def _unchunk(raw, w, h):
    """Decode the chunked (transparency) sprite encoding to w*h indices."""
    px = bytearray(w * h)
    wide = len(raw) > 0xFFFF
    osz = 4 if wide else 2
    big = w > 256
    for row in range(h):
        (off,) = struct.unpack_from("<I" if wide else "<H", raw, row * osz)
        while True:
            if big:
                hdr, x = struct.unpack_from("<HH", raw, off)
                off += 4
                last, n = hdr & 0x8000, hdr & 0x7FFF
            else:
                hdr, x = raw[off], raw[off + 1]
                off += 2
                last, n = hdr & 0x80, hdr & 0x7F
            px[row * w + x:row * w + x + n] = raw[off:off + n]
            off += n
            if last:
                break
    return bytes(px)


class GRF:
    def __init__(self, path, palette):
        self.data = open(path, "rb").read()
        self.palette = palette
        if not self.data.startswith(MAGIC_V2):
            raise ValueError("%s: only GRF container version 2 is supported" % path)
        (sprite_off,) = struct.unpack_from("<I", self.data, 10)
        pos = 15
        # data section: sprite number -> sprite id (None for pseudo sprites)
        self.ids = []
        while True:
            (size,) = struct.unpack_from("<I", self.data, pos)
            pos += 4
            if size == 0:
                break
            kind = self.data[pos]
            if kind == 0xFD:
                self.ids.append(struct.unpack_from("<I", self.data, pos + 1)[0])
            else:
                self.ids.append(None)
            pos += 1 + size
        # sprite section: id -> offset of its normal-zoom 8bpp entry
        self.index = {}
        pos = 14 + sprite_off
        while pos + 4 <= len(self.data):
            (sid,) = struct.unpack_from("<I", self.data, pos)
            if sid == 0:
                break
            size, info = struct.unpack_from("<IB", self.data, pos + 4)
            if info & INFO_PAL and self.data[pos + 9] == 0 and sid not in self.index:
                self.index[sid] = pos + 8
            pos += 8 + size

    def __len__(self):
        return len(self.ids)

    def sprite(self, number):
        """Base sprite `number` as a Sprite (palette image + offsets), or None."""
        sid = self.ids[number] if 0 <= number < len(self.ids) else None
        pos = self.index.get(sid)
        if pos is None:
            return None
        info = self.data[pos]
        h, w, xoff, yoff = struct.unpack_from("<HHhh", self.data, pos + 2)
        pos += 10
        if info & INFO_CHUNKED:
            (size,) = struct.unpack_from("<I", self.data, pos)
            px = _unchunk(_lz77(self.data, pos + 4, size), w, h)
        else:
            px = _lz77(self.data, pos, w * h)
        im = Image.frombytes("P", (w, h), px)
        im.putpalette(self.palette)
        return Sprite(im, xoff, yoff)
