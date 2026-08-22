"""Prueft den Sprachempfang gegen das echte Discord — der einzige harte Beleg.

Die Verschluesselung laesst sich am Schreibtisch pruefen (`pruefe_krypto.py`),
die Verbindung nicht: DAVE handelt eine MLS-Gruppe mit Discords Servern aus,
und ob das klappt, zeigt erst ein echter Sprachkanal.

Ablauf:
    1. Bot anmelden, in den angegebenen Sprachkanal gehen
    2. Aufnehmen, solange DAUER laeuft
    3. WAV-Datei je Sprecher schreiben, Groesse ausgeben

Aufruf (Git Bash oder PowerShell)::

    py -m pip install "davey>=0.1.6" "PyNaCl>=1.5.0,<1.6"
    set DISCORD_TOKEN=...        # PowerShell: $env:DISCORD_TOKEN = '...'
    py pruefe_voice_empfang.py <kanal-id>

Der Beweis ist **nicht** „kein Fehler im Log", sondern eine WAV-Datei, in der
man sich hoert. Eine Datei mit 44 Byte ist ein leerer WAV-Kopf — dann kam
nichts an.
"""
import asyncio
import os
import sys
import time

import discord

DAUER = 15  # Sekunden aufnehmen


def zeitstempel() -> str:
    return time.strftime('%H:%M:%S')


def melde(text: str) -> None:
    print(f'[{zeitstempel()}] {text}', flush=True)


class Pruefbot(discord.Client):
    """Minimaler Client, der genau eine Aufnahme macht und sich beendet."""

    def __init__(self, kanal_id: int) -> None:
        intents = discord.Intents.default()
        intents.voice_states = True
        super().__init__(intents=intents)
        self.kanal_id = kanal_id
        self.fertig = asyncio.Event()

    async def on_ready(self) -> None:
        melde(f'Angemeldet als {self.user} (ID {self.user.id})')

        kanal = self.get_channel(self.kanal_id)
        if kanal is None:
            melde(f'FEHLER: Kanal {self.kanal_id} nicht gefunden — ist der Bot auf dem Server?')
            self.fertig.set()
            return
        if not isinstance(kanal, discord.VoiceChannel):
            melde(f'FEHLER: {kanal.name} ist kein Sprachkanal, sondern {type(kanal).__name__}')
            self.fertig.set()
            return

        melde(f'Betrete Sprachkanal „{kanal.name}"')
        try:
            vc = await kanal.connect()
        except Exception as fehler:
            melde(f'FEHLER beim Verbinden: {type(fehler).__name__}: {fehler}')
            melde('  Close-Code 4017 bedeutet: DAVE fehlt oder wurde nicht ausgehandelt.')
            self.fertig.set()
            return

        melde(f'Verbunden. Transportmodus: {vc.mode}')
        melde(f'DAVE-Protokollversion: {vc.dave_protocol_version} '
              f'(0 = ohne DAVE, dann ist es ein Stage-Kanal)')
        melde(f'DAVE-Sitzung: {"vorhanden" if vc.dave_session is not None else "keine"}')
        if vc.dave_session is not None:
            melde(f'  Status: {vc.dave_session.status}, bereit: {vc.dave_session.ready}')
            melde(f'  Sprachcode: {vc.dave_session.voice_privacy_code}')

        melde(f'Nehme {DAUER} s auf — **jetzt sprechen**')
        # Sink-API dieses Forks: Encoding und Ausgabeordner am Konstruktor,
        # nicht als eigene Klasse je Format (das ist py-cord).
        vc.start_recording(discord.Sink(encoding='wav', output_path='.'),
                           self._fertig_rueckruf)

        await asyncio.sleep(DAUER)
        vc.stop_recording()
        await asyncio.sleep(1)
        await vc.disconnect()
        self.fertig.set()

    async def _fertig_rueckruf(self, sink, *args) -> None:
        """Wird nach `stop_recording` mit den gesammelten Daten gerufen."""
        melde(f'Aufnahme beendet — {len(sink.audio_data)} Sprecher erfasst')

        if not sink.audio_data:
            melde('  KEIN AUDIO. Moegliche Ursachen:')
            melde('   - es hat niemand gesprochen')
            melde('   - die SSRC-Zuordnung ist leer (niemand hat "speaking" gesendet)')
            melde('   - die DAVE-Entschluesselung schlaegt fehl (siehe Log auf DEBUG)')
            return

        for benutzer_id, audio in sink.audio_data.items():
            # Nach `cleanup` traegt `audio.file` den Pfad der fertigen Datei,
            # nicht mehr das offene Dateiobjekt.
            pfad = audio.file if isinstance(audio.file, str) else getattr(audio.file, 'name', None)
            if not pfad or not os.path.exists(pfad):
                melde(f'  Nutzer {benutzer_id}: keine Datei entstanden')
                continue

            groesse = os.path.getsize(pfad)
            # Ein WAV-Kopf allein ist 44 Byte — alles darunter oder gleich
            # heisst: es kam kein einziger Audiorahmen an.
            bewertung = 'LEER (nur WAV-Kopf)' if groesse <= 44 else 'Audio vorhanden'
            melde(f'  Nutzer {benutzer_id}: {os.path.basename(pfad)}, '
                  f'{groesse} Byte — {bewertung}')


async def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    token = os.environ.get('DISCORD_TOKEN')
    if not token:
        melde('FEHLER: Umgebungsvariable DISCORD_TOKEN ist leer.')
        sys.exit(2)

    try:
        kanal_id = int(sys.argv[1])
    except ValueError:
        melde(f'FEHLER: „{sys.argv[1]}" ist keine Kanal-ID.')
        sys.exit(2)

    bot = Pruefbot(kanal_id)
    # Die Referenz auf die Aufgabe muss gehalten werden, sonst kann der
    # Garbage Collector sie mitten im Lauf einsammeln (bekannte asyncio-Falle).
    aufgabe = asyncio.create_task(bot.start(token))
    try:
        await bot.fertig.wait()
    finally:
        await bot.close()
        aufgabe.cancel()


if __name__ == '__main__':
    asyncio.run(main())
