# Vsingerd
Vsingerd is a cross social platform reposter. It fetchs [Weibo](https://weibo.com/) updates of specific users and repost to other platforms.

The project is named [Vsinger](https://zh.moegirl.org.cn/%E4%B8%8A%E6%B5%B7%E7%A6%BE%E5%BF%B5%E4%BF%A1%E6%81%AF%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8#Vsinger), the Chinese [VOCALOID](https://zh.wikipedia.org/wiki/VOCALOID) project.

Supported platforms:
 - [x] Telegram
 - [ ] SMTP
 - [ ] [PushDeer](https://github.com/easychen/pushdeer)
 - [x] CSV Storage
 - [ ] MySQL Storage

## Installation
### Preparation
You need a Telegram bot, a Telegram chat (or channel) and a Weibo UIDs.
 1. To create Telegram bot, please contact [@BotFather](http://t.me/BotFather) (the official bot creator) on Telegram.
 2. You need create a channel on Telegram, and add the bot you created to the channel. You should also give permission of sending messages and photos to the bot.
 3. Get the chat ID of the channel. Send anything in the channel, and request chat ID with Telegram API:
    ```
    curl https://api.telegram.org/bot<token>/getUpdates
    ```
    where `<token>` is your bot token. You can see chat ID in JSON response.
 4. Get Weibo UIDs. Go to the Weibo profile page of who you want to subscribe, click _Followee_ and the URL will be show like `https://weibo.com/u/page/follow/<uid>?relate=fans`. Copy the `<uid>` part.

### Setup
Make sure **Python 3.8-3.10** is installed.

First clone the source code from repository:

```shell
git clone https://github.com/luotianyi-dev/vsingerd.git
```

Create an virtual environment and install dependencies:

```shell
cd vsingerd
python3 -m venv venv
source venv/bin/activate
cd src
pip3 install -r requirements.txt
```

Then create a folder for data storage:

```shell
mkdir data
```

Then you have 2 options to run it in schedule.

#### Using Crontab
Create a shell file and configurate with setting environment variables. Concat UIDs with `:` to subscribe multiple users.

For example, create the `vsingerd-cron.sh` in `/opt/vsingerd` and your cloned repository also located here.

```bash
#!/bin/bash
#                User 1     User 2     User 3
CONFIG_WEIBO_IDS=5146173015:3500223314:5146669192
CONFIG_TG_TOKEN=123456789:ExampleTelegramToken
CONFIG_TG_CHAT=-1001700507292
cd /opt/vsingerd/src
python3 vsingerd > vsingerd.log 2>&1
```

Add execute permission and edit crontab

```shell
chmod +x vsingerd-cron.sh
crontab -e
```

Add an entry

```
*/5 * * * * /opt/vsingerd/vsingerd-cron.sh
```

The `*/5 * * * *` means it will run every 5 minutes. You can generate the syntax with tools like [crontab guru](https://crontab.guru/).

#### Using Systemd
Edit `vsingerd.service` and `vsingerd.timer` edit them as you need. Read the previous section for configuration details.

Then enable the timer:

```shell
systemctl enable --now /opt/vsingerd/vsingerd.timer
systemctl enable --now /opt/vsingerd/vsingerd.service
```

You should do the initial run, or the timer won't work until you next reboot.

## License
MIT License
