FROM python:3.8.13-alpine3.15
LABEL maintainer="lty@luotianyi.dev"

COPY src /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD [ "python3" "/app/vsingerd.py" ]
