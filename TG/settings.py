from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from bot import Bot, Vars, logger
from Tools.db import ensure_user, uts, sync
from .storage import igrone_error, retry_on_flood
import random
from pyrogram.errors import ListenerTimeout as TimeoutError

users_txt = """<b>Welcome to the User Panel ! </b>

<b>=> Your ID: <code>{id}</code></b>
<b>=> File Name: <code>{file_name}</code><code>[{len}]</code></b>
<b>=> Caption: <code>{caption}</code></b>
<b>=> Thumbnail: <code>{thumb}</code></b>
<b>=> File Type: <code>{type}</code></b>
<b>=> PDF Password: <code>{password}</code></b>
<b>=> Merge Size: <code>{megre}</code></b>
<b>=> Regex/Zfill: <code>{regex}</code></b>
<b>=> Banner 1: <code>{banner1}</code></b>
<b>=> Banner 2: <code>{banner2}</code></b>
<b>=> Dump Channel: <code>{dump}</code></b>
<b>=> Compression Quality: <code>{compress}</code></b>"""


info_data_text = {
  "caption": """
<b>📐 Send Caption 📐 

<u>Note:</u> <blockquote>Use HTML Tags For Bold, Italic,etc</blockquote>

<u>Params:</u>
=><code>{manga_title}</code>: Manga Name
=> <code>{chapter_num}</code>: Chapter Number
=> <code>{file_name}</code>: File Name</b>""",
  
  "dump": """
<b>📐 Send Dump Channel 📐 

<u>Note:</u> <blockquote>You Can Send Username(without @) or Channel Id or Forward Message from Channel.. </blockquote></b>""",
  
  "megre": """
"<b>📐 Send Merge Size 📐 

<u>Note:</u> <blockquote>Number of chapters to merge into a single file, e.g. 2, 3, 4, 5...</blockquote></b>""",
  
  "password": "<b>📐 Send Password 📐 \n<u>Note:</u> <blockquote>It's Password For PDF.</blockquote></b>"
}


def get_user_txt(user_id):
  user_id = str(user_id)
  ensure_user(user_id)

  thumbnali = uts[user_id]['setting'].get("thumb", None)

  if thumbnali:
    thumb = thumbnali if thumbnali.startswith("http") else "True"
    thumb = "Constant" if thumbnali == "constant" else thumbnali
  else:
    thumb = thumbnali

  banner1 = uts[user_id]['setting'].get("banner1", None)
  banner2 = uts[user_id]['setting'].get("banner2", None)

  if banner1:
    banner1 = banner1 if banner1.startswith("http") else "True"

  if banner2:
    banner2 = banner2 if banner2.startswith("http") else "True"

  txt = users_txt.format(
      id=user_id,
      file_name=uts[user_id]['setting'].get("file_name", "None"),
      caption=uts[user_id]['setting'].get("caption", "None"),
      thumb=thumb,
      banner1=banner1,
      banner2=banner2,
      dump=uts[user_id]['setting'].get("dump", "None"),
      type=uts[user_id]['setting'].get("type", "None"),
      megre=uts[user_id]['setting'].get("megre", "None"),
      regex=uts[user_id]['setting'].get("regex", "None"),
      len=uts[user_id]['setting'].get("file_name_len", "None"),
      password=uts[user_id]['setting'].get("password", "None"),
      compress=uts[user_id]['setting'].get("compress", "None"),
  )
  return txt, thumbnali


