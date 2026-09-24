"""
Post Manager
============
Lets an admin/owner publish a formatted post (poster + title + genre +
description + a "📖 Read Now" button) to a public/private "Post Channel".

Workflow:
  1. Admin sets a Dump Channel and a Post Channel once via /postsettings
     (the bot must be an admin in both).
  2. Admin runs /newpost (or taps "➕ Create New Post"). The bot asks for the
     file(s) first -> each one is copied into the Dump Channel and its
     message id is remembered. Then it asks for poster / title / genre /
     description, shows a preview, and publishes on confirmation.
  3. The published post's "📖 Read Now" button is a deep link
     (https://t.me/<bot>?start=get_<post_id>). Clicking it opens a private
     chat with the bot, which fetches the stored file(s) from the Dump
     Channel and copies them straight to the user.
"""

import asyncio
import random
import string
import time

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import ListenerTimeout as TimeoutError

from bot import Bot, Vars, logger
from Tools.db import (
    get_config, set_config, save_post, get_post,
    delete_post, all_posts, bump_post_reads,
)
from .storage import retry_on_flood, igrone_error


# In-memory wizard drafts, keyed by the admin's user_id, while a post is
# being built and awaiting "✅ Confirm & Publish".
_drafts = {}

CANCEL_WORDS = ("/cancel", "cancel")


def _gen_post_id() -> str:
    chars = string.ascii_letters + string.digits
    while True:
        pid = "".join(random.choices(chars, k=8))
        if not get_post(pid):
            return pid


def _norm_channel(value):
    """Channel values may be a numeric id or a @username - keep whichever it is."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def get_post_channel():
    return get_config("post_channel", Vars.POST_CHANNEL)


def get_dump_channel():
    return get_config("dump_channel", Vars.DUMP_CHANNEL)


def _build_caption(title, genre_txt, description):
    caption = f"🎴 <b>{title}</b>\n\n"
    if genre_txt:
        caption += f"🏷 <b>Genre:</b> {genre_txt}\n\n"
    caption += f"📖 <b>Synopsis:</b>\n<blockquote expandable>{description}</blockquote>\n\n"
    caption += "👇 Tap below to get this manga."
    return caption[:1024]


def _settings_text():
    post_channel = get_post_channel()
    dump_channel = get_dump_channel()
    total = len(all_posts())
    return (
        "<b>📮 Post Manager</b>\n\n"
        f"<b>📢 Post Channel:</b> <code>{post_channel or 'Not Set'}</code>\n"
        f"<b>📥 Dump Channel:</b> <code>{dump_channel or 'Not Set'}</code>\n"
        f"<b>📚 Total Posts:</b> <code>{total}</code>\n\n"
        "<blockquote expandable>"
        "• <b>Dump Channel</b> — where the actual manga files are stored. The bot "
        "downloads/keeps files here, and later serves them to users.\n"
        "• <b>Post Channel</b> — where the poster + title + genre + description + "
        "\"Read Now\" post gets published.\n"
        "• The bot must be an <b>admin</b> in both channels."
        "</blockquote>"
    )


def _settings_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Set Post Channel", callback_data="pmset_post"),
            InlineKeyboardButton("📥 Set Dump Channel", callback_data="pmset_dump"),
        ],
        [InlineKeyboardButton("➕ Create New Post", callback_data="pmp_new")],
        [InlineKeyboardButton("📋 Manage Posts", callback_data="pmp_manage:1")],
        [InlineKeyboardButton("✖️ Close", callback_data="kclose")],
    ])


# ---------------------------------------------------------------------------
# /postsettings — configure Post Channel & Dump Channel, manage posts
# ---------------------------------------------------------------------------

@Bot.on_message(filters.command(["postsettings", "pm"]) & filters.user(Vars.ADMINS))
async def post_settings_cmd(client, message):
    await retry_on_flood(message.reply_text)(
        _settings_text(), quote=True, reply_markup=_settings_markup()
    )


@Bot.on_callback_query(filters.regex("^pmpanel$") & filters.user(Vars.ADMINS))
async def post_settings_panel_cb(client, query):
    await igrone_error(query.answer)()
    await retry_on_flood(query.edit_message_text)(
        _settings_text(), reply_markup=_settings_markup()
    )


@Bot.on_callback_query(filters.regex("^pmset_") & filters.user(Vars.ADMINS))
async def post_settings_set_cb(client, query):
    kind = query.data.removeprefix("pmset_")  # "post" or "dump"
    label = "Post Channel" if kind == "post" else "Dump Channel"
    await igrone_error(query.answer)()

    await retry_on_flood(query.edit_message_text)(
        f"<b>📐 Send the {label}</b>\n\n"
        "<blockquote>Forward any message from that channel, or send its "
        "username (without @) or numeric ID. Make sure the bot is an admin "
        f"there.\n\nSend /cancel to abort.</blockquote>"
    )

    try:
        call = await client.listen(
            user_id=query.from_user.id, timeout=120,
            filters=filters.text | filters.forwarded,
        )
    except TimeoutError:
        return await retry_on_flood(query.message.edit_text)(
            "📐 Timed out. Run /postsettings again."
        )

    if call.text and call.text.strip().lower() in CANCEL_WORDS:
        await igrone_error(call.delete)()
        return await retry_on_flood(query.message.edit_text)(
            _settings_text(), reply_markup=_settings_markup()
        )

    value = None
    if call.forward_from_chat:
        value = call.forward_from_chat.id
    elif call.text:
        text = call.text.strip()
        try:
            value = int(text)
        except ValueError:
            value = text

    await igrone_error(call.delete)()

    if value is None:
        return await retry_on_flood(query.message.edit_text)(
            "❌ Couldn't read that as a channel. Run /postsettings again."
        )

    set_config(f"{kind}_channel", value)
    await retry_on_flood(query.message.edit_text)(f"✅ {label} set to <code>{value}</code>.")
    await asyncio.sleep(1.5)
    await retry_on_flood(query.message.edit_text)(
        _settings_text(), reply_markup=_settings_markup()
    )


# ---------------------------------------------------------------------------
# /newpost — step-by-step wizard to build & publish a post
# ---------------------------------------------------------------------------

@Bot.on_callback_query(filters.regex("^pmp_new$") & filters.user(Vars.ADMINS))
async def new_post_cb(client, query):
    await igrone_error(query.answer)()
    await create_post_wizard(client, query.message.chat.id, query.from_user.id)


@Bot.on_message(filters.command("newpost") & filters.user(Vars.ADMINS))
async def new_post_cmd(client, message):
    await create_post_wizard(client, message.chat.id, message.from_user.id)


async def _ask(client, chat_id, admin_id, text, timeout=180):
    """Send a prompt and wait for the admin's next message."""
    await retry_on_flood(client.send_message)(chat_id, text)
    try:
        return await client.listen(user_id=admin_id, timeout=timeout)
    except TimeoutError:
        await retry_on_flood(client.send_message)(chat_id, "⏰ Timed out. Post creation cancelled.")
        return None


