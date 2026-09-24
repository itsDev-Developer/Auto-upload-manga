from TG.storage import retry_on_flood, igrone_error, queue
from bot import Bot, Vars, logger


from Tools.img2cbz import images_to_cbz
from Tools.img2pdf import ( 
    download_and_convert_images, convert_images_to_pdf,
)

import os
import shutil
import asyncio

from time import time
from pyrogram.types import InputMediaDocument

from Tools.base import TaskCard


LOGS_MESSAGE = """
{caption}

{url}

`Downloaded By`: `{user_id}`  [{mention}]
`PDF Password`: `{password}`
`Time Taken`: `{time_taken}`"""

class NormalError(BaseException):
  def __init__(self):
    pass


async def send_error(task_card: TaskCard, error_text):
  if task_card.sts:
    docs = await retry_on_flood(task_card.sts.edit)(
      f"{task_card.url} : `{error_text}`"
    )
  else:
    docs = await retry_on_flood(Bot.send_message)(
      int(task_card.user_id), f"{task_card.url} : `{error_text}`"
    )

  await retry_on_flood(docs.copy)(Vars.LOG_CHANNEL) if Vars.LOG_CHANNEL else None



async def send_manga_chapter(
  tasks_card: TaskCard,
):
  start_time = time()
  error_msg = None

  download_dir = None
  compressed_dir = None

  pdf_output_path = None
  cbz_output_path = None

  password = None
  banner_setting = await tasks_card.get_banner()
  thumb = banner_setting.get("thumb_file_name", None)
  banner1 = banner_setting.get("banner1_file_path", None)
  banner2 = banner_setting.get("banner2_file_path", None)

  #user_id = str(tasks_card.user_id)
  media_docs = []
  main_dir = f"Process/{tasks_card.tasks_id}"
  try:
    file_name = tasks_card.setting.get('file_name', None)
    if not file_name:
      file_name = "Chapter {episode_number} {manga_title}"

    if tasks_card.webs.sf == "mf" and "Vol" in tasks_card.manga_title or "Volume" in tasks_card.manga_title:
      file_name = file_name.replace("Chapter", "Vol")

    file_name = file_name.replace("{episode_number}", tasks_card.episode_number).replace("{manga_title}", tasks_card.manga_title).replace("{chapter_num}", tasks_card.episode_number) if file_name else f'{tasks_card.episode_number} - {tasks_card.manga_title}'

    caption = tasks_card.setting.get('caption', "<blockquote>{file_name}</blockquote>")
    if not caption:
      caption = "<blockquote>{file_name}</blockquote>"

    caption = caption.replace("{file_name}", file_name).replace("{episode_number}", tasks_card.episode_number).replace("{manga_title}", tasks_card.manga_title).replace("{chapter_num}", tasks_card.episode_number) if caption else file_name

    download_dir = f"{main_dir}/pictures"
    compressed_dir = f"{main_dir}/compress"

    try:
      cs = True if tasks_card.webs.cs is True else False
    except Exception:
      cs = False

    if not tasks_card.picturesList:
      await igrone_error(send_error)(tasks_card, "Error at Getting Picture")
      raise NormalError()

    downloads_list = await download_and_convert_images(
      tasks_card.picturesList, download_dir, 
      tasks_card.webs.url, cs=cs
    )
    if banner1:
      downloads_list.insert(0, banner1)
    if banner2:
      downloads_list.append(banner2)

    await igrone_error(tasks_card.sts.edit)("<code>Downloading.....</code>") if tasks_card.sts else None

    file_type = tasks_card.setting.get('type', ['PDF', 'CBZ'])

    if "PDF" in file_type:
      pdf_output_path = f"{main_dir}/{file_name}.pdf"
      password = tasks_card.setting.get('password', None)
      compress = int(compress) if (compress:= tasks_card.setting.get("compress", "30")) else 30

      ## from here
      if (test := await asyncio.to_thread(
        convert_images_to_pdf, downloads_list, pdf_output_path,
        compressed_dir, password, compress)):

        await igrone_error(send_error)(tasks_card, test)
        raise NormalError()

      else:
        media_docs.append(InputMediaDocument(pdf_output_path, caption=caption, thumb=thumb))

    if "CBZ" in file_type:
      cbz_output_path = f"{main_dir}/{file_name}.cbz"

      if ( test := await asyncio.to_thread(
        images_to_cbz, downloads_list, cbz_output_path)):

        await igrone_error(send_error)(tasks_card, test)
        raise NormalError()
      else:
        media_docs.append(InputMediaDocument(cbz_output_path, caption=caption, thumb=thumb))

    if len(media_docs) > 0:
      doc = await retry_on_flood(Bot.send_media_group)(int(tasks_card.chat_id), media_docs)

      # tasks_card.setting IS ALREADY the user's "setting" sub-dict (see TaskCard.__init__),
      # so it must be read directly. Reading .get('setting', {}) again always returned {}
      # which silently disabled every user's personal Dump Channel. Fixed.
      dump = tasks_card.setting.get('dump', None)
      if Vars.CONSTANT_DUMP_CHANNEL:
        try:
          await retry_on_flood(Bot.copy_media_group)(
            int(Vars.CONSTANT_DUMP_CHANNEL), int(tasks_card.chat_id), doc.id
          )
        except Exception:
          await igrone_error(send_error)(
            tasks_card, "Add Bot At Constant Dump Channel OR Provide Vaild Dump Channel"
          )
          await asyncio.sleep(10)

      elif dump:
        try:
          await retry_on_flood(Bot.copy_media_group)(
            int(dump), int(tasks_card.chat_id), doc.id
          )
        except Exception:
          await igrone_error(send_error)(
            tasks_card, "Add Bot At Dump Channel OR Provide Vaild Dump Channel"
          )
          await asyncio.sleep(10)

      if Vars.LOG_CHANNEL:
        async def log_msg():
          time_taken = time() - start_time
          minutes, seconds = divmod(int(time_taken), 60)
          time_taken = f"{minutes}m, {seconds}s"

          user = await Bot.get_users(int(tasks_card.user_id))

          return LOGS_MESSAGE.format(
            caption=caption,
            url=tasks_card.url,
            user_id=tasks_card.user_id,
            mention=user.mention(),
            password=password,
            time_taken=time_taken
          )

        media_docs[-1].caption = await log_msg()
        try:
          await retry_on_flood(Bot.send_media_group)(Vars.LOG_CHANNEL, media_docs)
        except:
          pass

  except NormalError:
    error_msg = True
    pass

  except Exception as e:
    error_msg = True
    await igrone_error(send_error)(
      tasks_card, str(e)
    )

    logger.exception(f"Error processing task: {e}")

  finally:
    if (tasks_card.setting.get("thumb", None) in ["constant"]) and thumb and os.path.exists(thumb):
      await igrone_error(os.remove, True)(thumb)

    if tasks_card.check_queue() is True:
      shutil.rmtree(f"Process/{tasks_card.user_id}", ignore_errors=True)

    if pdf_output_path and os.path.exists(pdf_output_path):
      await igrone_error(os.remove, True)(pdf_output_path)

    if cbz_output_path and os.path.exists(cbz_output_path):
      await igrone_error(os.remove, True)(cbz_output_path)

    if download_dir and os.path.exists(download_dir):
      shutil.rmtree(download_dir, ignore_errors=True)

    if compressed_dir and os.path.exists(compressed_dir):
      shutil.rmtree(compressed_dir, ignore_errors=True)

    if main_dir and os.path.exists(main_dir):
      shutil.rmtree(main_dir, ignore_errors=True)

    if not error_msg:
      await igrone_error(tasks_card.sts.delete)() if tasks_card.sts else None


async def worker(worker_id: int = 1):
  while True:
    tasks_card, _ = await queue.get(worker_id)
    logger.info(f"Worker {worker_id} processing task {tasks_card.tasks_id}")
    await retry_on_flood(tasks_card.sts.edit)("<code>Processing.....</code>") if tasks_card.sts else None
    try:
      if tasks_card.picturesList:
        try: 
          await send_manga_chapter(tasks_card)
        except Exception as error:
          logger.exception(f"Worker {worker_id} encountered an error: {error}")
          await send_error(tasks_card, error)
      else:
        await igrone_error(send_error)(
          tasks_card, "Error at Getting Picture",
        )

    except Exception as err:
      logger.exception(f"Worker {worker_id} encountered an error: {err}")
    finally:
      await queue.task_done(tasks_card)