async def main_settings(_, message_query, user_id):
  ensure_user(user_id)
  txt, thumbnali = get_user_txt(user_id)

  button = [
      [
          InlineKeyboardButton("⌜ғɪʟᴇ ɴᴀᴍᴇ⌟", callback_data="ufn"),
          InlineKeyboardButton("⌜ᴄᴀᴘᴛɪᴏɴ⌟", callback_data="sinfo_caption")
      ],
      [
          InlineKeyboardButton("⌜ᴛʜᴜᴍʙɴᴀɪʟ⌟", callback_data="uth"),
          InlineKeyboardButton("⌜ʀᴇɢᴇx⌟", callback_data="uregex")
      ],
      [
          InlineKeyboardButton("⌜ʙᴀɴɴᴇʀ⌟", callback_data="ubn"),
          InlineKeyboardButton("⌜ᴄᴏᴍᴘʀᴇss⌟", callback_data="u_compress"),
      ],
      [
          InlineKeyboardButton("⌜ᴘᴀssᴡᴏʀᴅ⌟", callback_data="sinfo_password"),
          InlineKeyboardButton("⌜ᴍᴇʀɢᴇ sɪᴢᴇ⌟", callback_data="sinfo_megre")
      ],
      [
          InlineKeyboardButton("⌜ғɪʟᴇ ᴛʏᴘᴇ⌟", callback_data="u_file_type"),
      ],
  ]
  if not Vars.CONSTANT_DUMP_CHANNEL:
    button[-1].append(
        InlineKeyboardButton("⌜ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ⌟", callback_data="sinfo_dump"))

  button.append([InlineKeyboardButton("▏𝗖𝗟𝗢𝗦𝗘▕", callback_data="close")])

  if not thumbnali or thumbnali == "constant":
    thumbnali = random.choice(Vars.PICS)

  try:
    await retry_on_flood(message_query.edit_media)(
      InputMediaPhoto(thumbnali, caption=txt),
      reply_markup=InlineKeyboardMarkup(button)
    )
  except Exception:
    await retry_on_flood(message_query.edit_media)(
      InputMediaPhoto(Vars.PICS[-2], caption=txt),
      reply_markup=InlineKeyboardMarkup(button)
    )



@Bot.on_message(filters.command(["us", "user_setting", "user_panel"]))
async def userxsettings(client, message):
  if Vars.IS_PRIVATE:
    if message.chat.id not in Vars.ADMINS:
      return await message.reply(Vars.PRIVATE_TXT)

  sts = await message.reply("<code>Processing...</code>", quote=True)
  try:
    await main_settings(client, sts, message.from_user.id)
  except Exception as err:
    logger.exception(err)
    await retry_on_flood(sts.edit)(err)



@Bot.on_callback_query(filters.regex("^mus$"))
async def main_user_panel(_, query):
  await igrone_error(query.answer)()
  await main_settings(_, query.message, query.from_user.id)


@Bot.on_callback_query(filters.regex("^sinfo"))
async def user_settings(_, query):
  type = query.data.removeprefix("sinfo_")
  user_id = str(query.from_user.id)
  ensure_user(user_id)
  
  button = [
    [
      InlineKeyboardButton("⌜sᴇᴛ/ᴄʜᴀɴɢᴇ⌟", callback_data=f"sset_{type}"),
      InlineKeyboardButton("▏ᴅᴇʟᴇᴛᴇ▕", callback_data=f"sdelete_{type}")
    ],
    [
      InlineKeyboardButton("⇦ 𝗕𝗔𝗖𝗞", callback_data="mus")
    ]
  ]
  await igrone_error(query.answer)()
  await retry_on_flood(query.edit_message_reply_markup)(InlineKeyboardMarkup(button))


@Bot.on_callback_query(filters.regex("^sset"))
async def user_settings_set(_, query):
  type = query.data.removeprefix("sset_")
  user_id = str(query.from_user.id)
  ensure_user(user_id)
  try:
    await retry_on_flood(query.edit_message_caption)(info_data_text[type])
    call_ = await _.listen(user_id=int(user_id), timeout=80, filters=filters.text | filters.forwarded)
    if type == "dump":
      if call_.forward_from_chat:
        uts[user_id]['setting']["dump"] = call_.forward_from_chat.id
        sync()
      
      elif call_.text:
        try: uts[user_id]['setting']["dump"] = int(call_.text)
        except: uts[user_id]['setting']["dump"] = call_.text
        sync()
        
    else:
      uts[user_id]['setting'][type] = call_.text
      sync()
    
    await igrone_error(call_.delete)()
  
  except TimeoutError:
    await retry_on_flood(query.answer)("📐 ᴛɪᴍᴇᴏᴜᴛ 📐")
  except Exception as err:
    await retry_on_flood(query.answer)(f"📐 {err} 📐")
  
  await igrone_error(query.answer)()
  await main_settings(_, query.message, query.from_user.id)
        