async def create_post_wizard(client, chat_id, admin_id):
    dump_channel = get_dump_channel()
    if not dump_channel:
        return await retry_on_flood(client.send_message)(
            chat_id,
            "❌ No <b>Dump Channel</b> is set yet. Set one first with /postsettings."
        )

    file_ids = []

    # Step 1 — files, saved straight into the Dump Channel
    await retry_on_flood(client.send_message)(
        chat_id,
        "<b>📁 Step 1/5 — Files</b>\n\n"
        "Send the file(s) for this post one at a time (documents, PDFs, "
        "images, or forward them from anywhere). They'll be stored in the "
        "Dump Channel.\n\nSend <code>/done</code> when finished, or "
        "<code>/cancel</code> to abort."
    )
    while True:
        try:
            call = await client.listen(user_id=admin_id, timeout=300)
        except TimeoutError:
            return await retry_on_flood(client.send_message)(chat_id, "⏰ Timed out. Post creation cancelled.")

        text = (call.text or "").strip().lower()
        if text == "/cancel":
            await igrone_error(call.delete)()
            return await retry_on_flood(client.send_message)(chat_id, "❌ Post creation cancelled.")

        if text == "/done":
            await igrone_error(call.delete)()
            break

        media = call.document or call.video or call.audio or call.photo or call.animation
        if not media:
            await retry_on_flood(client.send_message)(chat_id, "⚠️ Send a file, or /done, or /cancel.")
            continue

        try:
            copied = await retry_on_flood(call.copy)(_norm_channel(dump_channel))
            file_ids.append(copied.id)
            await retry_on_flood(client.send_message)(
                chat_id,
                f"✅ Saved to Dump Channel ({len(file_ids)} file(s) so far). Send another, or /done."
            )
        except Exception as e:
            logger.exception(e)
            await retry_on_flood(client.send_message)(
                chat_id,
                f"❌ Couldn't save that to the Dump Channel: <code>{e}</code>\n"
                "Make sure the bot is an admin there."
            )

    if not file_ids:
        return await retry_on_flood(client.send_message)(chat_id, "❌ No files were saved. Post creation cancelled.")

    # Step 2 — poster
    reply = await _ask(
        client, chat_id, admin_id,
        "<b>🖼 Step 2/5 — Poster</b>\n\nSend the poster image (as a photo), or paste an image URL."
    )
    if reply is None:
        return
    if reply.text and reply.text.strip().lower() in CANCEL_WORDS:
        await igrone_error(reply.delete)()
        return await retry_on_flood(client.send_message)(chat_id, "❌ Post creation cancelled.")

    poster = None
    if reply.photo:
        poster = reply.photo.file_id
    elif reply.text and reply.text.strip().startswith("http"):
        poster = reply.text.strip()
    await igrone_error(reply.delete)()

    if not poster:
        return await retry_on_flood(client.send_message)(chat_id, "❌ That's not a valid poster. Post creation cancelled.")

    # Step 3 — title
    reply = await _ask(client, chat_id, admin_id, "<b>📝 Step 3/5 — Title</b>\n\nSend the manga's title.")
    if reply is None:
        return
    title = (reply.text or "").strip()
    await igrone_error(reply.delete)()
    if not title or title.lower() in CANCEL_WORDS:
        return await retry_on_flood(client.send_message)(chat_id, "❌ Post creation cancelled.")

    # Step 4 — genre
    reply = await _ask(
        client, chat_id, admin_id,
        "<b>🏷 Step 4/5 — Genre</b>\n\nSend the genre(s), comma separated.\n"
        "e.g. <code>Action, Fantasy, Drama</code>"
    )
    if reply is None:
        return
    genre_raw = (reply.text or "").strip()
    await igrone_error(reply.delete)()
    if not genre_raw or genre_raw.lower() in CANCEL_WORDS:
        return await retry_on_flood(client.send_message)(chat_id, "❌ Post creation cancelled.")
    genres = [g.strip() for g in genre_raw.split(",") if g.strip()]
    genre_txt = " ".join(f"#{g.replace(' ', '_')}" for g in genres)

    # Step 5 — description
    reply = await _ask(
        client, chat_id, admin_id,
        "<b>🗒 Step 5/5 — Description</b>\n\nSend the synopsis/description."
    )
    if reply is None:
        return
    description = (reply.text or reply.caption or "").strip()
    await igrone_error(reply.delete)()
    if not description or description.lower() in CANCEL_WORDS:
        return await retry_on_flood(client.send_message)(chat_id, "❌ Post creation cancelled.")

    post_id = _gen_post_id()
    _drafts[admin_id] = {
        "post_id": post_id,
        "title": title,
        "genre": genre_txt,
        "description": description,
        "poster": poster,
        "dump_channel": _norm_channel(dump_channel),
        "file_ids": file_ids,
    }

    caption = _build_caption(title, genre_txt, description)
    preview_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Read Now", callback_data="pmp_noop")],
        [
            InlineKeyboardButton("✅ Confirm & Publish", callback_data="pdraft_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="pdraft_cancel"),
        ],
    ])
    await retry_on_flood(client.send_photo)(
        chat_id, poster,
        caption="<b>🔎 Preview — this is exactly how it will look:</b>\n\n" + caption,
        reply_markup=preview_markup,
    )


