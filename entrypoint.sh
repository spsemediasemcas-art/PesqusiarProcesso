#!/bin/sh
# Entrypoint do container.
#   MODO=teste (padrão) -> roda teste_nuvem.py uma vez e sai
#   MODO=worker          -> roda worker_supabase.py em loop (precisa das
#                           variáveis SUPABASE_URL e SUPABASE_KEY)
#
# Xvfb é iniciado manualmente (sem xvfb-run, que trava esperando readiness
# em alguns containers). DISPLAY :99 é fixo.

# O Railway pode reiniciar o processo reutilizando o /tmp do ciclo anterior;
# um lock velho do Xvfb faz o servidor novo morrer com "Server is already
# active" e o Chromium só veria "Missing X server". Limpa antes de subir.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null

echo "[entrypoint] iniciando Xvfb no display :99..."
Xvfb :99 -screen 0 1366x800x24 -ac &
XVFB_PID=$!
export DISPLAY=:99

# Espera o socket do X aparecer de verdade (até 10s) antes de seguir —
# sleep fixo é frágil: se o Xvfb morrer, o Python só descobre no launch.
i=0
while [ $i -lt 20 ]; do
    [ -e /tmp/.X11-unix/X99 ] && break
    sleep 0.5
    i=$((i + 1))
done
if [ -e /tmp/.X11-unix/X99 ]; then
    echo "[entrypoint] Xvfb rodando (pid $XVFB_PID, DISPLAY=$DISPLAY)"
else
    echo "[entrypoint] ATENCAO: socket do Xvfb nao apareceu em 10s"
fi

# garante que o Xvfb morra junto com este processo (nao deixa lock velho)
trap "kill $XVFB_PID 2>/dev/null" EXIT

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
