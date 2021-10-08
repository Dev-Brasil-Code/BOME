import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Você precisará me fornecer um nome de usuário para silenciar ou responder a alguém para ser silenciado.")
        return ""

    if user_id == bot.id:
        message.reply_text("Eu não estou me silenciando!")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("Com medo de não conseguir impedir um administrador de falar!")

        elif member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
            message.reply_text("👍🏻 mudo! 🤐")
            return "<b>{}:</b>" \
                   "\n#MUTE" \
                   "\n<b>Admin:</b> {}" \
                   "\n<b>User:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))

        else:
            message.reply_text("Este usuário já está silenciado!")
    else:
        message.reply_text("Este usuário não está no chat!")

    return ""


@run_async
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Você precisará fornecer um nome de usuário para ativar o som ou responder a alguém para ativar o som.")
        return ""

    member = chat.get_member(int(user_id))

    if member.status != 'kicked' and member.status != 'left':
        if member.can_send_messages and member.can_send_media_messages \
                and member.can_send_other_messages and member.can_add_web_page_previews:
            message.reply_text("Este usuário já tem o direito de falar.")
        else:
            bot.restrict_chat_member(chat.id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)
            message.reply_text("Com som!")
            return "<b>{}:</b>" \
                   "\n#UNMUTE" \
                   "\n<b>Admin:</b> {}" \
                   "\n<b>User:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))
    else:
        message.reply_text("Este usuário nem mesmo está no chat, reativá-lo não o fará falar mais do que ele "
                           "ja fiz!")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
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

    if is_user_admin(chat, user_id, member):
        message.reply_text("Eu realmente gostaria de poder silenciar os administradores ...")
        return ""

    if user_id == bot.id:
        message.reply_text("Eu não vou MUDAR, você está louco?")
        return ""

    if not reason:
        message.reply_text("Você não especificou um tempo para silenciar este usuário!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP MUTED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>Razão:</b> {}".format(reason)

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, until_date=mutetime, can_send_messages=False)
            message.reply_text("Cale-se! 😠 Silenciado por {}!".format(time_val))
            return log
        else:
            message.reply_text("Este usuário já está silenciado.")

    except BadRequest as excp:
        if excp.message == "Mensagem de resposta não encontrada":
            # Do not reply
            message.reply_text("Cale-se! 😠 Silenciado por {}!".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR usuário de silenciamento %s no bate-papo %s (%s) devido a %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Bem, caramba, não posso silenciar esse usuário.")

    return ""


__help__ = """
*Admin only:*
 - /mute <user>: silencia um usuário. Também pode ser usado como uma resposta, silenciando o usuário respondido.
 - /tmute <user> x(m/h/d): silencia um usuário por x vezes. (via identificador ou resposta). m = minutes, h = hours, d = days.
 - /unmute <user>: ativa o som de um usuário. Também pode ser usado como uma resposta, silenciando o usuário respondido.
"""

__mod_name__ = "🔇 Mute 🔇"

MUTE_HANDLER = CommandHandler("mute", mute, pass_args=True, filters=Filters.group)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, pass_args=True, filters=Filters.group)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, pass_args=True, filters=Filters.group)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)
