# Usa una imagen base de Node.js
FROM node:20-alpine
RUN apk update && apk upgrade

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el package.json para instalar las dependencias
COPY package*.json ./
RUN npm install

# Copia el resto del código de la aplicación
COPY . .

# Expone el puerto 3000 que usa React
EXPOSE 3000

# El comando para iniciar la aplicación
CMD ["npm", "start"]