@Bot.on_callback_query(filters.regex("^sdelete"))
async def user_settings_delete(_, query):
  type = query.data.removeprefix("sdelete_")
  user_id = str(query.from_user.id)
  ensure_user(user_id)
  
  if uts[user_id]['setting'].get(type, None) is not None:
    uts[user_id]['setting'][type] = None
    sync()
    
    await retry_on_flood(query.answer)("Successfully Deleted")
    await main_settings(_, query.message, query.from_user.id)
    
  else:
    await retry_on_flood(query.answer)(
      "📐 𝒀𝒐𝒖 𝒉𝒂𝒔 𝒏𝒐𝒕 𝑺𝒆𝒕 𝑰𝒕 ! 📐", show_alert=True
    )



@Bot.on_callback_query(filters.regex("^ufn"))
async def file_name_handler(_, query):
  user_id = str(query.from_user.id)
  ensure_user(user_id)

  if query.data == "ufn_change":
    await retry_on_flood(
        query.edit_message_caption
    )("<b>📐 Send File Name 📐 \n<u><i>Params:</u></i>\n=><code>{manga_title}</code>: Manga Name \n=> <code>{chapter_num}</code>: Chapter Number</b>"
      )
    try:
      call = await _.listen(user_id=int(user_id), timeout=80, filters=filters.text)

      uts[user_id]['setting']["file_name"] = call.text
      sync()
      
      await igrone_error(call.delete)()
      await igrone_error(query.answer)(" Successfully Added ")

    except TimeoutError:
      await retry_on_flood(query.answer)("📐 ᴛɪᴍᴇᴏᴜᴛ 📐")
    except Exception as err:
      await retry_on_flood(query.answer)(f"📐 {err} 📐")

  elif query.data == "ufn_delete":
    if uts[user_id]['setting'].get("file_name", None) is not None:
      uts[user_id]['setting']["file_name"] = None
      sync()
      
      await igrone_error(query.answer)("Successfully Deleted")
    else:
      await retry_on_flood(query.answer)(
        "📐 𝒀𝒐𝒖 𝒉𝒂𝒔 𝒏𝒐𝒕 𝑺𝒆𝒕 𝑰𝒕 ! 📐", show_alert=True
      )

  elif query.data == "ufn_len_change":
    await retry_on_flood(
        query.edit_message_caption
    )("<b>📐 Send File Name Len 📐\n Example: 15, 20, 50</b>")

    try:
      call = await _.listen(user_id=int(user_id), timeout=80, filters=filters.text)
      try:
        len_ch = int(call.text)
        uts[user_id]['setting']["file_name_len"] = call.text
        sync()

        await igrone_error(call.delete)()
        await retry_on_flood(query.answer)("🤖 Successfully Added 🤖")

      except ValueError:
        await retry_on_flood(query.answer)(
          "📐 ᴛʜɪs ɪs ɴᴏᴛ ᴀ ᴠᴀʟɪᴅ ɪɴᴛᴇɢᴇʀ 📐"
        )

    except (TimeoutError):
      await retry_on_flood(query.answer)("📐 ᴛɪᴍᴇᴏᴜᴛ 📐")
    except Exception as err:
      await retry_on_flood(query.answer)(f"📐 {err} 📐")

  elif query.data == "ufn_len_delete":
    if uts[user_id]['setting'].get("file_name_len", None) is not None:
      uts[user_id]['setting']["file_name_len"] = None
      sync()

      await retry_on_flood(query.answer)("🤖 Successfully Deleted 🤖")
    else:
      await retry_on_flood(query.answer)(
        "📐 𝒀𝒐𝒖 𝒉𝒂𝒔 𝒏𝒐𝒕 𝑺𝒆𝒕 𝑰𝒕 ! 📐", show_alert=True
      )

  button = [
    [
      InlineKeyboardButton("⌜sᴇᴛ/ᴄʜᴀɴɢᴇ⌟", callback_data="ufn_change"),
      InlineKeyboardButton("▏ᴅᴇʟᴇᴛᴇ▕", callback_data="ufn_delete")
    ],
    [
      InlineKeyboardButton("⌜sᴇᴛ/ᴄʜᴀɴɢᴇ ʟᴇɴ⌟", callback_data="ufn_len_change"),
      InlineKeyboardButton("▏ᴅᴇʟᴇᴛᴇ ʟᴇɴ▕", callback_data="ufn_len_delete")
    ], 
    [
      InlineKeyboardButton("⇦ 𝗕𝗔𝗖𝗞", callback_data="mus")
    ]
  ]
  
  await igrone_error(query.answer)()
  txt, thumbnali = get_user_txt(user_id)
  await retry_on_flood(query.edit_message_caption)(
    txt, reply_markup=InlineKeyboardMarkup(button)
  )

      

