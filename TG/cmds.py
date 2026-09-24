from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .storage import *
import pyrogram.errors

from bot import Bot, Vars, logger
from .post import deliver_post

import random
from Tools.db import *
from Tools.my_token import check_token_, verify_token

import time

from asyncio import create_subprocess_exec
from os import execl
from sys import executable

import shutil, psutil, time, os, platform
import asyncio

from io import BytesIO



HELP_MSG = """
<b>To download a manga just type the name of the manga you want to keep up to date.</b>

For example:
`One Piece`

<blockquote expandable><i>Then you will have to choose the language of the manga. Depending on this language, you will be able to choose the website where you could download the manga. Here you will have the option to subscribe, or to choose a chapter to download. The chapters are sorted according to the website.</i></blockquote>

<blockquote><b>Updates Channel : @Wizard_bots</b></blockquote>
"""

@Bot.on_message(filters.private)
async def on_private_message(client, message):
  channel = Vars.FORCE_SUB_CHANNEL
  if channel in ["None", None, "none", "OFF", False, "False", ""]:
    return message.continue_propagation()

  if not client.FSB or client.FSB == []:
    return message.continue_propagation()

  channel_button, change_data = await check_fsb(client, message)
  if not channel_button:
    return message.continue_propagation()

  channel_button = split_list(channel_button)
  channel_button.append([InlineKeyboardButton("𝗥𝗘𝗙𝗥𝗘𝗦𝗛 ⟳", callback_data="refresh")])

  await retry_on_flood(message.reply_photo)(
      caption=Vars.FORCE_SUB_TEXT,
      photo=random.choice(Vars.PICS),
      reply_markup=InlineKeyboardMarkup(channel_button),
      quote=True,
  )
  if change_data:
    for change_ in change_data:
      client.FSB[change_[0]] = (change_[1], change_[2], change_[3])


@Bot.on_message(filters.command("info") & filters.user(Vars.ADMINS))
async def get_info_(client, message):
  sts = await message.reply("<code>Processing...</code>")
  try:
    user_id = str(message.text.split(" ")[1])
    if user_id in uts:
      txt = f"<b>User ID: {user_id}</b>\n"
      txt += f"<b>File Name: {uts[user_id]['setting'].get('file_name', 'None')}</b>\n"
      txt += f"<b>Caption: {uts[user_id]['setting'].get('caption', 'None')}</b>\n"
      txt += f"<b>Thumb: {uts[user_id]['setting'].get('thumb', 'None')}</b>\n"
      txt += f"<b>Banner1: {uts[user_id]['setting'].get('banner1', 'None')}</b>\n"
      txt += f"<b>Banner2: {uts[user_id]['setting'].get('banner2', 'None')}</b>\n"
      txt += f"<b>Dump: {uts[user_id]['setting'].get('dump', 'None')}</b>\n"
      txt += f"<b>Type: {uts[user_id]['setting'].get('type', 'None')}</b>\n"
      txt += f"<b>Merge: {uts[user_id]['setting'].get('megre', 'None')}</b>\n"
      txt += f"<b>Regex: {uts[user_id]['setting'].get('regex', 'None')}</b>\n"
      txt += f"<b>File Name Len: {uts[user_id]['setting'].get('file_name_len', 'None')}</b>\n"
      txt += f"<b>Password: {uts[user_id]['setting'].get('password', 'None')}</b>\n"
      txt += f"<b>Compress: {uts[user_id]['setting'].get('compress', 'None')}</b>\n"
      await retry_on_flood(sts.edit)(txt)
    else:
      ensure_user(user_id)
      await retry_on_flood(sts.edit)("<code>User Not Found</code>")
  except Exception as err:
    await retry_on_flood(sts.edit)(err)


