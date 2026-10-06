FROM node:22-alpine AS base

WORKDIR /app

COPY package.json package-lock.json nx.json tsconfig.base.json ./
COPY apps/hermes/package.json ./apps/hermes/
COPY apps/hermes-e2e/package.json ./apps/hermes-e2e/
COPY libs/feature-map/package.json ./libs/feature-map/
COPY libs/shared/ui-components/package.json ./libs/shared/ui-components/
COPY libs/shared/util-types/package.json ./libs/shared/util-types/
COPY libs/shared/utils/package.json ./libs/shared/utils/

RUN --mount=type=cache,target=/root/.npm npm ci

COPY libs/ ./libs
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