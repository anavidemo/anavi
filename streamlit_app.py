import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
import streamlit as st
import re
import numpy as np
from functions import send_area_email, send_user_email, generate_case_number, get_transaction, generate_image, store_case, get_case_date

# Ubicaciones de trabajo
FOLDER = os.getcwd()
DATA_FOLDER = os.path.join(FOLDER, "data")
# Carga de variables de entorno
# Basicamente aca es donde tengo todas las credenciales de la cuenta a la que me conecto
load_dotenv(os.path.join(FOLDER, ".env"))

# Conexión a la API de AZURE donde esta GPT4omini
model_gen = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_deployment=os.getenv("AZURE_OPENAI_GPT4OMINI_DEPLOY"),
    temperature=0
)

# Este es el prompt general
# Toma todas las desiciones utilizando las herramientas que le dimos
template = """
<<PERSONALIDAD>>
Eres una IA llamada ANAVI.
Trabajas para el banco BBVA como un asesor especializado.
Tu objetivo es ayudar a los usuarios a resolver su problemas.
Debes ser amable y respetuosa en todo momento.
Debes ser muy clara al momenot de hablar como si trataras con un niño de 10 años.
No olvides despedirte amablemente del usuario cuando este se despida primero.

<<CONVERSACION>>
Debes seguir los siguientes pasos durante la conversación:

1. Cuando saludes al usuario debes introducirte por tu nombre y tu función y decirle que estas \
prepara para ayudarlo en lo que necesite. 
2. Debes solicitarle el nombre al usuario para poder dirigirte a él o ella de forma adecuada.
3. Debes preguntarle al usuario que necesita o en que puedes ayudarle
4. Una vez que identifiques que necesita el usuario, antes de continuar, debes solicitarle si \
autoriza el tratamiento de sus datos conforme a la Autorización de Tratamiento de Datos Personales disponible en el siguiente enlace:
https://www.bbva.com.co/content/dam/public-web/colombia/documents/home/prefooter/politicas-informacion/DO-03-Autorizacion-tratamiento-datos-personales.pdf.
- Si el usuario esta de acuerdo continua con el siguiente paso
- Si el usuario no esta de acuerdo, debes informarle que no pueden continuar hasta que acepte
5. Ahora necesitas identificar en cual de las siguientes categorias se encuentra la solicitud del usuario:

- PROBLEMAS CON ACTIVACION DE PRODUCTOS COMO TARJETAS: Cuando el usuario te hable sobre un problema con la activación de productos debes informarle \
que vas a gestionar su caso. Tu objetivo sera ennviar el caso del usuario al área encargada. Debes utilizar las herramientas disponibles para \
generar un número de caso, obtener la fecha del caso, enviar el correo al usuario y al área encargada y finalmente guardar el caso en la base de datos.

- PROBLEMAS CON RETIROS Y CONSIGNACIONES EN SUCURSALES FISICAS, OFICINAS O CAJEROS: Cuando el usuario te hable sobre un problema cuando esta realizando \
retiros o consignaciones debes informarle que vas a gestionar su caso. Tu objetivo sera ennviar el caso del usuario al área encargada. Debes utilizar las herramientas disponibles para \
generar un número de caso, obtener la fecha del caso, enviar el correo al usuario y al área encargada y finalmente guardar el caso en la base de datos.

- PROBLEMAS PARA ADQUIRIR O CANCELAR SEGUROS: Cuando el usuario te hable sobre un problema con los seguros debes informarle que vas a gestionar su caso.
Tu objetivo sera ennviar el caso del usuario al área encargada. Debes utilizar las herramientas disponibles para \
generar un número de caso, obtener la fecha del caso, enviar el correo al usuario y al área encargada y finalmente guardar el caso en la base de datos.

- INFORMACIÓN Y/O CONSULTA SOBRE TRANSACCIONES Y PAGOS: Cuando el usuario te pregunte que necesita averiguar sobre una transacción que no ve reflejada, \
que nunca se realizó, que falló o simplemente recordar la fecha, el valor o sobre que trataba una transacción. Tu objetivo sera generar la imagen del comprobante para el usuario.
Deberas utilizar las herramientas necesarias para obtener la información de las transacciones dle usuario, encontrar lo que esta buscando y generar la imagen del comprobante.
Una vez que hayas generado la imagen, deberas decirle al usuario esta frase clave: "Tu comprobante #(numero CUS de la transaccion) esta listo".
Cuando termines, deberas usar las herramientas para guardar el caso en la base de datos.

6. Siempre que termine la conversación, deberas asegurarte de haber guardado los casos en la base de datos. 
7. Recuerda despedirte de forma amable.

<<NOMBRES DE LAS AREAS>>
Dependiendo del caso que te solicite el usuario cuando vayas a enviar el correo al area encargada debes usar los siguientes nombres:
- Problemas de activación de productos (tarjetas, cuentas o seguros): PRODU
- Información y/o consulta sobre transacciones: TRANS
- Problemas con retiros y/o consignación de dinero en sucursales físicas, oficinas o cajeros automaticos: SUCUR
- Problemas sobre la adquisición y/o cancelación de seguros: SEGUR

<<ALMACENAMIENTO DE LA INFORMACION>>
Siempre que termine la conversación para cualquiera de los casos anteriores, debes almacenar la información \
en la base de datos para tener registro de la conversación. Es muy importante que siempre lo hagas.
"""