@Bot.on_message(filters.command("my_plan"))
async def my_plan(client, message):
  plan = await premium_user(message.from_user.id)
  if plan:
    xt = (plan["expiration_timestamp"] - (time.time()))
    x = round(xt / (24 * 60 * 60))
    await message.reply(f"""
<i>Your Information:</i>

  <b>- User ID: {message.from_user.id}</b>
  <b>- Username: {message.from_user.username}</b>
  <b>- Days: {plan.get("Days", "")}</b>
  <b>- Expiration Days: {x}</b> 

<i>Thanks For Buying It......</i>""",
                        quote=True,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("▏𝗖𝗟𝗢𝗦𝗘▕", callback_data="kclose")]]))
  else:
    await message.reply("<i> You Have No Plan!! </i>",
                        reply_markup=InlineKeyboardMarkup([
                          [InlineKeyboardButton(" Buy Now ", callback_data="premuim")]
                        ]))


@Bot.on_message(filters.command(["clean_tasks", "clean_queue"]))
async def deltask(client, message):
  if Vars.IS_PRIVATE:
    if message.chat.id not in Vars.ADMINS:
      return await message.reply(Vars.PRIVATE_TXT)

  if queue.get_count(message.from_user.id):
    numb = await queue.delete_tasks(message.from_user.id)
    await message.reply(f"<i>All Your Tasks Deleted:- {numb} </i>")
  else:
    await message.reply("<i>There is no any your pending tasks.... </i>")


START_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⚙️ Settings", callback_data="mus"),
        InlineKeyboardButton("❓ Help", callback_data="help_cb"),
    ],
    [
        InlineKeyboardButton("🆘 Support Group", url="https://t.me/WizardBotHelper"),
        InlineKeyboardButton("📢 Updates Channel", url="https://t.me/Wizard_bots"),
    ],
    [
        InlineKeyboardButton("⭐ Star on GitHub", url="https://github.com/Dra-Sama/Manhwa-Bot"),
    ],
    [
        InlineKeyboardButton("✖️ Close", callback_data="kclose"),
    ],
])


@Bot.on_message(filters.command("start"))
async def start(client, message):
  if Vars.IS_PRIVATE:
    if message.chat.id not in Vars.ADMINS:
      return await message.reply(Vars.PRIVATE_TXT)

  ensure_user(message.from_user.id)
  if len(message.command) > 1:
    param = message.command[1]
    if param != "start":
      # Deep link from a "📖 Read Now" button under a channel post:
      # https://t.me/<bot>?start=get_<post_id>
      if param.startswith("get_"):
        post_id = param.removeprefix("get_")
        return await deliver_post(client, message, post_id)

      user_id = message.from_user.id
      token = param
      sts = await message.reply("<i>ㅤProcessing.....</i>")
      return await verify_token(sts, user_id, token)

  photo = random.choice(Vars.PICS)
  ping = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - Vars.PING))
  await message.reply_photo(
      photo,
      caption=
      ("<b><i>👋 Welcome to the best manga/manhwa/manhua PDF bot on Telegram!</i></b>\n"
       "\n"
       "<b><i>How to use it?</i></b> Just type the name of the manga you want, "
       "e.g. <code>One Piece</code>, and I'll help you search, read and download it.\n"
       "\n"
       f"<b><i>⚡ Ping:</i></b> <code>{ping}</code>\n"
       "\n"
       "<b><i>Tap /help for a full guide.</i></b>"),
      reply_markup=START_BUTTONS)


@Bot.on_callback_query(filters.regex("^help_cb$"))
async def help_callback(client, query):
  await igrone_error(query.answer)()
  button = InlineKeyboardMarkup([[InlineKeyboardButton("⇦ Back", callback_data="start_cb")]])
  await retry_on_flood(query.edit_message_caption)(HELP_MSG, reply_markup=button)


