from typing import Optional, List

from telegram import ParseMode
from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.connection_sql as sql
from tg_bot import dispatcher, LOGGER, SUDO_USERS
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time

# from tg_bot.modules.translations.strings import tld

from tg_bot.modules.keyboard import keyboard

@user_admin
@run_async
def allow_connections(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
            print(var)
            if (var == "no"):
                sql.set_allow_connect_to_chat(chat.id, False)
                update.effective_message.reply_text("Conex�es desativadas para este chat para usu�rios")
            elif(var == "yes"):
                sql.set_allow_connect_to_chat(chat.id, True)
                update.effective_message.reply_text("Conex�es habilitadas para este chat para usu�rios")
            else:
                update.effective_message.reply_text("Por favor, insira on/yes/off/no no grupo!")
        else:
            update.effective_message.reply_text("Por favor, insira on/yes/off/no no grupo!")
    else:
        update.effective_message.reply_text("Por favor, insira on/yes/off/no em grupo!")


@run_async
def connect_chat(bot, update, args):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    if update.effective_chat.type == 'private':
        if len(args) >= 1:
            try:
                connect_chat = int(args[0])
            except ValueError:
                update.effective_message.reply_text("ID de bate-papo inv�lido fornecido!")
            if (bot.get_chat_member(connect_chat, update.effective_message.from_user.id).status in ('administrator', 'creator') or 
                                     (sql.allow_connect_to_chat(connect_chat) == True) and 
                                     bot.get_chat_member(connect_chat, update.effective_message.from_user.id).status in ('member')) or (
                                     user.id in SUDO_USERS):

                connection_status = sql.connect(update.effective_message.from_user.id, connect_chat)
                if connection_status:
                    chat_name = dispatcher.bot.getChat(connected(bot, update, chat, user.id, need_admin=False)).title
                    update.effective_message.reply_text("Conectado com sucesso a *{}*".format(chat_name), parse_mode=ParseMode.MARKDOWN)

                    #Add chat to connection history
                    history = sql.get_history(user.id)
                    if history:
                        #Vars
                        if history.chat_id1:
                            history1 = int(history.chat_id1)
                        if history.chat_id2:
                            history2 = int(history.chat_id2)
                        if history.chat_id3:
                            history3 = int(history.chat_id3)
                        if history.updated:
                            number = history.updated

                        if number == 1 and connect_chat != history2 and connect_chat != history3:
                            history1 = connect_chat
                            number = 2
                        elif number == 2 and connect_chat != history1 and connect_chat != history3:
                            history2 = connect_chat
                            number = 3
                        elif number >= 3 and connect_chat != history2 and connect_chat != history1:
                            history3 = connect_chat
                            number = 1
                        else:
                            print("Error")
                    
                        print(history.updated)
                        print(number)

                        sql.add_history(user.id, history1, history2, history3, number)
                        print(history.user_id, history.chat_id1, history.chat_id2, history.chat_id3, history.updated)
                    else:
                        sql.add_history(user.id, connect_chat, "0", "0", 2)
                    #Rebuild user's keyboard
                    keyboard(bot, update)
                    
                else:
                    update.effective_message.reply_text("A conex�o falhou!")
            else:
                update.effective_message.reply_text("Conex�es para este bate-papo n�o permitidas!")
        else:
            update.effective_message.reply_text("Insira o ID do bate-papo para se conectar!")
            history = sql.get_history(user.id)
            print(history.user_id, history.chat_id1, history.chat_id2, history.chat_id3, history.updated)

    else:
        update.effective_message.reply_text("Uso limitado apenas a PMs!")


def disconnect_chat(bot, update):
    if update.effective_chat.type == 'private':
        disconnection_status = sql.disconnect(update.effective_message.from_user.id)
        if disconnection_status:
            sql.disconnected_chat = update.effective_message.reply_text("Desconectado do bate-papo!")
            #Rebuild user's keyboard
            keyboard(bot, update)
        else:
           update.effective_message.reply_text("Desconex�o malsucedida!")
    else:
        update.effective_message.reply_text("Uso restrito apenas a PMs")


def connected(bot, update, chat, user_id, need_admin=True):
    if chat.type == chat.PRIVATE and sql.get_connected_chat(user_id):
        conn_id = sql.get_connected_chat(user_id).chat_id
        if (bot.get_chat_member(conn_id, user_id).status in ('administrator', 'creator') or 
                                     (sql.allow_connect_to_chat(connect_chat) == True) and 
                                     bot.get_chat_member(user_id, update.effective_message.from_user.id).status in ('member')) or (
                                     user_id in SUDO_USERS):
            if need_admin == True:
                if bot.get_chat_member(conn_id, update.effective_message.from_user.id).status in ('administrator', 'creator') or user_id in SUDO_USERS:
                    return conn_id
                else:
                    update.effective_message.reply_text("Voc� precisa ser um administrador em um grupo conectado!")
                    exit(1)
            else:
                return conn_id
        else:
            update.effective_message.reply_text("Grupo mudou de conex�o de direitos ou voc� n�o � mais administrador.\nVou desconectar voc�.")
            disconnect_chat(bot, update)
            exit(1)
    else:
        return False



__help__ = """
A��es est�o dispon�veis com grupos conectados:
 • Ver e editar notas
 • Ver e editar filtros
 • Mais no futuro!

 - /connect <chatid>: Conecte-se ao bate-papo remoto
 - /disconnect: Desconectar do bate-papo
 - /allowconnect on/yes/off/no: Permitir conectar usu�rios ao grupo
"""

__mod_name__ = "🔗 Conex�es 🔗"

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, allow_edited=True, pass_args=True)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat, allow_edited=True)
ALLOW_CONNECTIONS_HANDLER = CommandHandler("allowconnect", allow_connections, allow_edited=True, pass_args=True)

dispatcher.add_handler(CONNECT_CHAT_HANDLER)
dispatcher.add_handler(DISCONNECT_CHAT_HANDLER)
dispatcher.add_handler(ALLOW_CONNECTIONS_HANDLER)
