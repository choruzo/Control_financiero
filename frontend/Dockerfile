FROM node:20-alpine

WORKDIR /app

# Instalar dependencias (capa cacheada independiente del código fuente)
COPY package.json ./
RUN npm install

# El código fuente se monta como volume en dev → HMR funciona
# Las node_modules viven en la imagen para evitar conflictos Linux/Windows

EXPOSE 3000

CMD ["npm", "run", "dev"]
