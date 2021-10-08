import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin, can_delete
from tg_bot.modules.log_channel import loggable


@run_async
@user_admin
@loggable
def purge(bot: Bot, update: Update, args: List[str]) -> str:
    msg = update.effective_message  # type: Optional[Message]
    if msg.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, bot.id):
            message_id = msg.reply_to_message.message_id
            if args and args[0].isdigit():
                delete_to = message_id + int(args[0])
            else:
                delete_to = msg.message_id - 1
            for m_id in range(delete_to, message_id - 1, -1):  # Reverse iteration over message ids
                try:
                    bot.deleteMessage(chat.id, m_id)
                except BadRequest as err:
                    if err.message == "A mensagem não pode ser excluída":
                        bot.send_message(chat.id, "Não é possível excluir todas as mensagens. As mensagens podem ser muito antigas, eu posso "
                                                  "não tem direitos de exclusão ou pode não ser um supergrupo.")

                    elif err.message != "Mensagem para deletar não encontrada":
                        LOGGER.exception("Erro ao limpar mensagens de bate-papo.")

            try:
                msg.delete()
            except BadRequest as err:
                if err.message == "A mensagem não pode ser excluída":
                    bot.send_message(chat.id, "Não é possível excluir todas as mensagens. As mensagens podem ser muito antigas, eu posso "
                                              "não tem direitos de exclusão ou pode não ser um supergrupo.")

                elif err.message != "Mensagem para deletar não encontrada":
                    LOGGER.exception("Erro ao limpar mensagens de bate-papo.")

            return "<b>{}:</b>" \
                   "\n#PURGE" \
                   "\n<b>Admin:</b> {}" \
                   "\nPurged <code>{}</code> messages.".format(html.escape(chat.title),
                                                               mention_html(user.id, user.first_name),
                                                               delete_to - message_id)

    else:
        msg.reply_text("Responda a uma mensagem para selecionar de onde começar a purga.")

    return ""


@run_async
@user_admin
@loggable
def del_message(bot: Bot, update: Update) -> str:
    if update.effective_message.reply_to_message:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        if can_delete(chat, bot.id):
            update.effective_message.reply_to_message.delete()
            update.effective_message.delete()
            return "<b>{}:</b>" \
                   "\n#DEL" \
                   "\n<b>Admin:</b> {}" \
                   "\nMessage deleted.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))
    else:
        update.effective_message.reply_text("Whadya want to delete?")

    return ""


__help__ = """
*Admin only:*
 - /del: apaga a mensagem que você respondeu
 - /purge: exclui todas as mensagens entre esta e a mensagem respondida.
 - /purge <inteiro X>: apaga a mensagem respondida e as X mensagens a seguir.
"""

__mod_name__ = "✂️ Purgações ✂️"

DELETE_HANDLER = CommandHandler("del", del_message, filters=Filters.group)
PURGE_HANDLER = CommandHandler("purge", purge, filters=Filters.group, pass_args=True)

dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PURGE_HANDLER)
