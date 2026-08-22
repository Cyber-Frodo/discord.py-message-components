"""Prueft die neue RTP-Verschluesselung des Forks ohne Discord-Verbindung.

Verschluesselt ein Paket, zerlegt es wieder und vergleicht. Faengt genau die
Fehler ab, die sonst erst im Sprachkanal als Rauschen auffallen: falsch
abgeteilte Nonce, vergessene CSRC-Liste, Erweiterungs-Praeambel im falschen
Block.

Aufruf aus dem Fork-Wurzelordner:
    py pruefe_krypto.py
"""
import os
import struct
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# `discord/__init__.py` zieht das ganze Paket hoch, darunter `soundboard`,
# das `pydub` braucht — eine Fremdabhaengigkeit, die mit Sprachpaketen
# nichts zu tun hat. Statt sie zu installieren wird sie fuer die Dauer des
# Tests durch einen Platzhalter ersetzt: Der Test soll die Verschluesselung
# pruefen, nicht die Installationsumgebung.
for name, attrs in (('pydub', ('AudioSegment',)),):
    if name not in sys.modules:
        modul = types.ModuleType(name)
        for attr in attrs:
            setattr(modul, attr, type(attr, (), {}))
        sys.modules[name] = modul

import nacl.secret
import nacl.utils

from discord.sink import RawData


class FakeClient:
    """Minimaler Ersatz fuer den VoiceClient — nur was RawData wirklich braucht."""

    def __init__(self, mode: str, secret_key: bytes) -> None:
        self.mode = mode
        self.secret_key = list(secret_key)
        self._lite_nonce = 0

    # Die echten Methoden werden unveraendert uebernommen, damit der Test
    # wirklich den Produktivcode prueft und keine Nachbildung.
    from discord.voice_client import VoiceClient as _VC
    _encrypt_aead_xchacha20_poly1305_rtpsize = _VC._encrypt_aead_xchacha20_poly1305_rtpsize
    _decrypt_aead_xchacha20_poly1305_rtpsize = _VC._decrypt_aead_xchacha20_poly1305_rtpsize
    checked_add = _VC.checked_add


def kopf_bauen(ssrc: int, sequence: int, timestamp: int, *, extended: bool = False,
               cc: int = 0) -> bytearray:
    """Einen RTP-Kopf bauen, wie Discord ihn schickt."""
    kopf = bytearray(12 + cc * 4)
    kopf[0] = 0x80 | (0x10 if extended else 0x00) | cc
    kopf[1] = 0x78
    struct.pack_into('>H', kopf, 2, sequence)
    struct.pack_into('>I', kopf, 4, timestamp)
    struct.pack_into('>I', kopf, 8, ssrc)
    for i in range(cc):
        struct.pack_into('>I', kopf, 12 + i * 4, 0xDEAD0000 + i)
    return kopf


def fall_einfach() -> bool:
    """Verschluesseln und wieder entschluesseln, ohne Erweiterung."""
    schluessel = nacl.utils.random(32)
    client = FakeClient('aead_xchacha20_poly1305_rtpsize', schluessel)

    opus = b'\xfc\xff\xfe' + bytes(range(120))
    kopf = kopf_bauen(0x11223344, 42, 960)

    paket = client._encrypt_aead_xchacha20_poly1305_rtpsize(bytes(kopf), opus)
    roh = RawData(paket, client)

    ok = roh.decrypted_data == opus
    print(f'  einfach            : {"OK " if ok else "FEHLER"}  '
          f'{len(opus)} B rein, {len(roh.decrypted_data)} B raus, '
          f'ssrc={roh.ssrc:#x}, seq={roh.sequence}')
    return ok


