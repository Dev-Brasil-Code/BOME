from functools import wraps
from typing import Optional

from tg_bot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Bot, Update, ParseMode, Message, Chat
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, run_async
    from telegram.utils.helpers import escape_markdown

    from tg_bot import dispatcher, LOGGER
    from tg_bot.modules.helper_funcs.chat_status import user_admin
    from tg_bot.modules.sql import log_channel_sql as sql


    def loggable(func):
        @wraps(func)
        def log_action(bot: Bot, update: Update, *args, **kwargs):
            result = func(bot, update, *args, **kwargs)
            chat = update.effective_chat  # type: Optional[Chat]
            message = update.effective_message  # type: Optional[Message]
            if result:
                if chat.type == chat.SUPERGROUP and chat.username:
                    result += "\n<b>Link:</b> " \
                              "<a href=\"http://telegram.me/{}/{}\">Clique aqui</a>".format(chat.username,
                                                                                           message.message_id)
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    send_log(bot, log_chat, chat.id, result)
            elif result == "":
                pass
            else:
                LOGGER.warning("%s foi definido como registrável, mas não tinha declaração de retorno.", func)

            return result

        return log_action


    def send_log(bot: Bot, log_chat_id: str, orig_chat_id: str, result: str):
        try:
            bot.send_message(log_chat_id, result, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            if excp.message == "Chat not found":
                bot.send_message(orig_chat_id, "Este canal de registro foi excluído - desconfigurando.")
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("Could not parse")

                bot.send_message(log_chat_id, result + "\n\nA formatação foi desativada devido a um erro inesperado.")


    @run_async
    @user_admin
    def logging(bot: Bot, update: Update):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            message.reply_text(
                "Este grupo tem todos os seus logs enviados para: {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                         log_channel),
                parse_mode=ParseMode.MARKDOWN)

        else:
            message.reply_text("Nenhum canal de registro foi definido para este grupo!")


    @run_async
    @user_admin
    def setlog(bot: Bot, update: Update):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == chat.CHANNEL:
            message.reply_text("Agora, encaminhe o /setlog para o grupo ao qual você deseja vincular este canal!")

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Mensagem para deletar não encontrada":
                    pass
                else:
                    LOGGER.exception("Erro ao excluir mensagem no canal de registro. Deve funcionar de qualquer maneira.")

            try:
                bot.send_message(message.forward_from_chat.id,
                                 "Este canal foi definido como o canal de registro para {}.".format(
                                     chat.title or chat.first_name))
            except Unauthorized as excp:
                if excp.message == "Proibido: o bot não é membro do chat do canal":
                    bot.send_message(chat.id, "Canal de registro configurado com sucesso!")
                else:
                    LOGGER.exception("ERROR na configuração do canal de registro.")

            bot.send_message(chat.id, "Canal de registro configurado com sucesso!")

        else:
            message.reply_text("As etapas para definir um canal de registro são:\n"
                               " - adicionar bot ao canal desejado\n"
                               " - mandar /setlog para o canal\n"
                               " - encaminhar o /setlog para o grupo\n")


    @run_async
    @user_admin
    def unsetlog(bot: Bot, update: Update):
        message = update.effective_message  # type: Optional[Message]
        chat = update.effective_chat  # type: Optional[Chat]

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(log_channel, "O canal foi desvinculado de {}".format(chat.title))
            message.reply_text("O canal de registro foi desarmado.")

        else:
            message.reply_text("Nenhum canal de registro foi definido ainda!")


    def __stats__():
        return "{} conjunto de canais de registro.".format(sql.num_logchannels())


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return "Este grupo tem todos os seus registros enviados para: {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                            log_channel)
        return "Nenhum canal de registro está definido para este grupo!"


    __help__ = """
*Admin only:*
- /logchannel: obter informações do canal de registro
- /setlog: definir o canal de registro.
- /unsetlog: desative o canal de log.

A configuração do canal de registro é feita por:
- adicionando o bot ao canal desejado (como administrador!)
- enviando /setlog no canal
- encaminhando o /setlog para o grupo
"""

    __mod_name__ = "🎟️ Canal de registro 🎟️"

    LOG_HANDLER = CommandHandler("logchannel", logging)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func
