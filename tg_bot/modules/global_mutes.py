import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_mutes_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GMUTE
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GMUTE_ENFORCE_GROUP = 6


@run_async
def gmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Voc� n�o parece estar se referindo a um usu�rio.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Eu espio, com meu olhinho ... uma guerra de usu�rios de sudo! Por que voc�s est�o se virando?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH algu�m est� tentando gmutar um usu�rio de suporte! *pega pipoca*")
        return

    if user_id == bot.id:
        message.reply_text("-_- T�o engra�ado, vamos me calar, por que n�o? Boa tentativa.")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Isso n�o � um usu�rio!")
        return

    if sql.is_user_gmuted(user_id):
        if not reason:
            message.reply_text("Este usu�rio j� foi movido; Eu mudaria o motivo, mas voc� n�o me deu um...")
            return

        success = sql.update_gmute_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if success:
            message.reply_text("Este usu�rio j� foi movido; Eu atualizei o motivo do gmute embora!")
        else:
            message.reply_text("Voc� se importa em tentar novamente? Achei que essa pessoa fosse mutada, mas n�o foi? "
                               "Estou muito confuso")

        return

    message.reply_text("*Prepara a fita adesiva* 😉")

    muter = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} est� gmutando o usu�rio {} "
                 "Porque:\n{}".format(mention_html(muter.id, muter.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "Nenhuma raz�o dada"),
                 html=True)

    sql.gmute_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gmute(chat_id):
            continue

        try:
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=False)
        except BadRequest as excp:
            if excp.message == "O usu�rio � um administrador do chat":
                pass
            elif excp.message == "Chat not found":
                pass
            elif excp.message == "Direitos insuficientes para restringir / n�o restringir membro do bate-papo":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "Peer_id_invalid":  # Suspect this happens when a group is suspended by telegram.
                pass
            elif excp.message == "O chat em grupo foi desativado":
                pass
            elif excp.message == "Precisa ser o convite de um usu�rio para expuls�-lo de um grupo b�sico":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            elif excp.message == "Apenas o criador de um grupo b�sico pode expulsar os administradores do grupo":
                pass
            elif excp.message == "M�todo est� dispon�vel apenas para supergrupos":
                pass
            elif excp.message == "N�o � poss�vel rebaixar o criador do chat":
                pass
            else:
                message.reply_text("N�o foi poss�vel gmutar devido a: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "N�o foi poss�vel gmutar devido a: {}".format(excp.message))
                sql.ungmute_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "gmute conclu�do!")
    message.reply_text("A pessoa foi mutada.")


