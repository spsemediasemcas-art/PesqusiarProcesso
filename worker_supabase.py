"""
worker_supabase.py
------------------
Worker de busca com captcha para rodar no Railway (container 24h).

Fluxo:
  1. Lê a tabela `buscas` do Supabase por linhas com status 'pendente'.
  2. Marca como 'rodando', roda o buscar_link (SVM treinado nos rótulos).
  3. Escreve o status final: 'achou' (com a URL) / 'nao_encontrado' / 'erro'.
  4. Se achou, insere o processo na tabela `processos`.

Variáveis de ambiente (definir no painel do Railway):
  SUPABASE_URL        -> https://xxxx.supabase.co
  SUPABASE_KEY        -> service_role key (bypassa RLS; NUNCA a anon key no server)
  ORGAO               -> SEMCAS (padrão)
  INTERVALO_SEGUNDOS  -> 20 (padrão)

O captcha é resolvido por sei_captcha_pipeline + modelo_svm.pkl, ambos
copiados na imagem (ou montados por volume para atualizar sem rebuild).
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client  # noqa: E402

INTERVALO = int(os.environ.get("INTERVALO_SEGUNDOS", "20"))
ORGAO = os.environ.get("ORGAO", "SEMCAS")
MAX_TENTATIVAS = int(os.environ.get("MAX_TENTATIVAS", "8"))


def log(msg):
    print(f"[worker {datetime.now():%H:%M:%S}] {msg}", flush=True)


def criar_cliente():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Defina SUPABASE_URL e SUPABASE_KEY nas variáveis do Railway.")
    return create_client(url, key)


def processar_busca(sb, busca):
    """Executa uma busca pendente e devolve o estado final."""
    bid = busca["id"]
    numero = busca["numero"]
    apelido = busca.get("apelido")
    passos = []

    def ao_progresso(msg):
        passos.append(msg)
        try:
            sb.table("buscas").update({"passos": passos[-6:]}).eq("id", bid).execute()
        except Exception:
            pass

    log(f"buscando {numero} (id={bid})")
    sb.table("buscas").update({
        "status": "rodando",
        "iniciado_em": datetime.now(timezone.utc).isoformat(),
        "passos": [],
    }).eq("id", bid).execute()

    from buscar_link_processo import buscar_link
    url = None
    for chance in (1, 2):
        try:
            url = buscar_link(numero, orgao=ORGAO, oculto=True,
                              max_tentativas=MAX_TENTATIVAS,
                              ao_progresso=ao_progresso, verbose=False)
            break
        except Exception as e:
            log(f"{numero}: tentativa {chance} falhou -> {e}")
            if chance == 2:
                sb.table("buscas").update({
                    "status": "erro",
                    "erro": f"Falha na busca: {e}",
                    "finalizado_em": datetime.now(timezone.utc).isoformat(),
                }).eq("id", bid).execute()
                return "erro"
            time.sleep(2)

    agora = datetime.now(timezone.utc).isoformat()
    if not url:
        log(f"{numero}: não encontrado")
        sb.table("buscas").update({
            "status": "nao_encontrado",
            "erro": "Processo não encontrado (ou captcha não resolvido).",
            "finalizado_em": agora,
        }).eq("id", bid).execute()
        return "nao_encontrado"

    log(f"{numero}: achou -> {url}")
    # cadastra o processo (ignora se a URL já existir)
    try:
        sb.table("processos").upsert(
            {"url": url, "apelido": apelido, "numero": numero,
             "criado_em": agora},
            on_conflict="url", ignore_duplicates=True).execute()
    except Exception as e:
        log(f"aviso ao cadastrar processo: {e}")

    sb.table("buscas").update({
        "status": "achou",
        "url": url,
        "finalizado_em": agora,
    }).eq("id", bid).execute()
    return "achou"


def main():
    sb = criar_cliente()
    log("worker iniciado — aguardando buscas pendentes no Supabase...")
    while True:
        try:
            pendentes = (sb.table("buscas")
                         .select("*")
                         .eq("status", "pendente")
                         .order("criado_em")
                         .limit(1)
                         .execute())
            if pendentes.data:
                processar_busca(sb, pendentes.data[0])
            else:
                time.sleep(INTERVALO)
        except KeyboardInterrupt:
            log("encerrado pelo operador")
            break
        except Exception as e:
            log(f"erro no laço principal: {e}")
            time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
