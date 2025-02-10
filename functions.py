from langchain_core.tools import tool
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sqlite3
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import datetime
import logging

# LOGS
log_format = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

# Ubicaciones de trabajo
FOLDER = os.getcwd()
DATA_FOLDER = os.path.join(FOLDER, "data")

# Funcion para extraer informacion de la base de datos
@tool
def get_transaction(user_id):

    """
    Use this functon to find and return a table with the user's transactions
    """

    # Lectura de los datos de los CUS simulados
    # Se supone que si guardo la tabla en memoria, el acceso es mas rapido
    # Aunque no deberia porque podria colapsar la RAM
    # Mejor leerla y luego eliminar su registro en memoria cuando ya tenga la respuesta
    # Es una opción que luego veremos si funciona o no, por ahora en memoria
    db = pd.read_excel(
        os.path.join(DATA_FOLDER, "data_cus.xlsx"),
        sheet_name=0,
        dtype=str,
    )
    logger.info("Transacciones consultadas")

    # Basicamente lo que hacemos es filtrar la base de datos de las transacciones 
    # Unicamente para las del usuario que estoy buscando, nada más
    # El resultado es una TABLA REDUCIDA que el LLM luego va leer para encontrar lo que le pidamos

    return db[db["cedula"]==user_id]

# Función para generar un numero consecutivo que pueda meter en la base de datos
@tool
def generate_case_number():

    """
    Use this function to generate a case number for the user's case.
    """

    conn = sqlite3.connect(
        os.path.join(FOLDER, "case_db.db")
    )

    df = pd.read_sql_query("SELECT * FROM casos", conn)
    number = df["case_id"].tolist()[-1]
    number += 1
    logger.info("Numero de caso generado")
    conn.close()    

    return number

# Función para enviar correo al usuario
@tool
def send_user_email(user_email, user_name, case_info, case_number, date):

    """
    Use this function to send emails to the user as soon as you have the user's email.
    """
    
    # Credenciales
    sender_email = "anavi.bbva@gmail.com"
    sender_password = "nmmi duca pbqv etak"

    # Contenido
    subject = f"ANAVI (BBVA) - CASO #{case_number}"
    body = f"""
¡Hola! {user_name}
Soy ANAVI - Asistente Virtual de BBVA

He recolectado la siguiente información sobre tu caso:

Fecha: {date}
Número de caso: {case_number}
Descripción: {case_info}

Le he asignado tu caso al área encargada y será atendido a la máxima brevedad posible. Tendrás tu respuesta \
en un máximo de 5 días hábiles. Recuerda que todos nuestros canales estan disponibles para ti.
"""

# Envio
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = user_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Creating the server connection and sending the email
    try:
        # Setting up the SMTP server (Gmail's SMTP server)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Upgrade the connection to secure

        # Logging into the email account
        server.login(sender_email, sender_password)

        # Sending the email
        server.sendmail(sender_email, user_email, message.as_string())

        # Closing the server connection
        server.quit()

        logger.info("Correo enviado exitosamente al usuario")

    except Exception as e:
        logger.error(f"Error enviando correo del usuario: {e}")


# Funcion para enviar el correo al área encargada
@tool
def send_area_email(user_name, user_document, area_name, case_info, case_number, date):

    """
    Use this function to send emails to the responsible area as soon as you have the area's name and all 
    the info of the user's case.
    """
    
    # Utilizamos el nombre del area que detecto el bicho para relacionarlo con el correo
    # Por el momento es mas confiable a permitir que el bicho lo haga por si mismo
    # con un modelo mejor, resultado mejor y nos ahorramos esta parte
    # o quizas no...?
    mails = {
        "TRANS": "juandavid.duran@bbva.com",
        "SUCUR": "leslykatherine.pineros@bbva.com",
        "SEGUR": "lauraconsuelo.caro@bbva.com",
        "PRODU": "santiago.moreno.rodriguez@bbva.com"
    }
    area_email = mails[area_name]

    names = {
        "TRANS": "Transacciones",
        "SUCUR": "Sucursales Físicas",
        "SEGUR": "Seguros",
        "PRODU": "Productos Financieros"
    }
    area_name = names[area_name]

    # Credenciales
    sender_email = "anavi.bbva@gmail.com"
    sender_password = "nmmi duca pbqv etak"

    # Contenido
    subject = f"ANAVI (BBVA) - CASO #{case_number}"
    body = f"""
He recolectado el siguiente caso:

Fecha: {date}
Nombre: {user_name}
Documento: {user_document}
Número de caso: {case_number}
Descripción: {case_info}
Area: {area_name}

He identificado que este caso pertenece al área de {area_name} y como consecuencia estas recibiendo el aviso.
Toda la información ya ha sido documentada y almacenada en la base de datos correspondiente.
"""

