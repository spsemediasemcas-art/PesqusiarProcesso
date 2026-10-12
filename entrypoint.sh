#!/bin/sh
# Entrypoint do container.
#   MODO=teste (padrão) -> roda teste_nuvem.py uma vez e sai
#   MODO=worker          -> roda worker_supabase.py em loop (precisa das
#                           variáveis SUPABASE_URL e SUPABASE_KEY)
#
# Xvfb é iniciado manualmente (sem xvfb-run, que trava esperando readiness
# em alguns containers). DISPLAY :99 é fixo.
echo "[entrypoint] iniciando Xvfb no display :99..."
Xvfb :99 -screen 0 1366x800x24 -ac &
XVFB_PID=$!
sleep 2
export DISPLAY=:99
echo "[entrypoint] Xvfb rodando (pid $XVFB_PID, DISPLAY=$DISPLAY)"

MODO="${MODO:-teste}"
if [ "$MODO" = "worker" ]; then
    echo "[entrypoint] modo worker (loop infinito)"
    exec python -u worker_supabase.py
fi

echo "[entrypoint] modo teste (one-shot, limite 300s)"
timeout 300 python -u teste_nuvem.py
CODE=$?
echo "[entrypoint] teste terminou com codigo $CODE"
exit $CODE
