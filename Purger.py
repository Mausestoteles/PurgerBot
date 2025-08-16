import os
import json
import asyncio
import datetime as dt
from zoneinfo import ZoneInfo
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN") or "DEIN_BOT_TOKEN"
GUILD_ID = None

DEFAULT_PERMS = 74752
INT_PERMS = int(os.getenv("DISCORD_PERMISSIONS", DEFAULT_PERMS))

TIMEZONE = ZoneInfo("Europe/Berlin")
CONFIG_PATH = os.getenv("PURGER_CONFIG", "purger_config.json")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k: list(set(v)) for k, v in data.items()}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

CONFIG = load_config()

def add_channels_to_guild(guild_id: int, channel_ids: list[int]) -> int:
    key = str(guild_id)
    current = set(CONFIG.get(key, []))
    before = len(current)
    current.update(channel_ids)
    CONFIG[key] = sorted(current)
    save_config(CONFIG)
    return len(current) - before

def list_channels_for_guild(guild_id: int) -> list[int]:
    return CONFIG.get(str(guild_id), [])

def clear_channels_for_guild(guild_id: int) -> int:
    key = str(guild_id)
    count = len(CONFIG.get(key, []))
    CONFIG[key] = []
    save_config(CONFIG)
    return count

def bot_has_purge_perms(channel: discord.abc.GuildChannel, me: discord.Member) -> tuple[bool, str]:
    perms = channel.permissions_for(me)
    if not perms.view_channel:
        return False, "Mir fehlt die Berechtigung Kanal ansehen."
    if not perms.read_message_history:
        return False, "Mir fehlt Nachrichtenverlauf anzeigen."
    if not perms.manage_messages:
        return False, "Mir fehlt Nachrichten verwalten."
    return True, ""

async def ensure_thread_access(channel: discord.Thread, me: discord.Member, reason: str) -> None:
    if channel.archived:
        try:
            await channel.edit(archived=False, reason=reason)
        except discord.Forbidden:
            pass
    try:
        await channel.join()
    except discord.HTTPException:
        pass

def build_invite_url(client_id: int, permissions: int = INT_PERMS) -> str:
    return (
        "https://discord.com/oauth2/authorize"
        f"?client_id={client_id}"
        "&scope=bot%20applications.commands"
        f"&permissions={permissions}"
    )

async def purge_channel(channel: discord.abc.GuildChannel, invoker: str) -> int:
    if not hasattr(channel, "guild") or channel.guild is None:
        return 0

    me = channel.guild.me
    reason = f"Auto-Purge ausgelöst von {invoker}"

    if isinstance(channel, discord.Thread):
        await ensure_thread_access(channel, me, reason)

    ok, _msg = bot_has_purge_perms(channel, me)
    if not ok:
        return 0

    deleted_total = 0

    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=14)

    def younger_than_14d(m: discord.Message):
        return m.created_at > cutoff

    try:
        bulk_deleted = await channel.purge(limit=None, check=younger_than_14d, bulk=True, reason=reason)
        deleted_total += len(bulk_deleted)
    except (discord.Forbidden, discord.HTTPException):
        pass

    try:
        consec_429 = 0
        async for msg in channel.history(limit=None, oldest_first=False, before=cutoff):
            try:
                await msg.delete()
                deleted_total += 1
                consec_429 = 0
                await asyncio.sleep(0.5)  
            except discord.HTTPException as e:
                if getattr(e, "status", None) == 429:
                    consec_429 += 1
                    backoff = min((2 ** consec_429) * 0.5, 8.0) 
                    await asyncio.sleep(backoff)
                    continue
            except discord.Forbidden:
                continue
    except (discord.Forbidden, discord.HTTPException):
        pass

    return deleted_total

def next_anchor_after(now: dt.datetime) -> dt.datetime:
    today_13 = now.replace(hour=13, minute=0, second=0, microsecond=0)
    today_01 = now.replace(hour=1, minute=0, second=0, microsecond=0)
    anchors = [a for a in [today_01, today_13] if a > now]
    if anchors:
        return min(anchors)
    tomorrow = (now + dt.timedelta(days=1)).replace(hour=1, minute=0, second=0, microsecond=0)
    return tomorrow

