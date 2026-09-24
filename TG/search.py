from bot import  Bot, Vars, logger
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
import random

from Tools.db import ensure_user, premium_user

from .storage import (
    get_webs, igrone_error, plugins_list, 
    retry_on_flood, searchs, is_auth_query, 
    web_data, check_get_web
)

from Tools.my_token import verify_token, get_token, check_token_
import asyncio



@Bot.on_message(filters.command("search"))
@check_token_
async def search_group(client, message):
  if Vars.IS_PRIVATE:
    if message.chat.id not in Vars.ADMINS:
      return await message.reply(Vars.PRIVATE_TXT)

  if client.SHORTENER:
    if not await premium_user(message.from_user.id):
      if not verify_token(message.from_user.id):
        if not message.from_user.id in client.ADMINS:
          return await get_token(message, message.from_user.id)

  ensure_user(message.from_user.id)

  try:
    txt = message.text.split(" ")[1]
  except:
    return await message.reply("<code>Format:- /search Manga </code>")
  
  photo = random.choice(Vars.PICS)
  await retry_on_flood(message.reply_photo)(
    photo, caption="<i>Select search Webs ...</i>",
    reply_markup=plugins_list(), quote=True
  )



@Bot.on_message(filters.text & filters.private & ~filters.regex(r"/"))
@check_token_
async def search(client, message):
  if Vars.IS_PRIVATE:
    if message.chat.id not in Vars.ADMINS:
      return await message.reply(Vars.PRIVATE_TXT)
  
  ensure_user(message.from_user.id)
  photo = random.choice(Vars.PICS)
  await retry_on_flood(message.reply_photo)(
    photo, caption="<i>Select search Webs ...</i>",
    reply_markup=plugins_list(), quote=True
  )


@Bot.on_callback_query(filters.regex("^bk") & is_auth_query())
async def bk_handler(client, query):
  """This Is Back Handler Of Callback Data"""
  photo = random.choice(Vars.PICS)
  try: page = int(query.data.split(":")[-1])
  except:  page = 1

  ensure_user(query.from_user.id)
  await retry_on_flood(query.message.edit_media)(
      media=InputMediaPhoto(photo, caption="<i>Select The Webs ....</i>"),
      reply_markup=plugins_list(page=page),
  )
  await igrone_error(query.answer)()


async def search_all(search, sts, max_concurrent=5):
  """Ultra-low RAM usage with streaming results"""
  semaphore = asyncio.Semaphore(max_concurrent)
  results = []
  found = []
  no_found = []
  current_index = 0

  async def search_and_collect(web, web_name):
    async with semaphore:
      try:
        result = await web.search(search)
        if result and web_name not in found: 
          found.append(web_name)
        else: 
          no_found.append(web_name)
        return result or []
      except Exception:
        return []

  for web_name, web in web_data.items():
    result = await search_and_collect(web, web_name)
    if result:
      results.extend(result)
    current_index += 1
    try:
      await sts.edit_message_caption(
          f"<i>Searching: <b>{search}</b> | "
          f"Progress: <b>{current_index}/{len(web_data)}</b> | "
          f"Webs: <b>{web_name}</b></i> ")
    except:
      pass

  found = ", ".join(found) if found else None
  no_found = ", ".join(no_found) if no_found else None

  return results, found, no_found


@Bot.on_callback_query(filters.regex("^plugin_") & is_auth_query())
async def cb_handler(client, query):
  """ This Is Search  Handler Of Callback Data """

  def iterate_(results, page=1):
    try:
      return results[(page - 1) * 8:page * 8] if page != 1 else results[:8]
    except:
      return None

  data = query.data.split("_")[-1]
  photo = random.choice(Vars.PICS)

  try:
    page = int(query.data.split("_")[-2])
  except:
    page = 1

  reply = query.message.reply_to_message
  if not reply:
    return await query.answer("This is an old button, please redo the search",
                              show_alert=True)

  reply = reply.text
  if reply.startswith("/search"):
    search = reply.split(" ", 1)[-1]
  else:
    search = reply

  if "/subs" in search or "/subscribes" in search or "/queue" in search:
    try:
      return await isubs_handle(client, query)
    except Exception as err:
      logger.exception(err)
      await igrone_error(query.answer)(" Errors Occured ", show_alert=True)
      await igrone_error(query.message.delete)()
  
  reply_markup = query.message.reply_markup

  results = None
  results_ = None
  found = None
  no_found = None
  webs = get_webs(data)
  if not webs:
    webs = "all"
    await igrone_error(query.edit_message_text)(f"<i>Searching:- <b>{search}</b> ... </i>")

  if webs == "all":
    results_, found, no_found = await search_all(search, query)
  else:
    results_ = await igrone_error(webs.search)(search)
  
  results = iterate_(results_, page=page)
  if not results or not results_:
    return await retry_on_flood(query.edit_message_media)(
        media=InputMediaPhoto(
            photo, caption=f"<i>No results found:- <b>{search}</b></i>"),
        reply_markup=reply_markup,
    )

  button = []
  for result in results:
    c = f"chs|{data}{result['id']}" if "id" in result else f"chs|{data}{hash(result['url'])}"
    if webs == "all":
      webs_ = check_get_web(result['url'])
      if not webs: 
        continue

      searchs[c] = (webs_, result)
      web_name = type(webs_).__name__
      web_name = web_name.replace("Webs", "")
      button.append([
          InlineKeyboardButton(f"{result['title']} [{web_name}]",
                               callback_data=c)
      ])
    else:
      searchs[c] = (webs, result)
      button.append([InlineKeyboardButton(result['title'], callback_data=c)])
  
  await igrone_error(query.answer)()

  arrow = []
  if iterate_(results_, page=int(page - 1)):
    arrow.append(
        InlineKeyboardButton(f"<<", callback_data=f"plugin_{page-1}_{data}"))
  if iterate_(results_, page=int(page + 1)):
    arrow.append(
        InlineKeyboardButton(f">>", callback_data=f"plugin_{page+1}_{data}"))

  if arrow:
    button.append(arrow)

  button.append([
      InlineKeyboardButton("▏𝗖𝗟𝗢𝗦𝗘▕", callback_data="kclose"),
      InlineKeyboardButton("⇦ 𝗕𝗔𝗖𝗞", callback_data="bk.p"),
  ])
  
  if webs != "all":
    web_name = type(webs).__name__
    web_name = web_name.replace("Webs", "")
    caption_text = f"<blockquote expandable><i>Search <b>{search}</b> from <b>{web_name}</b></i></blockquote>"
  else:
    web_name = "All"
    caption_text = f"<blockquote><i>Search <b>{search}</b> from <b>{web_name}</b></i></blockquote>"
    caption_text += f"\n\n<blockquote expandable><b>Found Sites:</b> <i>{found}</i></blockquote>" if found else ""
    caption_text += f"\n\n<blockquote expandable><b>Not Found Sites:</b> <i>{no_found}</i></blockquote>" if no_found else ""

  await retry_on_flood(query.edit_message_media)(
    InputMediaPhoto(photo,caption=caption_text[:1024]),
      reply_markup=InlineKeyboardMarkup(button)
  )
