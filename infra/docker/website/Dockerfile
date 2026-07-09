# The public website: a stock nginx image with our static files copied in.
# Build context is the repo root (see docker-compose.yml), so the COPY path
# is relative to the repo, not to this Dockerfile.
FROM nginx:alpine

COPY apps/website/ /usr/share/nginx/html/
# The shared design system: the page links /design/index.css.
COPY design/ /usr/share/nginx/html/design/