async def scheduler_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now_local = dt.datetime.now(TIMEZONE)
        next_run = next_anchor_after(now_local)
        sleep_seconds = (next_run - now_local).total_seconds()
        if sleep_seconds > 0:
            await asyncio.sleep(sleep_seconds)

        for guild in bot.guilds:
            channel_ids = list_channels_for_guild(guild.id)
            if not channel_ids:
                continue
            for cid in channel_ids:
                ch = guild.get_channel(cid) or bot.get_channel(cid)
                if ch is None:
                    continue
                try:
                    deleted = await purge_channel(ch, invoker="Scheduler")
                    print(f"[Scheduler] Purged {deleted} messages in #{getattr(ch, 'name', cid)} (guild {guild.name}).")
                except Exception as e:
                    print(f"[Scheduler] Fehler in Channel {cid}: {e}")

        await asyncio.sleep(12 * 60 * 60)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} ist online!")
    try:
        app_info = await bot.application_info()
        client_id = app_info.id
        print(f"Application / Client ID: {client_id}")
        print(f"Bot User ID: {bot.user.id}")
        invite_url = build_invite_url(client_id)
        print("==> Lade den Bot mit dieser URL auf deinen Server ein:")
        print(invite_url)
        if TOKEN == "DEIN_BOT_TOKEN":
            print("Du verwendest noch den Platzhalter-Token. Bitte ENV DISCORD_TOKEN setzen oder im Code ersetzen.")
    except Exception as e:
        print("Konnte App-Info nicht laden:", e)

    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"Guild-Commands synchronisiert: {len(synced)}")
        else:
            synced = await bot.tree.sync()
            print(f"Globale Commands synchronisiert: {len(synced)}")
    except Exception as e:
        print("Sync-Fehler:", e)

    if not getattr(bot, "_purger_scheduler_started", False):
        bot.loop.create_task(scheduler_loop())
        bot._purger_scheduler_started = True
        print("Scheduler gestartet (13:00 & 01:00 Europe/Berlin).")

@bot.tree.command(name="invite", description="Gibt eine Invite-URL für diesen Bot aus (bot + applications.commands).")
async def invite_cmd(interaction: discord.Interaction):
    app_info = await bot.application_info()
    url = build_invite_url(app_info.id)
    await interaction.response.send_message(
        f"Invite-URL:\n{url}\n\nPermissions-Maske: `{INT_PERMS}`",
        ephemeral=True
    )

@bot.tree.command(name="whoami", description="Zeigt Bot- und App-IDs.")
async def whoami(interaction: discord.Interaction):
    app_info = await bot.application_info()
    await interaction.response.send_message(
        f"App/Client ID: `{app_info.id}`\nBot User ID: `{interaction.client.user.id}`",
        ephemeral=True
    )

@bot.tree.command(name="perms", description="Zeigt die Bot-Berechtigungen im aktuellen Kanal/Thread.")
async def perms(interaction: discord.Interaction):
    if not interaction.guild or not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
        return await interaction.response.send_message("Nur in Textkanälen/Threads.", ephemeral=True)

    me = interaction.guild.me
    admin = me.guild_permissions.administrator
    ch = interaction.channel
    p = ch.permissions_for(me)

    details = []
    details.append(f"Admin: {'Ja' if admin else 'Nein'}")
    if isinstance(ch, discord.Thread):
        details.append(f"Thread: Ja (private: {'Ja' if ch.is_private() else 'Nein'}, archiviert: {'Ja' if ch.archived else 'Nein'})")
    else:
        details.append("Thread: Nein")

    missing = []
    if not p.view_channel: missing.append("Kanal ansehen")
    if not p.read_message_history: missing.append("Nachrichtenverlauf anzeigen")
    if not p.manage_messages: missing.append("Nachrichten verwalten")

    msg = "\n".join(details)
    if missing:
        msg += "\n\nEs fehlen:\n- " + "\n- ".join(missing)
        if isinstance(ch, discord.Thread):
            msg += "\n\nHinweis: In privaten/archivierten Threads muss der Bot Mitglied sein oder den Thread kurz öffnen."
    else:
        msg += "\n\nAlle nötigen Berechtigungen vorhanden."

    await interaction.response.send_message(msg, ephemeral=True)

@app_commands.default_permissions(manage_messages=True)
@bot.tree.command(name="purge", description="Löscht alle Nachrichten im aktuellen Kanal (inkl. älter als 14 Tage).")
async def purge(interaction: discord.Interaction):
    await interaction.response.send_message("Starte Purge…", ephemeral=True)
    if not interaction.guild or not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
        return await interaction.followup.send("Dieser Befehl funktioniert nur in Textkanälen/Threads.", ephemeral=True)
    deleted = await purge_channel(interaction.channel, invoker=str(interaction.user))
    await interaction.followup.send(f"Fertig. Gelöscht: {deleted} Nachrichten.", ephemeral=True)

purger = app_commands.Group(name="purger", description="Automatisches Purgen konfigurieren.")
bot.tree.add_command(purger)

