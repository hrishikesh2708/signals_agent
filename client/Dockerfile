FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY next.config.ts tsconfig.json postcss.config.mjs next-env.d.ts ./
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]
