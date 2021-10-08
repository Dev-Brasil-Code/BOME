import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "O usuário é um administrador do chat",
    "Bate-papo não encontrado",
    "Direitos insuficientes para restringir / não restringir membro do bate-papo",
    "User_not_participant",
    "Peer_id_invalid",
    "O chat em grupo foi desativado",
    "Precisa ser o convite de um usuário para expulsá-lo de um grupo básico",
    "Chat_admin_required",
    "Apenas o criador de um grupo básico pode expulsar os administradores do grupo",
    "Channel_private",
    "Not in the chat"
}

UNGBAN_ERRORS = {
    "O usuário é um administrador do chat",
    "Bate-papo não encontrado",
    "Direitos insuficientes para restringir / não restringir membro do bate-papo",
    "User_not_participant",
    "O método está disponível para supergrupos e chats de canal apenas",
    "Não está no chat",
    "Channel_private",
    "Chat_admin_required",
}


@run_async
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Você não parece estar se referindo a um usuário.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Eu espio, com meu olhinho ... uma guerra de usuários de sudo! Por que vocês estão se virando??")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH alguém está tentando gban um usuário de suporte! *pega pipoca*")
        return

    if user_id == bot.id:
        message.reply_text("-_- Tão engraçado, vamos gban por que eu não faço? Boa tentativa.")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Isso não é um usuário!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text("Este usuário já foi banido; Eu mudaria o motivo, mas você não me deu um...")
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("Este usuário já foi banido pelo seguinte motivo:\n"
                               "<code>{}</code>\n"
                               "Eu fui e atualizei com seu novo motivo!".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)
        else:
            message.reply_text("Este usuário já foi banido, mas não tinha um motivo definido; Eu fui e atualizei!")

        return

    message.reply_text("⚡️ * Snaps Banr* ⚡️")

    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>Global Ban</b>" \
                 "\n#GBAN" \
                 "\n<b>Status:</b> <code>Enforcing</code>" \
                 "\n<b>Sudo Admin:</b> {}" \
                 "\n<b>User:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>" \
                 "\n<b>Razão:</b> {}".format(mention_html(banner.id, banner.first_name),
                                              mention_html(user_chat.id, user_chat.first_name), 
                                                           user_chat.id, reason or "Nenhuma razão dada"), 
                html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("Não foi possível gban devido a: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Não foi possível gban devido a: {}".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, 
                  "{} foi banido com sucesso!".format(mention_html(user_chat.id, user_chat.first_name)),
                html=True)
    message.reply_text("A pessoa foi banida.")


@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Você não parece estar se referindo a um usuário.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Isso não é um usuário!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Este usuário não foi banido!")
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("Eu perdôo {}, globalmente com uma segunda chance.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>Regressão da proibição global</b>" \
                 "\n#UNGBAN" \
                 "\n<b>Status:</b> <code>Ceased</code>" \
                 "\n<b>Sudo Admin:</b> {}" \
                 "\n<b>User:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>".format(mention_html(banner.id, banner.first_name),
                                                       mention_html(user_chat.id, user_chat.first_name), 
                                                                    user_chat.id),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Verifique se este grupo desabilitou gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("Não foi possível cancelar o gban devido a: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Não foi possível cancelar o gban devido a: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, 
                  "{} foi perdoado do gban!".format(mention_html(user_chat.id, 
                                                                         user_chat.first_name)),
                  html=True)

    message.reply_text("Esta pessoa foi anulada e o perdão foi concedido!")


@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("Não há nenhum usuário gbanned! Você é mais gentil do que eu esperava ...")
        return

    banfile = 'Dane-se esses caras.\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Razão: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Aqui está a lista de usuários banidos atualmente.")


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("Esta é uma pessoa má, eles não deveriam estar aqui!")


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Eu habilitei gbans neste grupo. Isso ajudará a protegê-lo "
                                                "de spammers, personagens desagradáveis ​​e os maiores trolls.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Desativei gbans neste grupo. GBans não afetará seus usuários "
                                                "mais. Você estará menos protegido de quaisquer trolls e spammers "
                                                "no entanto!")
    else:
        update.effective_message.reply_text("Dê-me alguns argumentos para escolher um cenário! on/off, yes/no!\n\n"
                                            "Sua configuração atual é: {}\n"
                                            "Quando True, qualquer gbans que acontecer também acontecerá em seu grupo. "
                                            "Quando False, eles não vão, deixando você à possível mercê de "
                                            "spammers.".format(sql.does_chat_gban(update.effective_chat.id)))


def __stats__():
    return "{} usuários gbanned.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "Banido globalmente: <b>{}</b>"
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += "\nRazão: {}".format(html.escape(user.reason))
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Este bate-papo está impondo *gbans*: `{}`.".format(sql.does_chat_gban(chat_id))


__help__ = """
*Admin apenas:*
 - /gbanstat <on/off/yes/no>: Desativará o efeito de banimentos globais em seu grupo ou retornará suas configurações atuais.

Gbans, também conhecidos como banimentos globais, são usados ​​pelos proprietários de bot para banir spammers em todos os grupos. Isso ajuda a proteger \
você e seus grupos removendo inundadores de spam o mais rápido possível. Eles podem ser desativados para o seu grupo ligando para \
/gbanstat
"""

__mod_name__ = "🚫 Proibição Global 🚫"

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CommandHandler("gbanlist", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_STATUS = CommandHandler("gbanstat", gbanstat, pass_args=True, filters=Filters.group)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