@purger.command(name="select", description="Wähle bis zu 5 Kanäle, die automatisch um 13:00/01:00 gepurgt werden.")
@app_commands.describe(
    channel1="Kanal 1",
    channel2="Kanal 2 (optional)",
    channel3="Kanal 3 (optional)",
    channel4="Kanal 4 (optional)",
    channel5="Kanal 5 (optional)",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def purger_select(
    interaction: discord.Interaction,
    channel1: discord.abc.GuildChannel | None = None,
    channel2: discord.abc.GuildChannel | None = None,
    channel3: discord.abc.GuildChannel | None = None,
    channel4: discord.abc.GuildChannel | None = None,
    channel5: discord.abc.GuildChannel | None = None,
):
    if not interaction.guild:
        return await interaction.response.send_message("Nur in Servern nutzbar.", ephemeral=True)

    chosen = [c for c in [channel1, channel2, channel3, channel4, channel5] if c]
    if not chosen:
        if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            chosen = [interaction.channel]
        else:
            return await interaction.response.send_message("Bitte mindestens einen Textkanal auswählen.", ephemeral=True)

    valid_types = (discord.TextChannel, discord.Thread)
    channel_ids = [c.id for c in chosen if isinstance(c, valid_types)]
    if not channel_ids:
        return await interaction.response.send_message("Nur Textkanäle oder Threads werden unterstützt.", ephemeral=True)

    added = add_channels_to_guild(interaction.guild.id, channel_ids)
    now_local = dt.datetime.now(TIMEZONE)
    nxt = next_anchor_after(now_local)
    names = []
    for cid in channel_ids:
        ch = interaction.guild.get_channel(cid) or bot.get_channel(cid)
        names.append(f"<#{cid}>" if ch else f"`{cid}`")

    await interaction.response.send_message(
        f"Eingestellt für Auto-Purge: {', '.join(names)}\n"
        f"Neu hinzugefügt: {added} | Gesamt in dieser Guild: {len(list_channels_for_guild(interaction.guild.id))}\n"
        f"Nächster Lauf (Europe/Berlin): {nxt.strftime('%Y-%m-%d %H:%M')} (danach alle 12 h).",
        ephemeral=True
    )

@purger.command(name="list", description="Zeigt die aktuell konfigurierten Auto-Purge-Kanäle.")
@app_commands.checks.has_permissions(manage_guild=True)
async def purger_list(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("Nur in Servern nutzbar.", ephemeral=True)
    ids = list_channels_for_guild(interaction.guild.id)
    if not ids:
        return await interaction.response.send_message("Kein Kanal für Auto-Purge konfiguriert.", ephemeral=True)
    names = []
    for cid in ids:
        ch = interaction.guild.get_channel(cid) or bot.get_channel(cid)
        names.append(f"<#{cid}>" if ch else f"`{cid}`")
    now_local = dt.datetime.now(TIMEZONE)
    nxt = next_anchor_after(now_local)
    await interaction.response.send_message(
        f"Auto-Purge-Kanäle: {', '.join(names)}\n"
        f"Nächster Lauf (Europe/Berlin): {nxt.strftime('%Y-%m-%d %H:%M')}.",
        ephemeral=True
    )

@purger.command(name="clear", description="Entfernt alle Auto-Purge-Kanäle für diese Guild.")
@app_commands.checks.has_permissions(manage_guild=True)
async def purger_clear(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("Nur in Servern nutzbar.", ephemeral=True)
    removed = clear_channels_for_guild(interaction.guild.id)
    await interaction.response.send_message(f"Entfernt. Betroffene Kanäle: {removed}.", ephemeral=True)

@purger.command(
    name="run",
    description="Purge sofort alle aktuell konfigurierten Auto-Purge-Kanäle dieser Guild."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def purger_run(interaction: discord.Interaction):
    if not interaction.guild:
        return await interaction.response.send_message("Nur in Servern nutzbar.", ephemeral=True)

    ids = list_channels_for_guild(interaction.guild.id)
    if not ids:
        return await interaction.response.send_message(
            "Kein Kanal für Auto-Purge konfiguriert.", ephemeral=True
        )

    await interaction.response.send_message("Starte Sofort-Purge aller Auto-Purge-Kanäle …", ephemeral=True)

    results = []
    total_deleted = 0

    for cid in ids:
        ch = interaction.guild.get_channel(cid) or bot.get_channel(cid)
        if ch is None:
            results.append(f"<#{cid}> nicht gefunden")
            continue
        try:
            deleted = await purge_channel(ch, invoker=str(interaction.user))
            total_deleted += deleted
            results.append(f"{ch.mention} {deleted} gelöscht")
        except Exception as e:
            results.append(f"{ch.mention} Fehler: {e}")

    summary = f"Sofort-Purge abgeschlossen – Gesamt: {total_deleted} Nachrichten gelöscht."
    details = "\n".join(results)
    msg = f"{summary}\n{details}" if details else summary

    if len(msg) > 1800:
        details_trimmed = "\n".join(results[:min(50, len(results))])
        msg = f"{summary}\n{details_trimmed}\n… (gekürzt)"

    await interaction.followup.send(msg, ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)

# /* ======================================== */
# // Signature
# //
#    01001001 01110000 01000001 01110101 01010110 01000011 01000101
#    01100111 01011010 01000101 01010011 00111000 01001010 00110010
#    01001001 01101110 01010000 01100111 00111101 00111101
# /* ======================================== */