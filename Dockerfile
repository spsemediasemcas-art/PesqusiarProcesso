FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

# Xvfb: o Chromium roda headful (único modo que passa pelo Cloudflare),
# e num servidor sem monitor isso exige um display virtual.
RUN apt-get update && apt-get install -y --no-install-recommends xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sei_captcha_pipeline.py buscar_link_processo.py worker_supabase.py ./
COPY captchas ./captchas
COPY rotulos.txt ./rotulos.txt

# modelo inicial treinado dentro da imagem (substituível por volume
# montando um modelo_svm.pkl treinado com mais rótulos depois)
RUN if [ ! -f modelo_svm.pkl ]; then \
      python -c "from sei_captcha_pipeline import treinar_modelo; treinar_modelo()" || true; \
    fi

# xvfb-run dá o display virtual; -a escolhe porta livre automaticamente
CMD ["xvfb-run", "-a", "--server-args=-screen 0 1366x800x24", "python", "worker_supabase.py"]
