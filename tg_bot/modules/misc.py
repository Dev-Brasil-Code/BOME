import html
import json
import random
from datetime import datetime
from typing import Optional, List

import requests
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.__main__ import STATS, USER_INFO
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters

RUN_STRINGS = (
    "Onde você pensa que está indo?",
    "Hã? O quê? Eles escaparam?",
    "ZZzzZZzz ... Hã? O quê? Oh, só eles de novo, deixa pra lá.",
    "Volte aqui!",
    "Não tão rápido...",
    "Cuidado com a parede!",
    "Não me deixe sozinho com eles !!",
    "Você corre, você morre.",
    "Brinca com você, estou em todo lugar",
    "Você vai se arrepender disso ...",
    "Você também poderia Experimente /kickme, Ouvi dizer que é divertido.",
    "Vá incomodar outra pessoa, ninguém aqui liga.",
    "Você pode correr, mas não pode se esconder.",
    "Isso é tudo que você tem?",
    "Estou atrás de você...",
    "Você tem companhia!",
    "Podemos fazer isso da maneira fácil ou da maneira mais difícil.",
    "Você simplesmente não entende, não é?",
    "Sim, é melhor você correr!",
    "Por favor, me lembre o quanto eu me importo?",
    "Eu correria mais rápido se fosse você.",
    "Esse é definitivamente o andróide que estamos procurando.",
    "Que as probabilidades estejam sempre a seu favor.",
    "Famous last words.",
    "And they disappeared forever, never to be seen again.",
    "\"Oh, look at me! I'm so cool, I can run from a bot!\" - this person",
    "Yeah yeah, just tap /kickme already.",
    "Here, take this ring and head to Mordor while you're at it.",
    "Legend has it, they're still running...",
    "Unlike Harry Potter, your parents can't protect you from me.",
    "Fear leads to anger. Anger leads to hate. Hate leads to suffering. If you keep running in fear, you might "
    "be the next Vader.",
    "Multiple calculations later, I have decided my interest in your shenanigans is exactly 0.",
    "Legend has it, they're still running.",
    "Keep it up, not sure we want you here anyway.",
    "You're a wiza- Oh. Wait. You're not Harry, keep moving.",
    "NO RUNNING IN THE HALLWAYS!",
    "Hasta la vista, baby.",
    "Who let the dogs out?",
    "It's funny, because no one cares.",
    "Ah, what a waste. I liked that one.",
    "Frankly, my dear, I don't give a damn.",
    "My milkshake brings all the boys to yard... So run faster!",
    "You can't HANDLE the truth!",
    "A long time ago, in a galaxy far far away... Someone would've cared about that. Not anymore though.",
    "Hey, look at them! They're running from the inevitable banhammer... Cute.",
    "Han shot first. So will I.",
    "What are you running after, a white rabbit?",
    "As The Doctor would say... RUN!",
)

SLAP_TEMPLATES = (
    "{user1} {hits} {user2} com um {item}.",
    "{user1} {hits} {user2} na cara com um {item}.",
    "{user1} {hits} {user2} around a bit with a {item}.",
    "{user1} {throws} a {item} at {user2}.",
    "{user1} grabs a {item} and {throws} it at {user2}'s face.",
    "{user1} launches a {item} in {user2}'s general direction.",
    "{user1} starts slapping {user2} silly with a {item}.",
    "{user1} pins {user2} down and repeatedly {hits} them with a {item}.",
    "{user1} grabs up a {item} and {hits} {user2} with it.",
    "{user1} ties {user2} to a chair and {throws} a {item} at them.",
    "{user1} gave a friendly push to help {user2} learn to swim in lava."
)

ITEMS = (
    "cast iron skillet",
    "large trout",
    "baseball bat",
    "cricket bat",
    "wooden cane",
    "nail",
    "printer",
    "shovel",
    "CRT monitor",
    "physics textbook",
    "toaster",
    "portrait of Richard Stallman",
    "television",
    "five ton truck",
    "roll of duct tape",
    "book",
    "laptop",
    "old television",
    "sack of rocks",
    "rainbow trout",
    "rubber chicken",
    "spiked bat",
    "fire extinguisher",
    "heavy rock",
    "chunk of dirt",
    "beehive",
    "piece of rotten meat",
    "bear",
    "ton of bricks",
)

THROW = (
    "throws",
    "flings",
    "chucks",
    "hurls",
)