# Envio
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = area_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Creating the server connection and sending the email
    try:
        # Setting up the SMTP server (Gmail's SMTP server)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Upgrade the connection to secure

        # Logging into the email account
        server.login(sender_email, sender_password)

        # Sending the email
        server.sendmail(sender_email, area_email, message.as_string())

        # Closing the server connection
        server.quit()

        logger.info("Correo enviado exitosamente al area encargada")

    except Exception as e:
        logger.error(f"Error enviando correo del area: {e}")

# Función para generar un comprobante
@tool
def generate_image(user_id, date, description, value, cus, account, state):
    
    """
    Use this function to use the transaction's info to create a image that 
    can be donwloaded by the user.
    """
    logger.info("Generando imagen")

    data = {
        "Cédula": user_id,
        "Fecha": date,
        "Descripción": description,
        "Valor": value,
        "CUS": cus,
        "Estado": state,
        "Cuenta de Ahorros": account
    }

    try:
        # Acá dejamos los parametros basicos de la libreria para generar imagenes
        font = os.path.join(FOLDER, "fonts", "ARIAL.TTF")
        boldfont = ImageFont.truetype(font, 20)
        normalfont = ImageFont.truetype(font, 20)

        # Esta es la base en blanco para dibujar por decirlo asi
        # Este tamaño es el que ha funcionado que no se ve feo
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        # Este es el logo fondo blanco del BBVA para que se vea coqueto
        logo = Image.open(os.path.join(FOLDER, "logo_bbva.jpg"))
        logo = logo.resize((200, 90))
        img.paste(logo, ((800 - logo.width) // 2, 20))

        # Mini función para centrar el texto que se vea mejor
        def draw_centered_text(draw, text, y, font, image_width, fill_color):
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            x = (image_width - text_width) // 2
            draw.text((x, y), text, font=font, fill=fill_color)

        # Si el estado es exitoso entonces sera de color de verde y si no, es rojo pues
        color = (0, 128, 0) if data['Estado'] == "Exitoso" else (255, 0, 0)

        # Agregar texto centrado a la imagen con descripciones en negrita y valores en normal
        y_offset = 130
        draw_centered_text(d, f"Pago {data['Estado'].lower()}", y_offset, boldfont, img.width, color)
        y_offset += 40
        draw_centered_text(d, f"Valor: {data['Valor']}", y_offset, normalfont, img.width, (0, 0, 0))
        y_offset += 40
        draw_centered_text(d, f"Fecha: {data['Fecha']}", y_offset, normalfont, img.width, (0, 0, 0))
        y_offset += 40
        draw_centered_text(d, f"Producto o servicio: {data['Descripción']}", y_offset, normalfont, img.width, (0, 0, 0))
        y_offset += 40
        draw_centered_text(d, f"Cédula: {data['Cédula']}", y_offset, normalfont, img.width, (0, 0, 0))
        y_offset += 40
        draw_centered_text(d, f"Cuenta de Ahorros: {data['Cuenta de Ahorros']}", y_offset, normalfont, img.width, (0, 0, 0))
        y_offset += 40
        draw_centered_text(d, f"Código de confirmación (CUS): {data['CUS']}", y_offset, normalfont, img.width, (0, 0, 0))

        # Guardar la imagen
        img.save(os.path.join(FOLDER, f"{cus}.png"))

        logger.info("Imagen generada exitosamente.")
    
    except Exception as e:
        logger.error(f"Error generando imagen: {e}")

    return "Imagen generada"

# Función para obtener la fecha y hora del caso
@tool
def get_case_date():

    """
    Use this function to get the current date and time to use in the user's case.
    """

    logger.info("Fecha recuperada")

    return  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Funcion para almacenar la informacion
@tool
def store_case(case_id, date, user_name, user_id, user_email, case_info):

    """
    Use thus function to store in a database the user's case info as sson as you have 
    all the information.
    """

    conn = sqlite3.connect(
        os.path.join(FOLDER, "case_db.db")
    )
    cursor = conn.cursor()

    # No tiene sentido que agreguemos un caso que ya existe
    # Pero si tiene sentido que me alerte cuando eso sucede
    cursor.execute('''
    SELECT * FROM casos WHERE case_id = ?
    ''', (case_id,))
    existing_case = cursor.fetchone()

    if existing_case:
        logger.info("Ya existe ese caso")
        response = "El caso que intentas agregar ya existe en la BD."
    else:
        cursor.execute('''
        INSERT INTO casos (case_id, date, user_name, user_id, user_email, case_info)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (case_id, date, user_name, user_id, user_email, case_info))
        conn.commit()
        logger.info("Caso agregado a la bd")
        response = "El caso ha sido agregado exitosamente a la BD"

    return response