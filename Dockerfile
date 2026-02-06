FROM node:20-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg python3 python3-pip \
    && pip3 install --no-cache-dir yt-dlp \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json* ./
RUN npm install --production

COPY . .

EXPOSE 5000

CMD ["node", "server.js"]