@Bot.on_callback_query(filters.regex("^start_cb$"))
async def back_to_start_callback(client, query):
  await igrone_error(query.answer)()
  ping = time.strftime("%Hh%Mm%Ss", time.gmtime(time.time() - Vars.PING))
  caption = (
      "<b><i>👋 Welcome to the best manga/manhwa/manhua PDF bot on Telegram!</i></b>\n"
      "\n"
      "<b><i>How to use it?</i></b> Just type the name of the manga you want, "
      "e.g. <code>One Piece</code>, and I'll help you search, read and download it.\n"
      "\n"
      f"<b><i>⚡ Ping:</i></b> <code>{ping}</code>\n"
      "\n"
      "<b><i>Tap /help for a full guide.</i></b>")
  await retry_on_flood(query.edit_message_caption)(caption, reply_markup=START_BUTTONS)



@Bot.on_message(filters.command(["add", "add_premium"]) & filters.user(Vars.ADMINS))
async def add_handler(_, msg):
  sts = await msg.reply_text("<code>Processing...</code>")
  try:
    user_id = int(msg.text.split(" ")[1])
    time_limit_days = int(msg.text.split(" ")[2])
    await add_premium(user_id, time_limit_days)
    await retry_on_flood(sts.edit)("<code>User added to premium successfully.</code>")
    try:
      await retry_on_flood(_.send_message)(
        user_id,
        f"<i>You are now a premium user for {time_limit_days} days... Thanks For Buying It.....</i>"
      )
    except:
      pass
  except Exception as err:
    await retry_on_flood(sts.edit)(err)


@Bot.on_message(filters.command(["del", "del_premium"]) & filters.user(Vars.ADMINS))
async def del_handler(_, msg):
  sts = await msg.reply_text("<code>Processing...</code>")
  try:
    user_id = int(msg.text.split(" ")[1])
    await remove_premium(user_id)
    await retry_on_flood(sts.edit)("<code>User removed from premium successfully.</code>")
    try:
      await retry_on_flood(_.send_message)(
        user_id,
        "<i>Your Premuims Plans End.. Please Buy again or Contact To Owner....  .</i>"
      )
    except:
      pass
  except Exception as err:
    await retry_on_flood(sts.edit)(err)


@Bot.on_message(filters.command(["del_expired", "del_expired_premium"]) & filters.user(Vars.ADMINS))
async def del_expired_handler(_, msg):
  sts = await msg.reply_text("<code>Processing...</code>")
  try:
    await remove_expired_users()
    await retry_on_flood(sts.edit)("<code>Expired users removed successfully.</code>")
  except Exception as err:
    await retry_on_flood(sts.edit)(err)


@Bot.on_message(filters.command(["premium", "premium_users"]) & filters.user(Vars.ADMINS))
async def premium_handler(_, msg):
  sts = await msg.reply_text("<code>Processing...</code>")
  try:
    txt = "<b>Premium Users:-</b>\n"
    async for user_ids, data in get_all_premuim():
      user_info = await _.get_users(user_ids)
      username = user_info.username
      first_name = user_info.first_name
      expiration_timestamp = data["expiration_timestamp"]
      xt = (expiration_timestamp - (time.time()))
      x = round(xt / (24 * 60 * 60))
      txt += f"User id: <code>{user_ids}</code>\nUsername: @{username}\nName: <code>{first_name}</code>\nExpiration Timestamp: {x} days\n"

    await retry_on_flood(sts.edit)(txt[:1024])
  except Exception as err:
    await retry_on_flood(sts.edit)(err)


@Bot.on_message(filters.command(["broadcast", "b"]) & filters.user(Vars.ADMINS))
async def b_handler(_, msg):
  return await borad_cast_(_, msg)


@Bot.on_message(filters.command(["pbroadcast", "pb"]) & filters.user(Vars.ADMINS))
async def pb_handler(_, msg):
  return await borad_cast_(_, msg, pin=True)

@Bot.on_message(filters.command(["forward", "fd"]) & filters.user(Vars.ADMINS))
async def fb_handler(_, msg):
  return await borad_cast_(_, msg, forward=True)

