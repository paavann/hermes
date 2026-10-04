FROM node:22-alpine AS base

WORKDIR /app

COPY package.json package-lock.json nx.json tsconfig.base.json ./
COPY apps/hermes/package.json ./apps/hermes/
COPY libs/ ./libs

RUN npm ci

COPY apps/hermes/ ./apps/hermes

# development target (vite dev server).
FROM base AS development
EXPOSE 4200
CMD ["npx", "nx", "dev", "hermes"]

# production target (compiled bundle served via react-router-serve).
FROM base AS production
RUN npx nx build hermes
ENV PORT=4200
EXPOSE 4200
CMD ["npx", "react-router-serve", "./apps/hermes/build/server/index.js"]