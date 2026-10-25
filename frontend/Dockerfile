# Development image for the Vite dev server (docker-compose.yml).
# The production web image is built by nginx/Dockerfile.prod instead.
FROM node:22-alpine AS development

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
