import struct

try:
    import engine_link
except Exception:
    engine_link = None

# Packet format: magic(2B 'SK'), x(h), y(h), facing(b), weapon_idx(B), hp(B), firing(B), sector_idx(B), score(H) = 13 bytes
PKT_FMT = "<2shhbBBBBH"
PKT_SIZE = struct.calcsize(PKT_FMT)


def _on_link_connected():
    if engine_link is not None:
        try:
            engine_link.clear_send()
            engine_link.clear_read()
        except Exception:
            pass


class LinkManager:
    def __init__(self):
        self.enabled = False
        self.mock = None
        self._rx_buf = bytearray(PKT_SIZE)
        self.remote_x = 0.0
        self.remote_y = 24.0
        self.remote_facing = 1
        self.remote_weapon = 0
        self.remote_hp = 5
        self.remote_firing = False
        self.remote_sector = 0
        self.remote_score = 0
        self.remote_seen = False

    def start(self):
        self.enabled = True
        self.remote_seen = False
        if self.mock is not None:
            return
        if engine_link is not None:
            try:
                engine_link.set_connected_cb(_on_link_connected)
                if not engine_link.is_started():
                    engine_link.start()
            except Exception as e:
                print("WARN: engine_link start failed:", e)

    def stop(self):
        self.enabled = False
        self.remote_seen = False
        if self.mock is not None:
            return
        if engine_link is not None:
            try:
                if engine_link.is_started():
                    engine_link.stop()
            except Exception:
                pass

    def is_connected(self):
        if not self.enabled:
            return False
        if self.mock is not None:
            return self.mock.connected()
        if engine_link is None:
            return False
        try:
            return bool(engine_link.connected())
        except Exception:
            return False

    def is_host(self):
        if self.mock is not None:
            return self.mock.is_host()
        if engine_link is None:
            return True
        try:
            return bool(engine_link.is_host())
        except Exception:
            return True

    def sync(self, px, py, facing, weapon_idx, hp, firing, sector_idx, score):
        if not self.enabled:
            return
        pkt = bytearray(struct.pack(
            PKT_FMT,
            b"SK",
            int(px * 10.0),
            int(py * 10.0),
            1 if facing >= 0 else -1,
            weapon_idx & 0xFF,
            max(0, min(255, int(hp))),
            1 if firing else 0,
            sector_idx & 0xFF,
            max(0, min(65535, int(score))),
        ))
        link = self.mock if self.mock is not None else engine_link
        if link is None:
            return
        try:
            if link.connected():
                link.send(pkt)
                while link.available() >= PKT_SIZE:
                    if self.mock is not None:
                        raw = link.read(PKT_SIZE)
                    else:
                        link.read_into(self._rx_buf, PKT_SIZE)
                        raw = self._rx_buf
                    if raw and len(raw) == PKT_SIZE and raw[0:2] == b"SK":
                        _, rx, ry, rf, rw, rhp, rfire, rsec, rsc = struct.unpack(PKT_FMT, raw)
                        self.remote_x = rx * 0.1
                        self.remote_y = ry * 0.1
                        self.remote_facing = rf
                        self.remote_weapon = rw
                        self.remote_hp = rhp
                        self.remote_firing = bool(rfire)
                        self.remote_sector = rsec
                        self.remote_score = rsc
                        self.remote_seen = True
        except Exception:
            pass
