FROM node:20-alpine

WORKDIR /app


COPY package.json ./
RUN npm install --omit=dev && npm cache clean --force

COPY index.html vite.config.js ./
COPY src ./src
COPY public ./public
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN addgroup -S ctf \
    && adduser -S ctf -G ctf \
    && chmod +x /usr/local/bin/docker-entrypoint.sh \
    && chown -R ctf:ctf /app

EXPOSE 5173

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
