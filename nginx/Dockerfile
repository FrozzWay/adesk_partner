FROM nginx:1.23.0-alpine

RUN rm /etc/nginx/conf.d/default.conf
RUN apk add certbot certbot-nginx
COPY nginx.conf /etc/nginx/conf.d