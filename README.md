# Purger — Discord Auto-Cleaner (deutsch)

Ein schlanker Discord-Bot, der Kanäle per Slash-Commands säubert und optional **automatisch alle 12 Stunden** (um **13:00** und **01:00** Europe/Berlin) leert. Unterstützt **Bulk-Delete** für jüngere Nachrichten und **adaptives Throttling** für ältere Nachrichten (>14 Tage).

---

## Features

* `/purge` löscht alle Nachrichten im aktuellen Kanal
* `/purger select` wählt Kanäle für den Auto-Purge
* `/purger list` zeigt die ausgewählten Auto-Purge-Kanäle
* `/purger clear` entfernt alle Auto-Purge-Kanäle
* `/purger run` startet sofort den Purge in allen ausgewählten Kanälen
* `/perms` zeigt die Bot-Berechtigungen im aktuellen Kanal/Thread
* `/invite` erzeugt eine exakte Invite-URL für **diese** Bot-App
* Zeitgesteuert: automatisch um **13:00** und **01:00** (Europe/Berlin)
* Persistenz pro Guild via `purger_config.json`
* Thread-Support: Bot tritt Threads bei / entarchiviert wenn nötig
* Rate-Limit-schonend: exponentielles Backoff beim Einzellöschen

---

## Voraussetzungen

* Python **3.11+** (empfohlen 3.12)
* `discord.py >= 2.3`
* Rechte auf dem Ziel-Server: „Server verwalten“, um den Bot einzuladen

---

## Installation

```bash
# Projekt klonen/kopieren, dann:
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -U discord.py
```

---

## Konfiguration

Setze mindestens deinen Bot-Token (aus dem Discord Developer Portal):

```bash
# Windows PowerShell
$env:DISCORD_TOKEN = "DEIN_BOT_TOKEN"

# Linux/macOS (bash/zsh)
export DISCORD_TOKEN="DEIN_BOT_TOKEN"
```

Optionale Umgebungsvariablen:

* `DISCORD_PERMISSIONS` (Default `74752`) – Invite-Permissions Maske
  (View Channel 1024 + Manage Messages 8192 + Read Message History 65536)
* `PURGER_CONFIG` (Pfad zur JSON, Default `purger_config.json`)

---

## Starten

```bash
python Purger.py
```

In der Konsole erscheint eine **Invite-URL**. Öffne sie, wähle deinen Server und bestätige.

> Alternativ im Server: `/invite` ausführen (ephemeral), um die Invite-URL zu erhalten.

---

## Slash-Commands

* `/purge`
  Löscht alle Nachrichten im aktuellen Kanal.
  Hinweis: Discord erlaubt Bulk-Delete nur für Nachrichten **< 14 Tage**. Ältere werden einzeln gelöscht.

* `/purger select [channel1..channel5]`
  Wählt bis zu 5 Kanäle für den Auto-Purge aus. Ohne Argumente wird der **aktuelle Kanal** hinzugefügt.

* `/purger list`
  Zeigt die gespeicherten Kanäle und die **nächste Ausführung**.

* `/purger clear`
  Entfernt alle gespeicherten Kanäle für diese Guild.

* `/purger run`
  Führt sofort einen Purge in **allen gespeicherten Kanälen** aus und zeigt eine Zusammenfassung.

* `/perms`
  Zeigt, ob der Bot im aktuellen Kanal/Thread die nötigen Rechte hat.

* `/invite`
  Gibt die exakte Invite-URL für diese App aus.

---

## Auto-Purge (Scheduler)

* Läuft automatisch um **13:00** und **01:00** (Zeitzone **Europe/Berlin**) und danach im 12-Stunden-Takt.
* Speicherung pro Guild in `purger_config.json`:

  ```json
  {
    "GUILD_ID_STRING": [123456789012345678, 234567890123456789]
  }
  ```

---

## Benötigte Berechtigungen

Für den **Bot** im jeweiligen Kanal:

* **Kanal ansehen**
* **Nachrichtenverlauf anzeigen**
* **Nachrichten verwalten**

**Threads/Foren:** In privaten/archivierten Threads muss der Bot **Mitglied** sein. Der Bot versucht automatisch beizutreten und zu entarchivieren; ggf. „Threads verwalten“ erlauben.

Beim Einladen sollten die Scopes **`bot`** und **`applications.commands`** gesetzt sein.
Empfohlene Permissions-Maske: **74752**.

---

## Troubleshooting

* **Bot ist nicht in der Mitgliederliste**
  → Invite mit Scopes `bot` + `applications.commands` verwenden (siehe Konsole oder `/invite`).
  → Prüfe, ob der **Token** der gleiche ist wie die geladene App (siehe `/whoami`).

* **Missing Access / 50001**
  → Bot hat nicht die nötigen Rechte im Kanal oder falsche Scopes beim Invite.
  → Rechte auf **Kanal-Ebene** prüfen; Kanal-Overrides können Server-Rollen überstimmen.

* **`/purge` löscht sehr langsam**
  → Nachrichten älter als 14 Tage müssen **einzeln** gelöscht werden. Der Bot nutzt bereits ein adaptives Backoff, um 429-Rate-Limits zu reduzieren.

* **`/perms` meldet fehlenden Nachrichtenverlauf in Threads**
  → In privaten/archivierten Threads muss der Bot Mitglied sein. Der Bot versucht beizutreten; ggf. Rechte „Threads verwalten“ geben oder händisch hinzufügen.

---

## Sicherheit

* Leake den Token nicht (keine Commits mit Token, keine Screenshots).
* Halte `discord.py` aktuell: `pip install -U discord.py`.

---

## Lizenz

Enhanced MIT License

---

### Signatur:

```bash
# /* ======================================== */
# // Signature
# //
#    01001001 01110000 01000001 01110101 01010110 01000011 01000101
#    01100111 01011010 01000101 01010011 00111000 01001010 00110010
#    01001001 01101110 01010000 01100111 00111101 00111101
# /* ======================================== */
```