@Bot.on_callback_query(filters.regex("^uth"))
async def thumb_handler(_, query):
  user_id = str(query.from_user.id)
  ensure_user(user_id)

  button = [
    [
      InlineKeyboardButton("⌜sᴇᴛ/ᴄʜᴀɴɢᴇ⌟", callback_data="uth_change"),
      InlineKeyboardButton("⌜ᴄᴏɴsᴛᴀɴᴛ⌟", callback_data="uth_constant")
    ],
    [
      InlineKeyboardButton("▏ᴅᴇʟᴇᴛᴇ▕", callback_data="uth_delete"),
      InlineKeyboardButton("⇦ 𝗕𝗔𝗖𝗞", callback_data="mus"),
    ]
  ]

  if query.data == "uth_constant":
    uts[user_id]['setting']["thumb"] = "constant"
    sync()
    
    await retry_on_flood(query.answer)("🎮 Successfully Added 🎮")

  elif query.data == "uth_change":
    await retry_on_flood(query.edit_message_caption)(
      "<b>📐 Send Thumbnail 📐 \n<u>Note:</u> <blockquote>You Can Send Links or Images Docs.. </blockquote></b>"
    )
    try:
      call = await _.listen(user_id=int(user_id), timeout=60)
      call_type = call.photo or call.document or None
      
      if call_type:
        call_type = call_type.file_id
        uts[user_id]['setting']["thumb"] = call_type
        sync()

      elif not call_type:
        call_type = call.text
        if call_type.startswith("http"):
          uts[user_id]['setting']["thumb"] = call_type
          sync()

        else:
          await retry_on_flood(query.answer)("📐 ᴛʜɪs ɪs ɴᴏᴛ ᴀ ᴠᴀʟɪᴅ ᴛʜᴜᴍʙɴᴀɪʟ 📐")

      await igrone_error(call.delete)()
      await retry_on_flood(query.answer)("🎮 Successfully Added 🎮")
      
    except TimeoutError:
      await retry_on_flood(query.answer)("📐 ᴛɪᴍᴇᴏᴜᴛ 📐", show_alert=True)

    except Exception as err:
      await retry_on_flood(query.answer)(f"📐 {err} 📐", show_alert=True)
      

  elif query.data == "uth_delete":
    if thumbnali:
      uts[user_id]['setting']["thumb"] = None
      sync()
    
    else:
      await retry_on_flood(query.answer)("📐 𝒀𝒐𝒖 𝒉𝒂𝒔 𝒏𝒐𝒕 𝑺𝒆𝒕 𝑰𝒕 ! 📐")
  
  txt, thumbnali = get_user_txt(user_id)
  txt += "\n\n<blockquote><b>ℹ️ Constant:</b> the manga's own poster will be used as the file's thumbnail.</blockquote>"
  if not thumbnali or thumbnali == "constant":
    thumbnali = random.choice(Vars.PICS)
  try:
    await retry_on_flood(query.edit_message_media)(
      media=InputMediaPhoto(thumbnali, txt),
      reply_markup=InlineKeyboardMarkup(button)
    )
  except:
    await retry_on_flood(query.edit_message_media)(
      media=InputMediaPhoto(random.choice(Vars.PICS), txt),
      reply_markup=InlineKeyboardMarkup(button)
    )
  
  await igrone_error(query.answer)()


