from bot import Bot, Vars, logger
from Tools.db import get_subs, add_sub, delete_sub, ensure_user
from TG.storage import igrone_error, subscribes, filters
import random
from TG.storage import retry_on_flood, check_get_web, is_auth_query, searchs
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto


@Bot.on_callback_query(filters.regex("^subs") & is_auth_query())
async def subs_handler(client, query):
  """This Is Subscribe Handler Of Callback Data"""
  if query.data in subscribes:
    webs, data = subscribes[query.data]
    
    reply_markup = query.message.reply_markup
    button = reply_markup.inline_keyboard
    
    if get_subs(str(query.from_user.id), data.manga_url, webs.sf):
      await delete_sub(str(query.from_user.id), data.manga_url, webs.sf)
      if webs.sf == "ck" or webs.sf == "mf":
        button[-3] = [
            InlineKeyboardButton("✓ sᴜʙsᴄʀɪʙᴇ ✓", callback_data=query.data)
        ]
      else:
        button[-2] = [
            InlineKeyboardButton("✓ sᴜʙsᴄʀɪʙᴇ ✓", callback_data=query.data)
        ]

      await igrone_error(query.answer)(" Comic Unsubscribed ")
    else:
      await add_sub(str(query.from_user.id), data, webs.sf)

      if webs.sf == "ck" or webs.sf == "mf":
        button[-3] = [
            InlineKeyboardButton("✘ ᴜɴsᴜʙsᴄʀɪʙᴇ ✘", callback_data=query.data)
        ]
      else:
        button[-2] = [
            InlineKeyboardButton("✘ ᴜɴsᴜʙsᴄʀɪʙᴇ ✘", callback_data=query.data)
        ]

      await igrone_error(query.answer)(" Comic Subscribed ")

    try:
      await retry_on_flood(query.edit_message_reply_markup
                           )(InlineKeyboardMarkup(button))
    except Exception:
      await retry_on_flood(client.edit_message_reply_markup
                           )(query.message.chat.id, query.message.message_id,
                             InlineKeyboardMarkup(button))
  else:
    await retry_on_flood(query.answer)("This is an old button, please redo the search")



async def isubs_handle(process, page, user_id):
  """This Is Subscribe Handler Of Callback Data"""
  def iterate_subs(subs, page=1):
    try:
      return subs[(page - 1) * 10:page * 10] if page != 1 else subs[:10]
    except:
      return None

  ensure_user(user_id)

  all_manga_subs = get_subs(user_id)
  if not all_manga_subs:
    return await retry_on_flood(process)("You Have No Subscribe Any Manga")

  if all_manga_subs is True:
    return await retry_on_flood(process)("You Have No Subscribe Any Manga")

  button = []
  manga_subs = iterate_subs(all_manga_subs, page=int(page))
  if not manga_subs:
    return button

  for data in manga_subs:
    web = check_get_web(data['url'])
    if not web: continue
    
    webs_name = type(web).__name__
    webs_name = webs_name.replace("Webs", "")

    c = f"chs|{web.sf}{hash(data['url'])}"
    searchs[c] = (web, data)
    button.append([
        InlineKeyboardButton(f"{data['title']} [{webs_name}]", callback_data=c)
    ])

  arrow = []
  if iterate_subs(all_manga_subs, page=int(page - 1)):
    arrow.append(InlineKeyboardButton(f"<<", callback_data=f"isubs:{page-1}"))

  if iterate_subs(all_manga_subs, page=int(page + 1)):
    arrow.append(InlineKeyboardButton(f">>", callback_data=f"isubs:{page+1}"))

  button.append(arrow)
  button.append([
    InlineKeyboardButton("✵ Clean All Subscribe ✵", callback_data="pqi_clean_all_subs")
  ])
  
  button.append([
      InlineKeyboardButton("◊ ǫᴜᴇᴜᴇ ◊", callback_data="refresh_queue"),
      InlineKeyboardButton("▏𝗖𝗟𝗢𝗦𝗘▕", callback_data="kclose")
  ])

  return button


@Bot.on_message(filters.command(["subs", "subscribes"]))
async def isubs_cmds(_, message):
  """This Is Subscribe Handler Of Callback Data"""
  sts = await retry_on_flood(message.reply_text)("<code>Processing...</code>", quote=True)
  user_id = str(message.from_user.id)
  ensure_user(user_id)
  
  button = await isubs_handle(
    process=sts.edit_text, 
    page=1, 
    user_id=user_id
  )
  if not button:
    return await retry_on_flood(sts.edit_text)("You Have No Subscribe Any Manga")
  
  try:
    await retry_on_flood(sts.edit_media)(
      InputMediaPhoto(random.choice(Vars.PICS), caption="<i>Your Subs ..</i>"),
      reply_markup=InlineKeyboardMarkup(button)
    )
  except:
    await retry_on_flood(message.reply_photo)(
      photo=random.choice(Vars.PICS),
      caption="<i>Your Subs ..</i>",
      reply_markup=InlineKeyboardMarkup(button),
      quote=True,
    )


@Bot.on_callback_query(filters.regex("^isubs") & is_auth_query())
async def isubs_callback(client, query):
  """This Is Subscribe Handler Of Callback Data"""
  try:
    page = query.data.split(":")[1]
  except:
    page = 1
  
  user_id = str(query.from_user.id)
  ensure_user(user_id)
  button =  await isubs_handle(
    process=query.answer,
    page=page,
    user_id=user_id
  )
  if not button:
     return await retry_on_flood(query.answer)("You Have No Subscribe Any Manga")
  
  await igrone_error(query.edit_message_reply_markup)(InlineKeyboardMarkup(button))


@Bot.on_callback_query(filters.regex("^pqi_clean_all_subs$") & is_auth_query())
async def _clean_all_subs_handler(client, query):
  """This Is Clean All Subs Handler Of Callback Data"""
  user_id = str(query.from_user.id)
  if not get_subs(user_id):
    return await query.answer("You Have No Subscribe Any Manga", show_alert=True)

  await delete_sub(user_id)
  await query.answer("All Subs Deleted", show_alert=True)
  try: 
    await retry_on_flood(query.message.delete)()
  except: 
    pass
