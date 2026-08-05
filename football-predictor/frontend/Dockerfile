# Dev-oriented image: runs the Vite dev server with the /api proxy.
FROM node:22-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173
# Proxy target is the backend service on the compose network.
ENV VITE_API_TARGET=http://backend:8000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