@run_async
def ungmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Voc� n�o parece estar se referindo a um usu�rio.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Isso n�o � um usu�rio!")
        return

    if not sql.is_user_gmuted(user_id):
        message.reply_text("Este usu�rio n�o foi mutado!")
        return

    muter = update.effective_user  # type: Optional[User]

    message.reply_text("Eu vou permitir {} fale novamente, globalmente.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} tem usu�rio n�o ativado {}".format(mention_html(muter.id, muter.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gmute(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'restricted':
                bot.restrict_chat_member(chat_id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)

        except BadRequest as excp:
            if excp.message == "O usu�rio � um administrador do chat":
                pass
            elif excp.message == "Bate-papo n�o encontrado":
                pass
            elif excp.message == "Direitos insuficientes para restringir / n�o restringir membro do bate-papo":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "O m�todo est� dispon�vel para supergrupos e chats de canal apenas":
                pass
            elif excp.message == "N�o est� no chat":
                pass
            elif excp.message == "channel_private":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            else:
                message.reply_text("N�o foi poss�vel reativar o som devido a: {}".format(excp.message))
                bot.send_message(OWNER_ID, "N�o foi poss�vel reativar o som devido a: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungmute_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "un-gmute complete!")

    message.reply_text("A pessoa foi reativada.")


@run_async
def gmutelist(bot: Bot, update: Update):
    muted_users = sql.get_gmute_list()

    if not muted_users:
        update.effective_message.reply_text("N�o existem usu�rios gmutados! Voc� � mais gentil do que eu esperava...")
        return

    mutefile = 'Dane-se esses caras.\n'
    for user in muted_users:
        mutefile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            mutefile += "Raz�o: {}\n".format(user["reason"])

    with BytesIO(str.encode(mutefile)) as output:
        output.name = "gmutelist.txt"
        update.effective_message.reply_document(document=output, filename="gmutelist.txt",
                                                caption="Aqui est� a lista de usu�rios atualmente gmutados.")


def check_and_mute(bot, update, user_id, should_message=True):
    if sql.is_user_gmuted(user_id):
        bot.restrict_chat_member(update.effective_chat.id, user_id, can_send_messages=False)
        if should_message:
            update.effective_message.reply_text("Essa � uma pessoa m�, vou silenci�-los para voc�!")


@run_async
def enforce_gmute(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gmute.
    if sql.does_chat_gmute(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_mute(bot, update, user.id, should_message=True)
        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_mute(bot, update, mem.id, should_message=True)
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_mute(bot, update, user.id, should_message=True)

@run_async
@user_admin
def gmutestat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gmutes(update.effective_chat.id)
            update.effective_message.reply_text("Eu habilitei gmutes neste grupo. Isso ajudar� a proteg�-lo "
                                                "de spammers, personagens desagrad�veis e Anirudh.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gmutes(update.effective_chat.id)
            update.effective_message.reply_text("Desativei gmutes neste grupo. GMutes n�o afetar�o seus usu�rios "
                                                "mais. Voc� estar� menos protegido de Anirudh!")
    else:
        update.effective_message.reply_text("D�-me alguns argumentos para escolher uma configura��o! on/off, yes/no!\n\n"
                                            "Sua configura��o atual �: {}\n"
                                            "Quando True, qualquer gmute que acontecer tamb�m acontecer� em seu grupo. "
                                            "Quando False, eles n�o v�o, deixando voc� � poss�vel merc� de "
                                            "spammers.".format(sql.does_chat_gmute(update.effective_chat.id)))


def __stats__():
    return "{} gmuted users.".format(sql.num_gmuted_users())


def __user_info__(user_id):
    is_gmuted = sql.is_user_gmuted(user_id)

    text = "Globally muted: <b>{}</b>"
    if is_gmuted:
        text = text.format("Yes")
        user = sql.get_gmuted_user(user_id)
        if user.reason:
            text += "\nRaz�o: {}".format(html.escape(user.reason))
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Este bate-papo est� impondo *gmutes*: `{}`.".format(sql.does_chat_gmute(chat_id))


__help__ = """
*Admin apenas:*
 - /gmutestat <on/off/yes/no>: Desativar� o efeito dos silenciamentos globais em seu grupo ou retornar� suas configura��es atuais.
Gmutes, tamb�m conhecidos como mutes globais, s�o usados pelos propriet�rios de bot para silenciar spammers em todos os grupos. Isso ajuda a proteger \
voc� e seus grupos removendo inundadores de spam o mais r�pido poss�vel. Eles podem ser desativados para o seu grupo chamando \
/gmutestat
"""

__mod_name__ = "🔇 Global Mute 🔇"

GMUTE_HANDLER = CommandHandler("gmute", gmute, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGMUTE_HANDLER = CommandHandler("ungmute", ungmute, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GMUTE_LIST = CommandHandler("gmutelist", gmutelist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GMUTE_STATUS = CommandHandler("gmutestat", gmutestat, pass_args=True, filters=Filters.group)

GMUTE_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gmute)

dispatcher.add_handler(GMUTE_HANDLER)
dispatcher.add_handler(UNGMUTE_HANDLER)
dispatcher.add_handler(GMUTE_LIST)
dispatcher.add_handler(GMUTE_STATUS)

if STRICT_GMUTE:
    dispatcher.add_handler(GMUTE_ENFORCER, GMUTE_ENFORCE_GROUP)
