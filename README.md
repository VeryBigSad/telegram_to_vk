# Telegram to VK
Redirect your telegram channel messages to your VK group automatically!

Supports editing on-the-fly & copies your photos/videos to the VK aswell.

![example of the forward functionality](/example.png)

## Setup
1. `git clone https://github.com/verybigsad/telegram_to_vk` 
2. Fill in the `.env` file with values

2 options from here:

### Via console:
```
pip install -r requirements.txt
python main.py
```

### Via Docker:
```
docker build --tag telegram_to_vk . 
docker run telegram_to_vk
```
