FROM node:22-alpine

WORKDIR /srv/news/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG NEWS_API_INTERNAL_URL=http://api:8001
ENV NEWS_API_INTERNAL_URL=${NEWS_API_INTERNAL_URL}
RUN npm run build

EXPOSE 3101
CMD ["npm", "run", "start"]
