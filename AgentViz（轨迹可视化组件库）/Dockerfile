FROM node:22-slim
WORKDIR /app
RUN npm install -g pnpm
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY packages/core/package.json packages/core/
COPY packages/react/package.json packages/react/
COPY packages/transform/package.json packages/transform/
COPY packages/vanilla/package.json packages/vanilla/
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install
COPY . .
EXPOSE 6006
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:6006 || exit 1
CMD ["pnpm", "storybook", "--host", "0.0.0.0"]
