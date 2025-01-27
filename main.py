import asyncio
import logging
import os
import random
from typing import List

from aiogram import Bot, Dispatcher, Router, types
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from requests.exceptions import ConnectionError
from vk_api import VkApi, upload

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Config
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
TELEGRAM_CHANNEL_USERNAME = os.getenv("TELEGRAM_CHANNEL_USERNAME")
VK_API_TOKEN = os.getenv("VK_API_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")

# VK initialization
vk_session = VkApi(token=VK_API_TOKEN, api_version="5.131")
vk = vk_session.get_api()
uploader = upload.VkUpload(vk)

# Aiogram initialization
bot = Bot(token=TELEGRAM_API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


def add_entry(message_id, post_id):
    # function for the editing sync to work
    # returns post_id from message_id
    with open("data.txt", "a") as f:
        f.write(f"{message_id}:{post_id}\n")


def get_entry(message_id) -> int:
    # function for the editing sync to work
    # returns post_id from message_id
    with open("data.txt", "r") as f:
        for line in f.readlines():
            if int(line.split(":")[0]) == message_id:
                return int(line.split(":")[1])
    raise KeyError(f"{message_id} is not in the file!")


def create_vk_post(text: str, message_id, photo_list=None, video_list=None):
    # creates a vk publication with your text, photo/video list and references the original telegram message
    photos, videos = [], []
    if photo_list:
        while True:
            try:
                photos = uploader.photo_wall(photos=photo_list, group_id=VK_GROUP_ID)
                break
            except ConnectionError:
                pass
        for i in photo_list:
            os.remove(i)
    if video_list:
        while True:
            try:
                videos = [
                    uploader.video(video_file=i, group_id=int(VK_GROUP_ID), album_id=0)
                    for i in video_list
                ]
                break
            except ConnectionError:
                pass
        for i in video_list:
            os.remove(i)
    attachments = [f"photo{i['owner_id']}_{i['id']}" for i in photos]
    attachments += [f"video{i['owner_id']}_{i['video_id']}" for i in videos]

    post = vk.wall.post(
        message=text,
        from_group=1,
        attachments=attachments,
        owner_id=f"-{VK_GROUP_ID}",
        copyright=f"https://{TELEGRAM_CHANNEL_USERNAME}.t.me/{message_id}",
    )

    add_entry(message_id, post["post_id"])


def edit_vk_post(post_id, new_text, message_id):
    # getting data from the original post
    old_post = vk.wall.get_by_id(posts=f"-{VK_GROUP_ID}_{post_id}")[0]
    if old_post.get("attachments"):
        attachments = [
            f"{attachment['type']}{attachment[attachment['type']]['owner_id']}_{attachment[attachment['type']]['id']}"
            for attachment in old_post["attachments"]
        ]
    else:
        attachments = []
    # edit it
    vk.wall.edit(
        message=new_text,
        post_id=post_id,
        from_group=1,
        owner_id=f"-{VK_GROUP_ID}",
        copyright=f"https://{TELEGRAM_CHANNEL_USERNAME}.t.me/{message_id}",
        attachments=attachments,
    )


@router.channel_post()
async def handle_album(message: types.Message, album: List[types.Message] = None):
    # Check if message is from monitored channel
    if message.chat.username != TELEGRAM_CHANNEL_USERNAME:
        logging.info(
            "someone sent a message from a chat that is not the one that I monitor"
        )
        return

    # Handle media group
    if album:
        random_number = random.randint(1000000, 9999999)
        c = 0

        photo_list = []
        video_list = []
        text = None

        for msg in album:
            if text is None and msg.caption is not None:
                text = msg.caption
            if msg.photo:
                path = f"./files/photo_{random_number}_{c}.jpg"
                await bot.download(msg.photo[-1].file_id, path)
                photo_list.append(path)
            elif msg.video:
                path = f"./files/video_{random_number}_{c}.mp4"
                await bot.download(msg.video.file_id, path)
                video_list.append(path)
            c += 1

        create_vk_post(
            text,
            message_id=message.message_id,
            photo_list=photo_list,
            video_list=video_list,
        )
        return

    # Handle single photo/video
    if message.photo or message.video:
        text = message.caption
        random_number = random.randint(1000000, 9999999)

        if message.photo:
            path = f"./files/photo_{random_number}.jpg"
            await bot.download(message.photo[-1].file_id, path)
            create_vk_post(
                text=text or "", message_id=message.message_id, photo_list=[path]
            )
        elif message.video:
            path = f"./files/video_{random_number}.mp4"
            await bot.download(message.video.file_id, path)
            create_vk_post(
                text=text or "", message_id=message.message_id, video_list=[path]
            )
        return

    # Handle text-only messages
    if message.text:
        create_vk_post(message.text, message_id=message.message_id)


@router.edited_channel_post()
async def message_edited_handler(message: types.Message):
    if message.chat.username != TELEGRAM_CHANNEL_USERNAME:
        logging.info(
            "someone sent a message from a chat that is not the one that I monitor"
        )
        return

    try:
        post_id = get_entry(message.message_id)
    except KeyError:
        logging.error(
            f"entry of post associated with message_id {message.message_id} is not found."
            f" aborting editing sync"
        )
        return

    text = message.text
    if message.text is None and message.caption is not None:
        text = message.caption
    elif message.text is None and message.caption is None:
        text = ""

    edit_vk_post(post_id=post_id, new_text=text, message_id=message.message_id)
    print("edited")


async def main():
    # if files dir does not exist, create it
    if not os.path.exists("./files"):
        os.makedirs("./files")
    # Start bot
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