@Bot.on_callback_query(filters.regex("^ubn"))
async def banner_handler(_, query):
  user_id = str(query.from_user.id)
  ensure_user(user_id)
  
  banner1 = uts[user_id]['setting'].get("banner1", None)
  banner2 = uts[user_id]['setting'].get("banner2", None)
  banner_set = banner1 if banner1 else banner2
  
  if query.data.startswith("ubn_set"):
    banner_set = ""
    await retry_on_flood(query.edit_message_media)(
      InputMediaPhoto(
        random.choice(Vars.PICS),
        caption="<b>📐 Send Banner 📐 \n<u>Note:</u> <blockquote>You Can Send Links or Images Docs.. </blockquote></b>"
      )
    )

    try:
      call = await _.listen(user_id=int(user_id), timeout=60)
      call_type = call.photo or call.document or None

      if call_type:
        banner_set = call.photo.file_id
        
      elif not call_type:
        banner_set = call.text
        
        if not banner_set.startswith("http"):
          await retry_on_flood(query.answer)("📐 This Is Not Vaild Banner 📐")
          return

      if query.data == "ubn_set1":
        uts[user_id]['setting']["banner1"] = banner_set
        sync()

      elif query.data == "ubn_set2":
        uts[user_id]['setting']["banner2"] = banner_set
        sync()
      
      await retry_on_flood(call.delete)()
      await retry_on_flood(query.answer)("🎬 Successfully Added 🎬")

    except TimeoutError:
      await retry_on_flood(query.answer)("📐 ᴛɪᴍᴇᴏᴜᴛ 📐", show_alert=True)

    except Exception as err:
      await retry_on_flood(query.answer)(f"📐 {err} 📐", show_alert=True)

  elif query.data == "ubn_delete1":
    if banner1:
      uts[user_id]['setting']["banner1"] = None
      sync()
      
    else:
      return await retry_on_flood(query.answer)("📐 𝒀𝒐𝒖 𝒉𝒂𝒔 𝒏𝒐𝒕 𝑺𝒆𝒕 𝑰𝒕 ! 📐",
                                         show_alert=True)

  elif query.data == "ubn_delete2":
    if banner2:
      uts[user_id]['setting']["banner2"] = None
      sync()
    
    else:
      return await retry_on_flood(query.answer)("📐 𝒀𝒐𝒖 𝒉𝒂𝒔 𝒏𝒐𝒕 𝑺𝒆𝒕 𝑰𝒕 ! 📐",
                                         show_alert=True)
  
  if not banner_set:
    banner_set = random.choice(Vars.PICS)

  txt, _ = get_user_txt(user_id)
  button = [
    [
      InlineKeyboardButton("⌜sᴇᴛ/ᴄʜᴀɴɢᴇ - 𝟷⌟", callback_data="ubn_set1"),
      InlineKeyboardButton("▏ᴅᴇʟᴇᴛᴇ - 𝟷▕", callback_data="ubn_delete1")
    ],
    [
      InlineKeyboardButton("⌜sᴇᴛ/ᴄʜᴀɴɢᴇ - 𝟸⌟", callback_data="ubn_set2"),
      InlineKeyboardButton("▏ᴅᴇʟᴇᴛᴇ - 𝟸▕", callback_data="ubn_delete2")
    ], 
    [
      InlineKeyboardButton("⇦ 𝗕𝗔𝗖𝗞", callback_data="mus")
    ]
  ]
  await igrone_error(query.answer)()
  try:
    await retry_on_flood(query.edit_message_media)(
      media=InputMediaPhoto(banner_set, txt),
      reply_markup=InlineKeyboardMarkup(button)
    )
  except:
    await retry_on_flood(query.edit_message_media)(
      media=InputMediaPhoto(random.choice(Vars.PICS), txt),
      reply_markup=InlineKeyboardMarkup(button)
    )




@Bot.on_callback_query(filters.regex("^u_file_type"))
async def type_handler(_, query):
  user_id = str(query.from_user.id)
  ensure_user(user_id)
  
  if "type" not in uts[user_id]['setting']:
    uts[user_id]['setting']["type"] = []
    sync()

  type = uts[user_id].get("setting", {}).get("type", [])

  button = [[]]
  if "PDF" in type:
    button[0].append(
        InlineKeyboardButton("📙 PDF 📙", callback_data="u_file_type_pdf"))
  else:
    button[0].append(
        InlineKeyboardButton("❗PDF ❗", callback_data="u_file_type_pdf"))
  if "CBZ" in type:
    button[0].append(
        InlineKeyboardButton("📂 CBZ 📂", callback_data="u_file_type_cbz"))
  else:
    button[0].append(
        InlineKeyboardButton("❗CBZ ❗", callback_data="u_file_type_cbz"))

  button.append([InlineKeyboardButton("⇦ 𝗕𝗔𝗖𝗞", callback_data="mus")])

  if query.data == "u_file_type_pdf":
    if "PDF" in type:
      uts[user_id]['setting']["type"].remove("PDF")
      sync()

      button[0][0] = InlineKeyboardButton("❗PDF ❗",
                                          callback_data="u_file_type_pdf")

    else:
      uts[user_id]['setting']["type"].append("PDF")
      sync()

      button[0][0] = InlineKeyboardButton("📙 PDF 📙",
                                          callback_data="u_file_type_pdf")

  elif query.data == "u_file_type_cbz":
    if "CBZ" in type:
      uts[user_id]['setting']["type"].remove("CBZ")
      sync()

      button[0][1] = InlineKeyboardButton("❗CBZ ❗",
                                          callback_data="u_file_type_cbz")

    else:
      uts[user_id]['setting']["type"].append("CBZ")
      sync()

      button[0][1] = InlineKeyboardButton("📂 CBZ 📂",
                                          callback_data="u_file_type_cbz")

  txt, _ = get_user_txt(user_id)
  await retry_on_flood(query.edit_message_media)(
    media=InputMediaPhoto(random.choice(Vars.PICS), txt),
    reply_markup=InlineKeyboardMarkup(button)
  )
  
  await igrone_error(query.answer)()





