import datetime
import mercadopago
import telebot
import base64
from telebot import types
from PIL import Image
from io import BytesIO
import time
import logging
import inspect

def example_func(a, b=10, *args, **kwargs):
    pass

argspec = inspect.getfullargspec(example_func)
print(argspec)

print("Iniciando o bot...")

# Configurar o logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

sdk = mercadopago.SDK('APP_USR-8610660431907045-062516-e253bcdf90c3518b1f2709aed99bf23d-702450853')
bot = telebot.TeleBot('7417376623:AAEyQPoqyrLeAK4jcJn4iD8JlljIHzaHMSk')


@bot.message_handler(commands=['start'])
def cmd_start(message):
    start_message = "Bem-vindo ao Grupo Vip!\n\n" \
                    "Para realizar um pagamento via Pix, utilize o comando /pix .\n" \
                    "Por exemplo: /pix\n\n" \
                    "Você receberá um QR code para realizar o pagamento.\n" \
                    "O bot verificará automaticamente se o pagamento foi recebido e enviará O LINK.\n\n" \
                    "Favor Qualquer Duvida Chame @SUPERVISOBR"
    bot.reply_to(message, start_message)


@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_message = "Lista de comandos disponíveis:\n\n" \
                   "/start - Iniciar o bot e obter informações\n" \
                   "/help - Exibir esta mensagem de ajuda\n" \
                   "/listar - Listar pagamentos recentes\n" \
                   "/verificar [ID] - Verificar o status de um pagamento pelo ID\n" \
                   "/pix [valor] - Realizar um pagamento via Pix\n\n" \
                   "Exemplo: /pix 10"
    bot.reply_to(message, help_message)


def create_payment(value, client_name):
    expire = datetime.datetime.now() + datetime.timedelta(minutes=30)
    expire = expire.strftime("2025-06-26T21:21:29.000-03:00")

    description = f"Pagamento de {client_name}"

    payment_data = {
        "transaction_amount": int(value),
        "payment_method_id": 'pix',
        "installments": 1,
        "description": description,
        "date_of_expiration": f"{expire}",
        "payer": {
            "email": 'delacavipp@gmail.com'
        }
    }
    result = sdk.payment().create(payment_data)
    operation_number = result['response']['id']  # Extrai o ID da transação (Número de Operação de Cobrança)
    return result, operation_number


def verificar_pagamento(operation_number, chat_id, message_id, client_name):
    for _ in range(24):  # Executa a verificação por 4 minutos (24 vezes a cada 10 segundos)
        time.sleep(10)  # Aguarda 10 segundos antes de cada verificação
        result = sdk.payment().get(operation_number)
        status = result['response']['status']
        if status == 'approved':
            value = result['response']['transaction_amount']
            logger.info(f"Pagamento de número {operation_number} recebido com sucesso!")
            bot.send_message(chat_id,
                             f"Pagamento Confirmado ! {operation_number} Link Do Grupo t.me/+ML2BAwK8E5owZDYx\n\n"
                             f"Detalhes do pagamento:\n"
                             f"Cliente: {client_name}\n"
                             f"Valor: R${value}\n"
                             f"Link do comprovante:\n"
                             f"https://www.mercadopago.com.br/money-out/transfer/api/receipt/pix_pdf/"
                             f"{operation_number}/pix_account/pix_payment.pdf")
            bot.delete_message(chat_id, message_id)  # Apaga a mensagem com o QR code
            return  # Interrompe o loop e a função
    logger.info(f"Pagamento de número {operation_number} não recebido após 4 minutos.")
    bot.send_message(chat_id, "Pagamento não recebido após 4 minutos.")
    bot.delete_message(chat_id, message_id)  # Apaga a mensagem com o QR code


def capture_name(message):
    global value  # Adicione esta linha para utilizar a variável global "value"
    client_name = message.text
    payment, operation_number = create_payment(value, client_name)
    result = payment['response']
    pix_copia_cola = result['point_of_interaction']['transaction_data']['qr_code']
    qr_code = result['point_of_interaction']['transaction_data']['qr_code_base64']
    qr_code = base64.b64decode(qr_code)
    qr_code_img = Image.open(BytesIO(qr_code))
    qrcode_output = qr_code_img.convert('RGB')

    # Caso queira que o bot envie o qrcode no grupo ou no privado descomente a linha abaixo!
    sent_message = bot.send_photo(message.chat.id, qrcode_output,
                                  # Caso queira que o bot só envie o qrcode no privado descomente a linha abaixo e comente a de cima!
                                  # sent_message = bot.send_photo(message.from_user.id, qrcode_output,
                                  f'<code>{pix_copia_cola}</code>\n\n'
                                  f'Número de operação: {operation_number}\n'
                                  f'Cliente: {client_name}\n\n'
                                  f'Aguardando pagamento...',
                                  parse_mode='HTML')

    # Gerando log do pagamento
    logger.info(f"Pix Valor: R${value}, Cliente: {client_name}, Data e Hora: {datetime.datetime.now()}")
    # Agendamento da verificação periódica do pagamento
    verificar_pagamento(operation_number, message.chat.id, sent_message.message_id, client_name)


@bot.message_handler(commands=['listar'])
def cmd_listar(message):
    payments = sdk.payment().search({'sort': 'date_created', 'criteria': 'desc'})
    for payment in payments['response']['results']:
        print(payment['id'], payment['status'], payment['description'], payment['date_of_expiration'])
        logger.info(f"ID: {payment['id']}, Status: {payment['status']}, Descrição: {payment['description']}, "
                    f"Data de Expiração: {payment['date_of_expiration']}")


@bot.message_handler(commands=['verificar'])
def cmd_verificar(message):
    if len(message.text.split()) < 2:
        bot.reply_to(message, "Por favor, forneça o número da transação.")
        return

    pg_id = message.text.split()[1]
    result = sdk.payment().get(pg_id)
    status = result['response']['status']
    if status == 'approved':
        bot.reply_to(message, "Pagamento recebido!")
        logger.info(f"Verificação de pagamento - Pagamento recebido - ID: {pg_id}")
    elif status == 'cancelled':
        bot.reply_to(message, "Pagamento excedeu o tempo!")
        logger.info(f"Verificação de pagamento - Pagamento excedeu o tempo - ID: {pg_id}")
    else:
        bot.reply_to(message, "Pagamento pendente ou não encontrado.")
        logger.info(f"Verificação de pagamento - Pagamento pendente ou não encontrado - ID: {pg_id}")


@bot.message_handler(commands=['pix'])
def cmd_pix(message):
    try:
        markup = types.InlineKeyboardMarkup()

        # Defina os preços fixos que você deseja oferecer como opções
        preco1 = types.InlineKeyboardButton('Grupo Vip R$ 16', callback_data='16')

        # Adicione os botões ao markup
        markup.row(preco1)

        bot.reply_to(message, "Selecione o Grupo Abaixo:", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, "Ocorreu um erro ao processar a solicitação. Tente novamente mais tarde.")


# Handler para lidar com as callbacks dos botões inline
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        global value
        value = float(call.data)  # Converte o valor do callback para float
        bot.send_message(call.message.chat.id, "Digite Seu Nome/apelido:")
        bot.register_next_step_handler(call.message, capture_name)
    except Exception as e:
        bot.send_message(call.message.chat.id,
                         "Ocorreu um erro ao processar a solicitação. Tente novamente mais tarde.")


if __name__ == "__main__":
    bot.infinity_polling()
