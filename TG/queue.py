from bot import Bot, Vars, logger
from pyrogram import filters
from TG.storage import retry_on_flood, queue
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
import random
import asyncio


def get_queue_markup(user_error=None):
    button = [
        [
            InlineKeyboardButton("⌜ᴄʟᴇᴀɴ ǫᴜᴇᴜᴇ⌟", callback_data="clean_queue"),
            InlineKeyboardButton("⌜sᴜʙsᴄʀɪᴘᴛɪᴏɴ⌟", callback_data="isubs")
        ],
        [
            InlineKeyboardButton("▏𝗖𝗟𝗢𝗦𝗘▕", callback_data="kclose"),
            InlineKeyboardButton("𝗥𝗘𝗙𝗥𝗘𝗦𝗛 ⟳", callback_data="refresh_queue")
        ]
    ]
    if user_error:
        button.append([InlineKeyboardButton("♕ ᴏᴡɴᴇʀ ♕", url=f"tg://user?id={Vars.OWNER}")])
    else:
        button.append([InlineKeyboardButton("♕ ᴏᴡɴᴇʀ ♕", url=f"tg://user?id={Vars.OWNER}")])
    
    return InlineKeyboardMarkup(button)

async def get_queue_text(user_id):
    try:
        total_tasks = queue.qsize()
        total_users = queue.get_count()
        ongoing_tasks = list(queue.ongoing_tasks.values())

        reply_txt = (
            f"<blockquote><b>📌 Queue Status (Total: {total_tasks} chapters & {total_users} Users)</b></blockquote>\n\n"
            "**👤 Your queue:**"
        )

        user_count = queue.get_count(user_id)

        if user_count != 0:
            reply_txt += f"""<blockquote expandable>=> <i>Total Chapters: {user_count}</i>\n"""

            # Check if user has ongoing task
            if user_id in queue.ongoing_tasks:
                task = queue.ongoing_tasks[user_id]
                reply_txt += f"=> <i>{task.manga_title} - {task.episode_number}</i>\n"
                reply_txt += "=> <i>Processing...</i>\n"
            else:
                # Get waiting tasks
                available_tasks = queue.get_available_tasks(user_id)
                if available_tasks:
                    task = available_tasks[0]
                    reply_txt += f"=> <i>{task.manga_title} - {task.episode_number}</i>\n"
                    reply_txt += "=> <i>Waiting...</i>\n"
                else:
                    reply_txt += "=> <i>In queue...</i>\n"
            reply_txt += "</blockquote>\n"
        else:
            reply_txt += "\n=> <i>No chapters in your queue.</i>\n"

        # Global processing section
        reply_txt += "\n**🚦 Now Processing:**\n"
        if ongoing_tasks:
            reply_txt += "<blockquote expandable>"
            for i, data in enumerate(ongoing_tasks, 1):
                try:
                    user_query = await Bot.get_users(int(data.user_id))
                    reply_txt += f"{i}. {user_query.mention()}\n"
                except Exception as e:
                    logger.warning(f"Failed to get user info for {data.user_id}: {e}")
                    reply_txt += f"{i}. User[{data.user_id}]\n"
            reply_txt += "</blockquote>\n"
        else:
            reply_txt += "=> <i>No active processing tasks.</i>\n"

        reply_txt += "<b>=> <i>Other chapters are in the waiting line.</i></b>"
        return reply_txt

    except Exception as e:
        logger.exception(f"Error generating queue text: {e}")
        return "❌ Error generating queue information."

@Bot.on_message(filters.command("queue"))
async def queue_msg_handler(client, message):
    if Vars.IS_PRIVATE and message.chat.id not in Vars.ADMINS:
        return await message.reply("<code>You cannot use this command.</code>")

    try:
        await retry_on_flood(message.reply_text)(
            await get_queue_text(message.from_user.id),
            quote=True,
            reply_markup=get_queue_markup()
        )
    except Exception:
        try:
            await retry_on_flood(message.reply_text)(
                await get_queue_text(message.from_user.id),
                quote=True,
                reply_markup=get_queue_markup(True)
            )
        except Exception as e:
            logger.error(f"Queue command error: {e}")
            await message.reply("❌ Failed to fetch queue information.")



@Bot.on_callback_query(filters.regex("^refresh_queue$"))
async def queue_refresh_handler(_, query):
    """Refresh queue information"""
    try:
        rand_photo = random.choice(Vars.PICS)
        await retry_on_flood(query.edit_message_media)(
            InputMediaPhoto(
                rand_photo, 
                caption=await get_queue_text(query.from_user.id)
            ),
            reply_markup=get_queue_markup()
        )
        await query.answer("✅ Queue refreshed!")
    except Exception as e:
        logger.error(f"Queue refresh error: {e}")
        await query.answer("❌ Failed to refresh queue.", show_alert=True)


@Bot.on_callback_query(filters.regex("^clean_queue$"))
async def clean_queue_handler(_, query):
    """Clean user's queue"""
    try:
        user_id = query.from_user.id
        if queue.get_count(user_id):
            numb = await queue.delete_tasks(user_id)
            await retry_on_flood(query.answer)(f"✅ All your tasks deleted: {numb}")

            await asyncio.sleep(1)
            rand_photo = random.choice(Vars.PICS)
            await query.edit_message_media(
                InputMediaPhoto(
                    rand_photo,
                    caption=await get_queue_text(user_id)
                ),
                reply_markup=get_queue_markup()
            )
        else:
            await retry_on_flood(query.answer)("ℹ️ There are no pending tasks in your queue.")
    except Exception as e:
        logger.error(f"Clean queue error: {e}")
        await query.answer("❌ Failed to clean queue.", show_alert=True)