@Bot.on_message(filters.command(["pforward", "pfd"]) & filters.user(Vars.ADMINS))
async def pfb_handler(_, msg):
  return await borad_cast_(_, msg, pin=True, forward=True)

async def borad_cast_(_, message, pin=None, forward=None):

  def del_users(user_id):
    try:
      user_id = str(user_id)
      del uts[user_id]
      sync()
    except:
      pass

  sts = await message.reply_text("<code>Processing...</code>")
  if message.reply_to_message:
    user_ids = get_users()
    if not user_ids:
      return await retry_on_flood(sts.edit)("<code>No users found.</code>")
    
    msg = message.reply_to_message
    total = 0
    successful = 0
    blocked = 0
    deleted = 0
    unsuccessful = 0
    await retry_on_flood(sts.edit)("<code>Broadcasting...</code>")
    for user_id in user_ids:
      try:
        docs = await msg.forward(int(user_id)) if forward else await msg.copy(int(user_id))
        if pin:
          await docs.pin(both_sides=True)

        successful += 1
      except FloodWait as e:
        await asyncio.sleep(e.value)

        docs = await msg.copy(int(user_id))
        if pin:
          await docs.pin(both_sides=True)

        successful += 1
      except pyrogram.errors.UserIsBlocked:
        del_users(user_id)
        blocked += 1
      except pyrogram.errors.PeerIdInvalid:
        del_users(user_id)
        unsuccessful += 1
      except pyrogram.errors.InputUserDeactivated:
        del_users(user_id)
        deleted += 1
      except pyrogram.errors.UserNotParticipant:
        del_users(user_id)
        blocked += 1
      except:
        unsuccessful += 1

    status = f"""<b><u>Broadcast Completed</u>

    Total Users: <code>{total}</code>
    Successful: <code>{successful}</code>
    Blocked Users: <code>{blocked}</code>
    Deleted Accounts: <code>{deleted}</code>
    Unsuccessful: <code>{unsuccessful}</code></b>"""

    await retry_on_flood(sts.edit)(status)
  else:
    await retry_on_flood(sts.edit)("<code>Reply to a message to broadcast it.</code>")


@Bot.on_message(filters.command("restart") & filters.user(Vars.ADMINS))
async def restart_(client, message):
  msg = await message.reply_text("<code>Restarting.....</code>", quote=True)
  with open("restart_msg.txt", "w") as file:
    file.write(str(msg.chat.id) + ":" + str(msg.id))
    file.close()

  await (await create_subprocess_exec("python3", "update.py")).wait()
  execl(executable, executable, "-B", "main.py")



def humanbytes(size):
  if not size:
    return ""
  units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
  size = float(size)
  i = 0
  while size >= 1024.0 and i < len(units) - 1:
    i += 1
    size /= 1024.0
  return "%.2f %s" % (size, units[i])


def get_process_stats():
  p = psutil.Process(os.getpid())
  try:
      cpu = p.cpu_percent(interval=0.5)
  except Exception:
      cpu = "N/A"
  try:
      mem_info = p.memory_info()
      rss = humanbytes(mem_info.rss)
      vms = humanbytes(mem_info.vms)
  except Exception:
      rss = vms = "N/A"
  return (
      f" ├ CPU: {cpu}%\n"
      f" ├ RAM (RSS): {rss}\n"
      f" └ RAM (VMS): {vms}"
  )

