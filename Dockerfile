FROM node:18-alpine AS base

# Install pnpm via corepack (built into Node.js 18)
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app

# Copy workspace manifests
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY tsconfig.json tsconfig.base.json ./

# Copy all package manifests (needed for pnpm workspace resolution)
COPY lib/db/package.json              ./lib/db/
COPY lib/api-zod/package.json         ./lib/api-zod/
COPY lib/api-client-react/package.json ./lib/api-client-react/
COPY lib/api-spec/package.json        ./lib/api-spec/
COPY artifacts/api-server/package.json ./artifacts/api-server/
COPY scripts/package.json             ./scripts/

# Install ALL workspace dependencies
RUN pnpm install --frozen-lockfile

# Copy source
COPY lib/      ./lib/
COPY artifacts/api-server/ ./artifacts/api-server/
COPY tsconfig.base.json ./

# Build lib declarations
RUN pnpm run typecheck:libs

# Build api-server bundle
RUN pnpm --filter @workspace/api-server run build

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM node:18-alpine AS runtime

WORKDIR /app

COPY --from=base /app/artifacts/api-server/dist ./artifacts/api-server/dist
COPY --from=base /app/node_modules              ./node_modules
COPY --from=base /app/artifacts/api-server/node_modules ./artifacts/api-server/node_modules

ENV NODE_ENV=production
ENV PORT=8080

EXPOSE 8080

CMD ["node", "--enable-source-maps", "artifacts/api-server/dist/index.mjs"]
