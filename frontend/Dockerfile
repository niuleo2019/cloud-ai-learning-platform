FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install
RUN chmod -R a+x node_modules/.bin

COPY . .

EXPOSE 5173

CMD ["node", "node_modules/vite/bin/vite.js", "--host", "0.0.0.0"]