@Bot.on_callback_query(filters.regex("^pdraft_") & filters.user(Vars.ADMINS))
async def draft_decision_cb(client, query):
    admin_id = query.from_user.id
    draft = _drafts.get(admin_id)
    if not draft:
        return await retry_on_flood(query.answer)("⚠️ No pending draft found. Run /newpost again.", show_alert=True)

    action = query.data.removeprefix("pdraft_")
    if action == "cancel":
        del _drafts[admin_id]
        await igrone_error(query.answer)("❌ Cancelled")
        return await igrone_error(query.message.delete)()

    post_channel = get_post_channel()
    if not post_channel:
        return await retry_on_flood(query.answer)(
            "❌ No Post Channel set. Set one via /postsettings first.", show_alert=True
        )

    caption = _build_caption(draft["title"], draft["genre"], draft["description"])
    button = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Read Now", url=f"https://t.me/{Bot.username}?start=get_{draft['post_id']}")
    ]])

    try:
        sent = await retry_on_flood(client.send_photo)(
            _norm_channel(post_channel), draft["poster"], caption=caption, reply_markup=button
        )
    except Exception as e:
        logger.exception(e)
        return await retry_on_flood(query.answer)(f"❌ Failed to publish: {e}", show_alert=True)

    save_post(draft["post_id"], {
        "title": draft["title"],
        "genre": draft["genre"],
        "description": draft["description"],
        "poster": draft["poster"],
        "dump_channel": draft["dump_channel"],
        "file_ids": draft["file_ids"],
        "post_channel": _norm_channel(post_channel),
        "post_msg_id": sent.id,
        "created_by": admin_id,
        "created_at": int(time.time()),
        "reads": 0,
    })
    del _drafts[admin_id]

    await igrone_error(query.answer)("✅ Published!")
    txt = f"✅ <b>Post published!</b>\n\n<b>ID:</b> <code>{draft['post_id']}</code>"
    if getattr(sent.chat, "username", None):
        txt += f"\n<b>Link:</b> https://t.me/{sent.chat.username}/{sent.id}"
    await igrone_error(query.message.edit_caption)(txt)


