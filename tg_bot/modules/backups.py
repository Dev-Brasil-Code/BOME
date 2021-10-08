import json
from io import BytesIO
from typing import Optional

from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.__main__ import DATA_IMPORT
from tg_bot.modules.helper_funcs.chat_status import user_admin


@run_async
@user_admin
def import_data(bot: Bot, update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    # TODO: allow uploading doc with command, not just as reply
    # only work with a doc
    if msg.reply_to_message and msg.reply_to_message.document:
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text("Tente baixar e recarregar o arquivo como você mesmo antes de importar - este parece "
                           "ser duvidoso!")
            return

        with BytesIO() as file:
            file_info.download(out=file)
            file.seek(0)
            data = json.load(file)

        # only import one group
        if len(data) > 1 and str(chat.id) not in data:
            msg.reply_text("Há mais de um grupo aqui neste arquivo, e nenhum tem o mesmo id de bate-papo que este grupo "
                           "- como faço para escolher o que importar?")
            return

        # Select data source
        if str(chat.id) in data:
            data = data[str(chat.id)]['hashes']
        else:
            data = data[list(data.keys())[0]]['hashes']

        try:
            for mod in DATA_IMPORT:
                mod.__import_data__(str(chat.id), data)
        except Exception:
            msg.reply_text("Ocorreu uma exceção ao restaurar seus dados. O processo pode não estar completo. Se "
                           "você está tendo problemas com isso, envie uma mensagem para @Claynetchat com seu arquivo de backup para que "
                           "problema pode ser depurado. Meus proprietários ficarão felizes em ajudar, e cada bug "
                           "relatado me torna melhor! Obrigado! :)")
            LOGGER.exception("Importar para chatid %s com nome %s fracassado.", str(chat.id), str(chat.title))
            return

        # TODO: some of that link logic
        # NOTE: consider default permissions stuff?
        msg.reply_text("Backup totalmente importado. Bem vindo de volta! :D")


@run_async
@user_admin
def export_data(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    msg.reply_text("")


__mod_name__ = "ðŸ’¾ Backups ðŸ’¾"

__help__ = """
*Apenas administrador:*
 - /import: responda a um arquivo de backup do mordomo do grupo para importar o máximo possível, tornando a transferência super simples! Observação \
naquela arquivos / fotos não pode ser importado devido a restrições de telegrama.
 - /export: !!! Este não é um comando ainda, mas deve chegar em breve!
"""
IMPORT_HANDLER = CommandHandler("import", import_data)
EXPORT_HANDLER = CommandHandler("export", export_data)

dispatcher.add_handler(IMPORT_HANDLER)
# dispatcher.add_handler(EXPORT_HANDLER)