@Bot.on_callback_query(filters.regex("^uregex"))
async def regex_handler(_, query):
  user_id = str(query.from_user.id)
  ensure_user(user_id)
  
  regex = uts[user_id]['setting'].get("regex", None)
  if query.data.startswith("uregex_set"):
    regex = query.data.split("_")[-1]
    uts[user_id]['setting'][f"regex"] = regex
    sync()
    
  elif query.data == "uregex_delete":
    if regex:
      regex = None
      uts[user_id]['setting']["regex"] = regex
      sync()
      
    else:
      await retry_on_flood(query.answer)("📐 𝒀𝒐𝒖 𝒉𝒂𝒔 𝒏𝒐𝒕 𝑺𝒆𝒕 𝑰𝒕 ! 📐")
  
  await igrone_error(query.answer)()
  button = [
    [
      InlineKeyboardButton(
        f"{'✅' if regex and str(regex) == str(i) else '' } {str(i)}", 
        callback_data=f"uregex_set_{i}") 
      for i in range(1, 5)
    ], 
    [
      InlineKeyboardButton("▏ᴅᴇʟᴇᴛᴇ▕", callback_data="uregex_delete"),
      InlineKeyboardButton("⇦ 𝗕𝗔𝗖𝗞", callback_data="mus")
    ]
  ]
  
  txt, thumbnali = get_user_txt(user_id)
  await retry_on_flood(query.edit_message_media)(
    media=InputMediaPhoto(random.choice(Vars.PICS), txt),
    reply_markup=InlineKeyboardMarkup(button)
  )



@Bot.on_callback_query(filters.regex("^u_compress"))
async def compress_handler(_, query):
  user_id = str(query.from_user.id)
  ensure_user(user_id)
  
  compress = uts[user_id]['setting'].get("compress", None)
  
  def get_button(compress):
    compress = int(compress) if compress else 2
    button = []
    button = [
      InlineKeyboardButton(
        f"{'✅' if int(compress) == i else '' } {str(i)}",
        callback_data=f"u_compress_set_{i}"
      )
      for i in range(0, 105, 5)
    ]
    
    button = [button[x:x + 5] for x in range(0, len(button), 5)]
    
    button.append([
      InlineKeyboardButton("▏ᴅᴇʟᴇᴛᴇ▕", callback_data="u_compress_delete"),
      InlineKeyboardButton("⇦ 𝗕𝗔𝗖𝗞", callback_data="mus")
    ])
    return InlineKeyboardMarkup(button)
  
  if query.data.startswith("u_compress_set"):
    compress = query.data.split("_")[-1]
    uts[user_id]['setting']["compress"] = compress
    sync()
    
    await retry_on_flood(query.answer)(" Successfully Added ")

  elif query.data == "u_compress_delete":
    if compress:
      uts[user_id]['setting']["compress"] = None
      sync()
      
      await retry_on_flood(query.answer)(" Successfully Deleted ")
    else:
      await retry_on_flood(query.answer)("📐 𝒀𝒐𝒖 𝒉𝒂𝒔 𝒏𝒐𝒕 𝑺𝒆𝒕 𝑰𝒕 ! 📐")
  
  txt, thumbnali = get_user_txt(user_id)
  await retry_on_flood(query.edit_message_media)(
    media=InputMediaPhoto(random.choice(Vars.PICS), txt),
    reply_markup=get_button(compress)
  )
