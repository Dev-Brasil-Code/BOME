import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery

from tg_bot import dispatcher, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.helper_funcs.filters import CustomFilters

RBAN_ERRORS = {
    "O usuário é um administrador do chat",
    "Bate-papo não encontrado",
    "Direitos insuficientes para restringir / não restringir membro do bate-papo",
    "User_not_participant",
    "Peer_id_invalid",
    "O chat em grupo foi desativado",
    "Precisa ser o convite de um usuário para expulsá-lo de um grupo básico",
    "Chat_admin_required",
    "Apenas o criador de um grupo básico pode expulsar os administradores do grupo",
    "Channel_privado",
    "Não está no chat"
}

RUNBAN_ERRORS = {
    "O usuário é um administrador do chat",
    "Bate-papo não encontrado",
    "Direitos insuficientes para restringir / não restringir membro do bate-papo",
    "User do participante nao encontrado",
    "Peer_id_invalid",
    "O chat em grupo foi desativado",
    "Precisa ser o convite de um usuário para expulsá-lo de um grupo básico",
    "Chat Admin",
    "Apenas o criador de um grupo básico pode expulsar os administradores do grupo",
    "Channel_private",
    "Não está no chat"
}



@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Você não parece estar se referindo a um usuário.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Usuário não encontrado":
            message.reply_text("Não consigo encontrar este usuário")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Eu realmente gostaria de poder banir administradores...")
        return ""

    if user_id == bot.id:
        message.reply_text("Eu não vou me PROIBIR, você está louco?")
        return ""

    log = "<b>{}:</b>" \
          "\n#BANIDO" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>Razão:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        keyboard = []
        reply = "{} Banido!".format(mention_html(member.user.id, member.user.first_name))
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Mensagem de resposta não encontrada":
            # Do not reply
            message.reply_text('Banido!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banindo usuário %s no bate-papo %s (%s) devido a %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Bem, caramba, não posso banir esse usuário.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Você não parece estar se referindo a um usuário.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Usuário não encontrado":
            message.reply_text("Não consigo encontrar este usuário")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Eu realmente gostaria de banir administradores...")
        return ""

    if user_id == bot.id:
        message.reply_text("Eu não vou me PROIBIR, você está louco?")
        return ""

    if not reason:
        message.reply_text("Você não especificou um horário para banir este usuário por!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>Razão:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Banido! O usuário será banido por {}.".format(time_val))
        return log

    except BadRequest as excp:
        if excp.message == "Mensagem de resposta não encontrada":
            # Do not reply
            message.reply_text("Banido! O usuário será banido por {}.".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banindo usuário %s no bate-papo %s (%s) devido a %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Bem, caramba, não posso banir esse usuário.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Usuário não encontrado":
            message.reply_text("Não consigo encontrar este usuário")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Eu realmente gostaria de poder chutar administradores...")
        return ""

    if user_id == bot.id:
        message.reply_text("Simhh eu não vou fazer isso")
        return ""

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Chutado!")
        log = "<b>{}:</b>" \
              "\n#Chutado" \
              "\n<b>Admin:</b> {}" \
              "\n<b>User:</b> {}".format(html.escape(chat.title),
                                         mention_html(user.id, user.first_name),
                                         mention_html(member.user.id, member.user.first_name))
        if reason:
            log += "\n<b>Razão:</b> {}".format(reason)

        return log

    else:
        message.reply_text("Bem, caramba, eu não posso chutar esse usuário.")

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Eu gostaria de poder ... mas você é um administrador.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("Sem problemas.")
    else:
        update.effective_message.reply_text("Huh? Não posso :/")


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Usuário não encontrado":
            message.reply_text("Não consigo encontrar este usuário")
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Como eu me desanharia se não estivesse aqui ...?")
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("Por que você está tentando cancelar o banimento de alguém que já está no chat?")
        return ""

    chat.unban_member(user_id)
    message.reply_text("Sim, este usuário pode entrar!")

    log = "<b>{}:</b>" \
          "\n#NÃO BANIFICADO" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>Razão:</b> {}".format(reason)

    return log


@run_async
@bot_admin
def rban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Você não parece estar se referindo a um chat / usuário.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Você não parece estar se referindo a um usuário.")
        return
    elif not chat_id:
        message.reply_text("Você não parece estar se referindo a um bate-papo.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Bate-papo não encontrado":
            message.reply_text("Bate-papo não encontrado! Certifique-se de inserir um ID de bate-papo válido e eu faço parte desse bate-papo.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Me desculpe, mas isso é um chat privado!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Eu não posso restringir as pessoas lá! Certifique-se de que sou administrador e posso banir usuários.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Usuário não encontrado":
            message.reply_text("Não consigo encontrar este usuário")
            return
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Eu realmente gostaria de poder banir administradores...")
        return

    if user_id == bot.id:
        message.reply_text("Eu não vou me PROIBIR, você está louco?")
        return

    try:
        chat.kick_member(user_id)
        message.reply_text("Banido!")
    except BadRequest as excp:
        if excp.message == "Mensagem de resposta não encontrada":
            # Do not reply
            message.reply_text('Banido!', quote=False)
        elif excp.message in RBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banindo usuário %s no bate-papo %s (%s) devido a %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Bem, caramba, eu não posso banir esse usuário.")

@run_async
@bot_admin
def runban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Você não parece estar se referindo a um chat / usuário.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Você não parece estar se referindo a um usuário.")
        return
    elif not chat_id:
        message.reply_text("Você não parece estar se referindo a um bate-papo.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Bate-papo não encontrado":
            message.reply_text("Bate-papo não encontrado! Certifique-se de inserir um ID de bate-papo válido e eu faço parte desse bate-papo.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Lamento, mas é um chat privado!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Eu não posso restringir as pessoas lá! Certifique-se de que sou administrador e posso cancelar o banimento de usuários.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Usuário não encontrado":
            message.reply_text("Não consigo encontrar este usuário lá")
            return
        else:
            raise
            
    if is_user_in_chat(chat, user_id):
        message.reply_text("Por que você está tentando remover o banimento remotamente de alguém que já está nesse chat?")
        return

    if user_id == bot.id:
        message.reply_text("Eu não vou UNBAN, sou um administrador lá!")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("Sim, este usuário pode entrar nesse chat!")
    except BadRequest as excp:
        if excp.message == "Mensagem de resposta não encontrada":
            # Do not reply
            message.reply_text('Não banido!', quote=False)
        elif excp.message in RUNBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR desbanindo usuário %s no bate-papo %s (%s) devido a %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Bem, caramba, não posso cancelar o banimento desse usuário.")


__help__ = """
 - /kickme: chuta o usuário que emitiu o comando

*Admin only:*
 - /ban <userhandle>: proíbe um usuário. (via identificador ou resposta)
 - /tban <userhandle> x(m/h/d): bane um usuário por x Tempo. (via identificador ou resposta). m = minutes, h = hours, d = days.
 - /unban <userhandle>: desfaz o usuário. (via identificador ou resposta)
 - /kick <userhandle>: chuta um usuário, (via identificador ou resposta)
"""

__mod_name__ = "🚫 Ban 🚫"

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True, filters=Filters.group)
KICK_HANDLER = CommandHandler("kick", kick, pass_args=True, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)
RBAN_HANDLER = CommandHandler("rban", rban, pass_args=True, filters=CustomFilters.sudo_filter)
RUNBAN_HANDLER = CommandHandler("runban", runban, pass_args=True, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(RBAN_HANDLER)
dispatcher.add_handler(RUNBAN_HANDLER)
