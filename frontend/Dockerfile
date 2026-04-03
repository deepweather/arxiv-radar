FROM node:20-alpine AS build

ARG VITE_IMPRINT_COMPANY
ARG VITE_IMPRINT_REPRESENTATIVE
ARG VITE_IMPRINT_ADDRESS
ARG VITE_IMPRINT_EMAIL
ARG VITE_IMPRINT_PHONE
ARG VITE_IMPRINT_REGISTER
ARG VITE_IMPRINT_VAT_ID

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

EXPOSE 80
