from Webs import *

web_data = {
    #" Comick ": ComickWebs(),
    #" MangaMob ": MangaMobWebs(),
    " Asura Scans ": AsuraScansWebs(),
    #" Flame Comics": FlameComicsWebs(),
    #" Demonic Scans ": DemonicScansWebs(),
    " Manhua Fast ": ManhuaFastWebs(),
    " Weeb Central ": WeebCentralWebs(),
    " ManhwaClan ": ManhwaClanWebs(),
    " TempleToons ":TempleToonsWebs(),
    " Manhuaplus ": ManhuaplusWebs(),
    " Mgeko ": MgekoWebs(),
    " Manga18fx ": Manga18fxWebs(),
    " Manhwa18 ":  Manhwa18Webs(),
}


from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import pyrogram.errors
from pyrogram.errors import FloodWait
from bot import Vars
from loguru import logger
from pyrogram import filters
from Tools.base import AQueue, igrone_error, get_episode_number, retry_on_flood


queue = AQueue()
searchs = {}
backs = {}
chaptersList = {}
queueList = {}
pagination = {}
subscribes = {}


web_data = dict(sorted(web_data.items()))
plugins_name = " ".join(web_data[i].sf for i in web_data)

def split_list(li):
    return [li[x:x + 2] for x in range(0, len(li), 2)]

def check_get_web(url):
    for web in web_data.values():
        if url.startswith(web.url):
            return web



def is_auth_query():
    async def func(flt, _, query):
        reply = query.message.reply_to_message
        if not reply:
            return True
        
        if not reply.from_user:
            return False
        
        user_id = reply.from_user.id
        query_user_id = query.from_user.id
        if user_id != query_user_id:
            await query.answer("This is not for you", show_alert=True)
            return False
        return True
    
    return filters.create(func)


def plugins_list(type=None, page=1):
    button = []
    if type and type == "updates":
        for i in web_data.keys():
            c = web_data[i].sf
            c = f"udat_{c}"
            button.append(InlineKeyboardButton(i, callback_data=c))
    elif type and type == "gens":
        for i in web_data.keys():
            c = web_data[i].sf
            c = f"gens_{c}"
            button.append(InlineKeyboardButton(i, callback_data=c))
    elif type and type == "subs":
        for i in web_data.keys():
            c = web_data[i].sf
            c = f"isubs_{c}"
            button.append(InlineKeyboardButton(i, callback_data=c))
    else:
        for i in web_data.keys():
            c = web_data[i].sf
            c = f"plugin_{c}"
            button.append(InlineKeyboardButton(i, callback_data=c))

    button = button[len(button)//2:len(button)] if page != 1 else button[:len(button)//2]
    button = split_list(button)
    button.append([
        InlineKeyboardButton(" >> ", callback_data="bk.p:2") if page == 1 else InlineKeyboardButton(" << ", callback_data="bk.p:1")
    ])
    button.append([
        InlineKeyboardButton("♞ All Search ♞", callback_data="plugin_all"),
        InlineKeyboardButton("🔥 Close 🔥", callback_data="kclose")
    ])
    return InlineKeyboardMarkup(button)

def get_webs(sf):
    return next((web for web in web_data.values() if web.sf == sf), None)



async def check_fsb(client, message):
    channel_button = []
    
    for channel_info in client.FSB:
        try:
            channel = int(channel_info[1])
        except:
            channel = channel_info[1]

        try:
            await client.get_chat_member(channel, message.from_user.id)
        except pyrogram.errors.UserNotParticipant:
            channel_link = channel_info[2] if len(channel_info) > 2 else (
                await client.export_chat_invite_link(channel) if isinstance(channel, int) 
                else f"https://telegram.me/{channel.strip()}"
            )
            channel_button.append(InlineKeyboardButton(channel_info[0], url=channel_link))
        except (pyrogram.errors.UsernameNotOccupied, pyrogram.errors.ChatAdminRequired) as e:
            await retry_on_flood(client.send_message)(
                Vars.LOG_CHANNEL, f"Channel issue: {channel} - {type(e).__name__}"
            )
        except (pyrogram.ContinuePropagation, pyrogram.StopPropagation):
            raise
        except Exception as e:
            await retry_on_flood(client.send_message)(
                Vars.LOG_CHANNEL, f"Force Subscribe error: {e} at {channel}"
            )

    return channel_button, []


# Optimized utility functions
def clean(txt, length=-1):
    """Clean text by removing special characters"""
    remove_chars = "_&;:None'|*?><`!@#$%^~+=\\/\n"
    for char in remove_chars:
        txt = txt.replace(char, "")
    return txt[:length] if length != -1 else txt