def fall_erweiterung() -> bool:
    """Paket MIT Header-Erweiterung — der Fall, an dem die Aufteilung kippt.

    Discord setzt die Erweiterung regelmaessig. Sie wird hier von Hand
    gebaut, weil der Sendepfad der Bibliothek selbst keine erzeugt.
    """
    schluessel = nacl.utils.random(32)
    client = FakeClient('aead_xchacha20_poly1305_rtpsize', schluessel)

    opus = b'\xfc\xff\xfe' + bytes(range(200))
    kopf = kopf_bauen(0x55667788, 7, 1920, extended=True)

    # Praeambel: Profil 0xBEDE, danach die Laenge in 32-Bit-Woertern.
    woerter = 2
    praeambel = struct.pack('>HH', 0xBEDE, woerter)
    ext_daten = bytes(range(woerter * 4))

    box = nacl.secret.Aead(schluessel)
    nonce = bytearray(24)
    nonce[:4] = struct.pack('>I', 99)

    # AAD ist Kopf + Praeambel, Geheimtext ist Erweiterungsdaten + Opus.
    aad = bytes(kopf) + praeambel
    geheim = box.encrypt(ext_daten + opus, aad, bytes(nonce)).ciphertext
    paket = aad + geheim + bytes(nonce[:4])

    roh = RawData(paket, client)

    ok = roh.decrypted_data == opus
    print(f'  mit Erweiterung    : {"OK " if ok else "FEHLER"}  '
          f'{len(opus)} B rein, {len(roh.decrypted_data)} B raus, '
          f'ext_offset={roh.ext_offset}, extended={roh.extended}')
    if not ok:
        print(f'      erwartet: {opus[:16].hex()}')
        print(f'      bekommen: {bytes(roh.decrypted_data[:16]).hex()}')
    return ok


def fall_csrc() -> bool:
    """Paket mit CSRC-Liste — seltener, aber die Zerlegung muss stimmen."""
    schluessel = nacl.utils.random(32)
    client = FakeClient('aead_xchacha20_poly1305_rtpsize', schluessel)

    opus = bytes(range(60))
    kopf = kopf_bauen(0x99AABBCC, 3, 2880, cc=2)

    box = nacl.secret.Aead(schluessel)
    nonce = bytearray(24)
    nonce[:4] = struct.pack('>I', 5)
    geheim = box.encrypt(opus, bytes(kopf), bytes(nonce)).ciphertext
    paket = bytes(kopf) + geheim + bytes(nonce[:4])

    roh = RawData(paket, client)
    ok = roh.decrypted_data == opus
    print(f'  mit CSRC-Liste     : {"OK " if ok else "FEHLER"}  '
          f'cc={roh.cc}, Kopf {len(roh.header)} B')
    return ok


def fall_nebenlaeufig() -> bool:
    """Zwei Sprecher abwechselnd — faengt einen Nonce-Zustand am Client.

    Wuerde die Nonce am Client zwischengespeichert statt aus dem Paket
    gelesen, liefe dieser Fall auf Rauschen hinaus.
    """
    schluessel = nacl.utils.random(32)
    client = FakeClient('aead_xchacha20_poly1305_rtpsize', schluessel)

    pakete = []
    erwartet = []
    for i in range(6):
        opus = bytes([i]) * (50 + i)
        kopf = kopf_bauen(0x1000 + (i % 2), i, i * 960)
        pakete.append(client._encrypt_aead_xchacha20_poly1305_rtpsize(bytes(kopf), opus))
        erwartet.append(opus)

    # Bewusst in verdrehter Reihenfolge entschluesseln.
    reihenfolge = [3, 0, 5, 1, 4, 2]
    ok = all(RawData(pakete[i], client).decrypted_data == erwartet[i] for i in reihenfolge)
    print(f'  verdrehte Folge    : {"OK " if ok else "FEHLER"}  '
          f'6 Pakete, Reihenfolge {reihenfolge}')
    return ok


def main() -> None:
    print('Pruefe aead_xchacha20_poly1305_rtpsize gegen den Produktivcode:')
    ergebnisse = [fall_einfach(), fall_erweiterung(), fall_csrc(), fall_nebenlaeufig()]
    bestanden = sum(ergebnisse)
    print(f'--- {bestanden} von {len(ergebnisse)} bestanden')
    sys.exit(0 if bestanden == len(ergebnisse) else 1)


if __name__ == '__main__':
    main()
