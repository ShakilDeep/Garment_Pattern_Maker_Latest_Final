FROM rust:1-bookworm AS wasm
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN rustup target add wasm32-unknown-unknown \
    && cargo build --release --lib --target wasm32-unknown-unknown

FROM node:22-bookworm AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web ./
COPY --from=wasm /app/target/wasm32-unknown-unknown/release/patternforge.wasm ./public/patternforge.wasm
RUN npm run build

FROM nginx:1-alpine
COPY --from=web /app/web/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV PORT=10000
EXPOSE 10000
