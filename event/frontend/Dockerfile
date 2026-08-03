FROM node:22-alpine AS build

WORKDIR /app
RUN corepack enable

ENV npm_config_fetch_retries=10 \
    npm_config_fetch_retry_mintimeout=10000 \
    npm_config_fetch_retry_maxtimeout=120000 \
    npm_config_fetch_timeout=600000

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN for attempt in 1 2 3 4 5; do \
      corepack install --global pnpm@11.9.0 && break; \
      if [ "$attempt" = 5 ]; then exit 1; fi; \
      sleep 2; \
    done
RUN --mount=type=cache,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && \
    pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