@Bot.on_message(filters.command('stats'))
async def show_stats(client, message):
  total_disk, used_disk, free_disk = shutil.disk_usage(".")
  total_disk_h = humanbytes(total_disk)
  used_disk_h = humanbytes(used_disk)
  free_disk_h = humanbytes(free_disk)
  disk_usage_percent = psutil.disk_usage('/').percent

  net_start = psutil.net_io_counters()
  time.sleep(2)
  net_end = psutil.net_io_counters()

  bytes_sent = net_end.bytes_sent - net_start.bytes_sent
  bytes_recv = net_end.bytes_recv - net_start.bytes_recv

  cpu_cores = os.cpu_count()
  cpu_usage = psutil.cpu_percent()

  ram = psutil.virtual_memory()
  ram_total = humanbytes(ram.total)
  ram_used = humanbytes(ram.used)
  ram_free = humanbytes(ram.available)
  ram_usage_percent = ram.percent

  try:
    uptime_seconds = time.time() - Vars.PING
    uptime = time.strftime("%Hh %Mm %Ss", time.gmtime(uptime_seconds))
  except:
    uptime = "N/A"

  start_time = time.time()
  status_msg = await message.reply('📊 **Accessing System Details...**')
  end_time = time.time()
  time_taken_ms = int((end_time - start_time) * 1000)

  os_name = platform.system()
  os_version = platform.release()
  python_version = platform.python_version()

  response_text = f"""
🖥️ **System Statistics Dashboard**

💾 **Disk Storage**
├ Total:  `{total_disk_h}`
├ Used:  `{used_disk_h}` ({disk_usage_percent}%)
└ Free:  `{free_disk_h}`

🧠 **RAM (Memory)**
├ Total:  `{ram_total}`
├ Used:  `{ram_used}` ({ram_usage_percent}%)
└ Free:  `{ram_free}`

⚡ **CPU**
├ Cores:  `{cpu_cores}`
└ Usage:  `{cpu_usage}%`

🔌 **Bot Process**
{get_process_stats()}

🌐 **Network**
├ Upload Speed:  `{humanbytes(bytes_sent/2)}/s`
├ Download Speed:  `{humanbytes(bytes_recv/2)}/s`
└ Total I/O:  `{humanbytes(net_end.bytes_sent + net_end.bytes_recv)}`

📟 **System Info**
├ OS:  `{os_name}`
├ OS Version:  `{os_version}`
├ Python:  `{python_version}`
└ Uptime:  `{uptime}`

⏱️ **Performance**
└ Current Ping:  `{time_taken_ms:.3f} ms`
"""

  await retry_on_flood(message.reply_text)(response_text, quote=True)
  await retry_on_flood(status_msg.delete)()


@Bot.on_message(filters.command("shell") & filters.user(Vars.ADMINS))
async def shell(_, message):
  cmd = message.text.split(maxsplit=1)
  if len(cmd) == 1:
    return await message.reply("<code>No command to execute was given.</code>")

  cmd = cmd[1]
  proc = await asyncio.create_subprocess_shell(
    cmd, stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
  )
  stdout, stderr = await proc.communicate()
  stdout = stdout.decode().strip()
  stderr = stderr.decode().strip()
  reply = ""
  if len(stdout) != 0:
    reply += f"<b>Stdout</b>\n<blockquote>{stdout}</blockquote>\n"
  if len(stderr) != 0:
    reply += f"<b>Stderr</b>\n<blockquote>{stderr}</blockquote>"

  if len(reply) > 3000:
    bio = BytesIO()
    bio.write(str(reply).encode('utf-8'))
    bio.seek(0)
  
    await message.reply_document(bio, file_name="shell_output.txt")
    bio.close()
    
  elif len(reply) != 0:
    await message.reply(reply)
  else:
    await message.reply("No Reply")


@Bot.on_message(filters.command("export") & filters.user(Vars.ADMINS))
async def export_(_, message):
  cmd = message.text.split(maxsplit=1)
  if len(cmd) == 1:
    return await message.reply("<code>File Name Not given.</code>")

  sts = await message.reply("<code>Processing...</code>")
  try:
    file_name = cmd[1]
    if "*2" in file_name:
      file_name = file_name.replace("*2", "")
      file_name = f"__{file_name}__"

    if os.path.exists(file_name):
      await message.reply_document(file_name)
    else:
      await sts.edit("<code>File Not Found</code>")
  except Exception as err:
    await sts.edit(err)