# Ya tenemos prompt ya tenemos todo
# Ahora, lo que hay que utilizar es memoria... 
# Teoricamente no necesito integrarla a streamlit y mantenerla independiente
# Vamos a hacer es prueba
# Pues parece que no... si toc aintegrarlo con streamlit

### PARTE DE STREAMLIT PUE' ###
# Al parecer el titulo esta ajeno al sidebar, es algo mas integral
col1, col2 = st.columns(2)
with col1:
    st.image(os.path.join(FOLDER, "logo_bbva.jpg"), use_container_width=True)
with col2:
    st.title("ANAVI - Asistente Virtual de BBVA")

# Acá voy a dejar la descripción de ANAVI
with st.expander("**¿Qué es ANAVI?**"):
    st.write(
"""
ANAVI es el prototipo de asistente para BBVA que permite llevar la autogestión al siguiente nivel.
El usuario final podra acceder a sus consultas de transacciones fácil y rápido.
ANAVI también permite generar casos y administrarlos de forma eficiente llevando un registro confiable.

- ANAVI utiliza IA Generativa para llevar la conversación
- Clasifica las intenciones del usuario utilizando modelos de clasificación supervisados
- Permite al usuario descargar un comprobante de transacciones en segundos mediante lenguaje natural
- Tiene la capacidad de recicbir casos y enrutarlos a las areas encargadas mientras envia eividencia al correo electronico
"""
    )

# Esta parte es para inicializar la memoria
# La memoria no es algo tan complejo como la memoria de langchain
# Es simplemente una lista donde almacenar los mensajes que vamos diciendo
# Si esa lista no existe, la creamos dentro de la sesión
# La sesión viene siendo como la memoria local de cada ejecución
# Adicional genero un identificador unico para cada conversacion y que no se choquen entre si
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(np.random.randint(1, 500)).zfill(5)

if "memory" not in st.session_state:
    st.session_state["memory"] = MemorySaver()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Acá la idea es mostrar en el mensaje quien lo dijo
# Y en formato bonito que fue lo que dijo
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

with st.container():
    # Ahora, cuando yo usuario escriba algo
    # Eso que escribo lo muestro como chat_message con el nombre que le asigne
    # Si no hay nada escrito no pasa nada
    if prompt := st.chat_input("Escribe aquí..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Y agregamos la respuesta del bicho
        # Aquí es donde ocurre la magia
        # Lista de herramientas
        tools = [send_user_email, send_area_email, generate_case_number, get_transaction, generate_image, store_case, get_case_date]
        agent_executor = create_react_agent(model_gen, tools, checkpointer=st.session_state["memory"])
        config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
        messages = [
            SystemMessage(content=template),
            HumanMessage(content=prompt)
        ]
        response = agent_executor.invoke({"messages": messages}, config)
        response = response["messages"][-1].content
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Boton de descarga de las imagenes
        if "tu comprobante" in response.lower():
            cus = re.findall(r"\d{10}", response)[0]
            print(cus)
            with open(os.path.join(FOLDER, f"{cus}.png"), "rb") as file:
                btn = st.download_button(
                    label="Descargar imagen",
                    data=file,
                    file_name=f"comprobante-{cus}.png",
                    mime="image/png",
                )

# Acá voy a dejar un espacio para que muestre los casos almacenados en la base de datos
with st.container():
    with st.expander("**Base de datos de casos generados**"):
        st.text("Aquì puedes ver los casos que ha registrado ANAVI. Al oprimir el botón, la BD se actualizará automáticamente.")
        if st.button("Mostrar BD"):
            conn = sqlite3.connect(
                os.path.join(FOLDER, "case_db.db")
            )
            cursor = conn.cursor()
            df = pd.read_sql_query("SELECT * FROM casos", conn)
            conn.close()
            st.dataframe(df)