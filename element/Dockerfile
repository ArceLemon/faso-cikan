# Client web Faso Cikan : Element Web officiel, étendu et adapté.
#
# 1. on récupère le code source d'Element à une version figée ;
# 2. on ajoute nos fichiers (src/faso) et on applique nos patchs ;
# 3. on construit, puis on remplace l'application dans l'image officielle d'Element.

ARG ELEMENT_VERSION=v1.12.32

FROM node:24-bookworm AS construction
ARG ELEMENT_VERSION

RUN npm install -g pnpm@11.23.0

WORKDIR /src
RUN git clone --depth 1 --branch "${ELEMENT_VERSION}" https://github.com/element-hq/element-web.git .

# Dépendances : couche mise en cache tant que la version d'Element ne change pas.
# Le magasin pnpm est conservé entre deux constructions, et les connexions lentes tolérées.
RUN --mount=type=cache,id=faso-pnpm,target=/pnpm-store \
    pnpm config set store-dir /pnpm-store \
    && pnpm config set fetch-timeout 600000 \
    && pnpm config set fetch-retries 6 \
    && pnpm config set network-concurrency 8 \
    && pnpm install --frozen-lockfile

# Ajouts et patchs Faso Cikan
COPY src/faso/ apps/web/src/faso/
COPY src/faso/_Faso.pcss apps/web/res/css/views/faso/_Faso.pcss
COPY patches/ /patches/
RUN git apply --verbose /patches/element-web/*.patch \
    && cd "$(realpath apps/web/node_modules/matrix-js-sdk)" \
    && for p in /patches/matrix-js-sdk/*.patch; do patch -p1 --forward < "$p"; done

ENV NODE_OPTIONS=--max-old-space-size=4096
RUN VERSION="${ELEMENT_VERSION}-faso" pnpm --dir apps/web build

FROM vectorim/element-web:${ELEMENT_VERSION}
USER root
RUN rm -rf /app && mkdir /app
COPY --from=construction /src/apps/web/webapp /app
USER nginx