HIT = (
    "hits",
    "whacks",
    "slaps",
    "smacks",
    "bashes",
)

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"


@run_async
def runs(bot: Bot, update: Update):
    update.effective_message.reply_text(random.choice(RUN_STRINGS))


@run_async
def slap(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(slapped_user.first_name,
                                                   slapped_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)


@run_async
def get_bot_ip(bot: Bot, update: Update):
    """ Envia o endereço IP do bot, para poder fazer o ssh se necessário.
        SÓ PROPRIETÁRIO.
    """
    res = requests.get("http://ipinfo.io/ip")
    update.message.reply_text(res.text)


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            update.effective_message.reply_text(
                "O remetente original, {}, tem um ID de `{}`.\nO despachante, {}, tem um ID de `{}`.".format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = bot.get_chat(user_id)
            update.effective_message.reply_text("{}'s id is `{}`.".format(escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            update.effective_message.reply_text("Sua id é `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            update.effective_message.reply_text("O id deste grupo é `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not msg.reply_to_message and not args:
        user = msg.from_user

    elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        msg.reply_text("Não consigo extrair um usuário deste.")
        return

    else:
        return

    text = "<b>User info</b>:" \
           "\nID: <code>{}</code>" \
           "\nPrimeiro nome: {}".format(user.id, html.escape(user.first_name))

    if user.last_name:
        text += "\nÚltimo nome: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\nUsername: @{}".format(html.escape(user.username))

    text += "\nPermanente user link: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\nEsta pessoa é minha dona - I nunca faria nada contra eles!"
    else:
        if user.id in SUDO_USERS:
            text += "\nEsta pessoa é um dos meus usuários de sudo! " \
                    "Quase tão poderoso quanto meu dono - então observe."
        else:
            if user.id in SUPPORT_USERS:
                text += "\nEsta pessoa é um dos meus usuários de suporte! " \
                        "Não é bem um usuário sudo, mas ainda pode expulsá-lo do mapa."

            if user.id in WHITELIST_USERS:
                text += "\nEsta pessoa foi colocada na lista de permissões! " \
                        "Isso significa que não tenho permissão para bani-los / expulsá-los."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def get_time(bot: Bot, update: Update, args: List[str]):
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("É sempre hora de martelar para mim!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location))

    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            lat = loc['results'][0]['geometry']['location']['lat']
            long = loc['results'][0]['geometry']['location']['lng']

            country = None
            city = None

            address_parts = loc['results'][0]['address_components']
            for part in address_parts:
                if 'country' in part['types']:
                    country = part.get('long_name')
                if 'administrative_area_level_1' in part['types'] and not city:
                    city = part.get('long_name')
                if 'locality' in part['types']:
                    city = part.get('long_name')

            if city and country:
                location = "{}, {}".format(city, country)
            elif country:
                location = country

            timenow = int(datetime.utcnow().timestamp())
            res = requests.get(GMAPS_TIME, params=dict(location="{},{}".format(lat, long), timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp + offset).strftime("%H:%M:%S on %A %d %B")
                update.message.reply_text("It's {} in {}".format(time_there, location))


@run_async
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    message.delete()


@run_async
def gdpr(bot: Bot, update: Update):
    update.effective_message.reply_text("Exclusão de dados identificáveis...")
    for mod in GDPR:
        mod.__gdpr__(update.effective_user.id)

    update.effective_message.reply_text("Seus dados pessoais foram excluídos.\n\nObserve que isso não cancelará o banimento "
                                        "você de qualquer bate-papo, já que são dados de telegrama, não dados de Termux School. "
                                        "Inundações, avisos e gbans também são preservados, a partir de "
                                        "[this](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/), "
                                        "que afirma claramente que o direito de apagamento não se aplica "
                                        "\"para o desempenho de uma tarefa realizada no interesse público\", como é "
                                        "o caso para os dados acima mencionados.",
                                        parse_mode=ParseMode.MARKDOWN)


MARKDOWN_HELP = """
Markdown é uma ferramenta de formatação muito poderosa suportada por telegrama. {} has some enhancements, to make sure that \
as mensagens salvas são analisadas corretamente e permitem que você crie botões.

- <code>_italic_</code>: envolver o texto com '_' irá produzir texto em itálico
- <code>*bold*</code>: envolver o texto com '*' irá produzir texto em negrito
- <code>`code`</code>: envolver o texto com '`' irá produzir texto monoespaçado, também conhecido como 'código'
- <code>[sometext](someURL)</code>: isso criará um link - a mensagem apenas mostrará <code>algum texto</code>, \
e tocar nele abrirá a página em <code>algum URL</code>.
POR EXEMPLO: <code>[test](example.com)</code>

- <code>[buttontext](buttonurl:suaurl)</code>: este é um aprimoramento especial para permitir que os usuários tenham telegrama \
botões em sua marcação. <code>buttontext</code> será o que é exibido no botão, e <code>suaurl</code> \
será o url que será aberto.
POR EXEMPLO: <code>[Isto é um botão](buttonurl:example.com)</code>

Se você quiser vários botões na mesma linha, use: same, como tal:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
Isso criará dois botões em uma única linha, em vez de um botão por linha.

Lembre-se de que sua mensagem <b>MUST</b> contém algum texto que não seja apenas um botão!
""".format(dispatcher.bot.first_name)


@run_async
def markdown_help(bot: Bot, update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("Tente encaminhar a seguinte mensagem para mim e você verá!")
    update.effective_message.reply_text("/save test Este é um teste de remarcação. _italics_, *bold*, `code`, "
                                        "[URL](example.com) [button](buttonurl:github.com) "
                                        "[button2](buttonurl://google.com:same)")


@run_async
def stats(bot: Bot, update: Update):
    update.effective_message.reply_text("Current stats:\n" + "\n".join([mod.__stats__() for mod in STATS]))

@run_async
def stickerid(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        update.effective_message.reply_text("Olá " +
                                            "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)
                                            + ", O adesivo, se você estiver respondendo, é :\n```" + 
                                            escape_markdown(msg.reply_to_message.sticker.file_id) + "```",
                                            parse_mode=ParseMode.MARKDOWN)
    else:
        update.effective_message.reply_text("Olá " + "[{}](tg://user?id={})".format(msg.from_user.first_name,
                                            msg.from_user.id) + ", Responda à mensagem do adesivo para obter o adesivo de identificação",
                                            parse_mode=ParseMode.MARKDOWN)
@run_async
def getsticker(bot: Bot, update: Update):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        bot.sendChatAction(chat_id, "typing")
        update.effective_message.reply_text("Hello " + "[{}](tg://user?id={})".format(msg.from_user.first_name,
                                            msg.from_user.id) + ", Por favor, verifique o arquivo que você solicitou abaixo."
                                            "\nUse este recurso com sabedoria!",
                                            parse_mode=ParseMode.MARKDOWN)
        bot.sendChatAction(chat_id, "upload_document")
        file_id = msg.reply_to_message.sticker.file_id
        newFile = bot.get_file(file_id)
        newFile.download('sticker.png')
        bot.sendDocument(chat_id, document=open('sticker.png', 'rb'))
        bot.sendChatAction(chat_id, "upload_photo")
        bot.send_photo(chat_id, photo=open('sticker.png', 'rb'))
        
    else:
        bot.sendChatAction(chat_id, "typing")
        update.effective_message.reply_text("Hello " + "[{}](tg://user?id={})".format(msg.from_user.first_name,
                                            msg.from_user.id) + ", Responda à mensagem do adesivo para obter a imagem do adesivo",
                                            parse_mode=ParseMode.MARKDOWN)

# /ip is for private use
__help__ = """
 - /id: obtenha o ID do grupo atual. Se usado para responder a uma mensagem, obtém a id desse usuário.
 - /runs: responda uma string aleatória de uma série de respostas.
 - /slap: dê um tapa em um usuário ou leve um tapa se não for uma resposta.
 - /time <Lugar, colocar>: dá a hora local em um determinado lugar.
 - /info: obter informações sobre um usuário.
 - /gdpr: apaga suas informações do banco de dados do bot. Apenas bate-papos privados.
 - /markdownhelp: resumo rápido de como o markdown funciona no telegrama - só pode ser chamado em chats privados.
 - /stickerid: responder a um adesivo e obter a identificação dele.
 - /getsticker: responda a um adesivo e obtenha esse adesivo como .png e imagem. 
"""

__mod_name__ = "🗞️ Diversos 🗞️"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))

TIME_HANDLER = CommandHandler("time", get_time, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)

ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)

STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)
GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=Filters.private)

STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)


dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(IP_HANDLER)
dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(GDPR_HANDLER)
dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