@Bot.on_callback_query(filters.regex("^pmp_noop$"))
async def noop_cb(client, query):
    await igrone_error(query.answer)("This is just a preview of the button 🙂")


# ---------------------------------------------------------------------------
# Manage existing posts (list / delete)
# ---------------------------------------------------------------------------

@Bot.on_callback_query(filters.regex("^pmp_manage") & filters.user(Vars.ADMINS))
async def manage_posts_cb(client, query):
    await igrone_error(query.answer)()
    try:
        page = int(query.data.split(":")[-1])
    except Exception:
        page = 1

    posts = all_posts()
    items = sorted(posts.items(), key=lambda kv: kv[1].get("created_at", 0), reverse=True)

    if not items:
        button = InlineKeyboardMarkup([[InlineKeyboardButton("⇦ Back", callback_data="pmpanel")]])
        return await retry_on_flood(query.edit_message_text)("📭 No posts yet.", reply_markup=button)

    per_page = 8
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    page_items = items[(page - 1) * per_page: page * per_page]

    button = []
    for post_id, data in page_items:
        title = data.get("title", post_id)[:26]
        reads = data.get("reads", 0)
        button.append([
            InlineKeyboardButton(f"📖 {title} ({reads})", url=f"https://t.me/{Bot.username}?start=get_{post_id}"),
            InlineKeyboardButton("🗑", callback_data=f"pmp_del_{post_id}"),
        ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"pmp_manage:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="pmp_noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"pmp_manage:{page + 1}"))
    button.append(nav)
    button.append([InlineKeyboardButton("⇦ Back", callback_data="pmpanel")])

    await retry_on_flood(query.edit_message_text)(
        f"<b>📋 Manage Posts</b> ({len(items)} total)\n"
        "<i>Number in brackets = how many times it's been delivered.</i>",
        reply_markup=InlineKeyboardMarkup(button),
    )


@Bot.on_callback_query(filters.regex("^pmp_del_") & filters.user(Vars.ADMINS))
async def delete_post_cb(client, query):
    post_id = query.data.removeprefix("pmp_del_")
    post = get_post(post_id)
    if not post:
        return await retry_on_flood(query.answer)("⚠️ Already deleted.", show_alert=True)

    if post.get("post_channel") and post.get("post_msg_id"):
        await igrone_error(client.delete_messages)(
            _norm_channel(post["post_channel"]), int(post["post_msg_id"])
        )

    delete_post(post_id)
    await retry_on_flood(query.answer)("🗑 Post deleted.", show_alert=True)

    query.data = "pmp_manage:1"
    await manage_posts_cb(client, query)


# ---------------------------------------------------------------------------
# Delivery — called from /start when the deep link is ?start=get_<post_id>
# ---------------------------------------------------------------------------

async def deliver_post(client, message, post_id):
    post = get_post(post_id)
    if not post:
        return await retry_on_flood(message.reply_text)(
            "❌ This link is invalid or has expired.", quote=True
        )

    sts = await retry_on_flood(message.reply_text)("<code>📦 Fetching your file(s)...</code>", quote=True)
    dump_channel = post.get("dump_channel")
    file_ids = post.get("file_ids", [])
    if not dump_channel or not file_ids:
        return await retry_on_flood(sts.edit_text)("❌ No files are linked to this post. Please contact the admin.")

    sent = 0
    for msg_id in file_ids:
        try:
            await retry_on_flood(client.copy_message)(
                message.chat.id, _norm_channel(dump_channel), int(msg_id)
            )
            sent += 1
            await asyncio.sleep(1)
        except Exception as e:
            logger.exception(f"Failed delivering post {post_id} file {msg_id}: {e}")

    if not sent:
        return await retry_on_flood(sts.edit_text)("❌ Couldn't fetch the file(s). Please contact the admin.")

    bump_post_reads(post_id)
    await retry_on_flood(sts.edit_text)(
        f"✅ Sent {sent} file(s) for <b>{post.get('title', 'this manga')}</b>. Enjoy reading! 📖"
    )

    if Vars.LOG_CHANNEL:
        await igrone_error(client.send_message)(
            Vars.LOG_CHANNEL,
            f"📖 Post <code>{post_id}</code> (<b>{post.get('title')}</b>) delivered to "
            f"<code>{message.from_user.id}</code> [{message.from_user.mention()}]"
        )
