FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY tsconfig.json ./
COPY prisma/ ./prisma/
RUN npx prisma generate
COPY src/ ./src/
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
RUN addgroup --system --gid 1001 quantive && adduser --system --uid 1001 quantive
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/prisma ./prisma
COPY package.json ./
USER quantive
ENV NODE_ENV=production
EXPOSE 4000
CMD ["node", "dist/server.js"]
