# Astoka web — Next.js 14 App Router.
# Dev mode (hot reload) for MVP; standalone build comes in Sprint 9.

FROM node:20-alpine

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

COPY package.json ./
RUN pnpm install --no-frozen-lockfile

COPY . .

EXPOSE 3000

CMD ["pnpm", "dev"]
