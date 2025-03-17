# nginx/Dockerfile

FROM nginx:stable-alpine

RUN apk add --update openssl

RUN mkdir /etc/nginx/ssl \
&& chmod 700 /etc/nginx/ssl \
&& openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/example.key -out /etc/nginx/ssl/example.crt -subj "/C=/ST=/L=/O=/CN="

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.local.conf /etc/nginx/conf.d

EXPOSE 80
EXPOSE 443