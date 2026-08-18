FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json nx.json tsconfig.base.json ./
COPY apps/hermes/package.json ./apps/hermes/

RUN npm ci

COPY apps/hermes/ ./apps/hermes

EXPOSE 4200

CMD ["npx", "nx", "dev", "hermes"]