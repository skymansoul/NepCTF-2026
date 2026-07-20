FROM python:3.11-slim

RUN pip install --no-cache-dir numpy==1.26.4

WORKDIR /app
COPY server.py index.html search.html upload.html docs.html .

ENV PORT=8080
ENV FLAG="flag{l34ky_v3ct0r_s34rch_1s_n0t_3ncrypt10n}"

EXPOSE 8080
CMD ["python", "server.py"]
