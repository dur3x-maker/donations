FROM node:20-alpine

WORKDIR /app

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY package*.json ./
RUN npm install

COPY . .

RUN test -n "$NEXT_PUBLIC_API_URL"
RUN npm run build

CMD ["npm", "run", "start"]
