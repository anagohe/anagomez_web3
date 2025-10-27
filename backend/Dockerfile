# Usa una imagen oficial de Python
FROM python:3.12-slim
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /code

# Copia el archivo de requerimientos y los instala
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copia el resto del código de tu aplicación
COPY ./app /code/app
COPY ./tests /code/tests 
COPY ./pytest.ini /code/pytest.ini 

# Expone el puerto 8000 y corre la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]