@Bot.on_message(filters.command("import") & filters.user(Vars.ADMINS))
async def import_(_, message):
  cmd = message.text.split(maxsplit=1)
  if len(cmd) == 1:
    return await message.reply("<code>File Name Not given.</code>")

  sts = await message.reply("<code>Processing...</code>")
  try:
    file_name = cmd[1]
    if "*2" in file_name:
      file_name = file_name.replace("*2", "")
      file_name = f"__{file_name}__"

    if not os.path.exists(file_name):
      await message.download(file_name, file_name=file_name)
    else:
      await sts.edit("<code>File Path Found</code>")
  except Exception as err:
    await sts.edit(err)


@Bot.on_message(filters.command(["clean", "c"]) & filters.user(Vars.ADMINS))
async def clean(_, message):
  directory = '/app'
  ex = (".mkv", ".mp4", ".zip", ".pdf", ".png", ".epub", ".temp")
  protected_dirs = (".git", "venv", "env", "__pycache__"
                    )  # Directories to SKIP
  sts = await message.reply_text("🔍 Cleaning files...")
  deleted_files = []
  removed_dirs = []

  if os.path.exists("Process"):
    shutil.rmtree("Process")
  elif os.path.exists("./Process"):
    shutil.rmtree("./Process")

  try:
    for root, dirs, files in os.walk(directory, topdown=False):
      # Skip protected directories (e.g., .git)
      dirs[:] = [d for d in dirs if d not in protected_dirs]
      for file in files:
        if file.lower().endswith(ex):
          file_path = os.path.join(root, file)
          try:
            os.remove(file_path)
            deleted_files.append(file_path)
          except Exception as e:
            pass

        elif file.lower().startswith("vol"):
          file_path = os.path.join(root, file)
          try:
            os.remove(file_path)
            deleted_files.append(file_path)
          except Exception as e:
            pass

      for dir_name in dirs:
        dir_path = os.path.join(root, dir_name)
        try:
          if not os.listdir(dir_path):  # Check if empty
            os.rmdir(dir_path)
            removed_dirs.append(dir_path)

          elif dir_path == "/app/Downloads":
            os.rmdir("/app/Downloads")
            removed_dirs.append("/app/Downloads")

          elif dir_path == "/app/downloads":
            os.rmdir("/app/downloads")
            removed_dirs.append("/app/downloads")

          try:
            dir_path = int(dir_path)
            os.rmdir(dir_path)
            removed_dirs.append(dir_path)
          except:
            pass
        except Exception as e:
          pass

    msg = "**🧹 Cleaning Logs:**\n"
    if deleted_files:
      msg += f"🗑 **Deleted {len(deleted_files)} files:**\n" + "\n".join(
          deleted_files[:10])  # Show first 10
      if len(deleted_files) > 10:
        msg += f"\n...and {len(deleted_files) - 10} more."
      else:
        msg += "✅ No files deleted."

    if removed_dirs:
      msg += f"\n\n📁 **Removed {len(removed_dirs)} empty directories:**\n" + "\n".join(
          removed_dirs[:5])
      if len(removed_dirs) > 5:
        msg += f"\n...and {len(removed_dirs) - 5} more."

    await sts.edit(msg[:4096])  # Telegram's max message length
  except Exception as err:
    await sts.edit(f"❌ Error: {str(err)}")


def remove_dir(path):
  try:
    if os.path.exists(path):
      for root, dirs, files in os.walk(path, topdown=False):
        for file in files:
          os.remove(os.path.join(root, file))
          for dir in dirs:
            os.rmdir(os.path.join(root, dir))
      os.rmdir(path)
  except Exception as err:
    return err


@Bot.on_message(filters.command("help"))
async def help(client, message):
  if Vars.IS_PRIVATE:
    if message.chat.id not in Vars.ADMINS:
      return await message.reply(Vars.PRIVATE_TXT)

  return await message.reply(HELP_MSG)



