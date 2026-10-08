FROM python:3.13-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY static static
COPY ml ml
# Entrena el modelo local durante la construccion de la imagen (unos segundos)
RUN python -m ml.train
ENV CTF_DB=/data/ctf.db
VOLUME /data
EXPOSE 8000
# Render y Railway indican el puerto en $PORT; detrás de su proxy, confía en X-Forwarded-*
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips="*"
