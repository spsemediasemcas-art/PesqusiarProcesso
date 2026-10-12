"""
teste_nuvem.py
--------------
Teste de conectividade para rodar na nuvem (Railway, VPS, etc.).

Responde UMA pergunta: o Cloudflare do SEI bloqueia este IP de datacenter?

Etapa 1: abre a página de pesquisa e verifica se veio bloqueio.
Etapa 2 (bônus): roda uma busca completa com o fluxo de produção
         (buscar_link + SVM treinado nos rótulos).

Uso:
    python teste_nuvem.py [numero_processo]

Saída (procure a linha VEREDITO):
    VEREDITO: PASSOU    - o IP passa e a busca funciona
    VEREDITO: BLOQUEADO - Cloudflare barrou este IP (precisa proxy residencial)
    VEREDITO: IP PASSOU - passa, mas o captcha não resolveu (não bloqueia o deploy)
"""

import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))

from buscar_link_processo import (  # noqa: E402
    URL_PESQUISA, _carregar_reconhecedor, buscar_link,
)
from playwright.sync_api import sync_playwright  # noqa: E402

PROCESSO_TESTE = sys.argv[1] if len(sys.argv) > 1 else "25101.006859/2026"
ORGAO = "SEMCAS"


def veredito(texto, ok):
    print("\n" + "=" * 62)
    print(f"VEREDITO: {texto}")
    print("=" * 62)
    sys.exit(0 if ok else 1)


def ip_passa_cloudflare():
    """Etapa 1: só verifica se a página carrega sem bloqueio."""
    with sync_playwright() as p:
        print("[teste] lançando Chromium...", flush=True)
        browser = p.chromium.launch(headless=False, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        print("[teste] Chromium no ar, abrindo página...", flush=True)
        try:
            page = browser.new_context(
                viewport={"width": 1366, "height": 800}).new_page()
            page.goto(URL_PESQUISA, wait_until="domcontentloaded")
            page.wait_for_selector("#txtProtocoloPesquisa", timeout=45000)
            titulo = page.title()
            corpo = (page.locator("body").inner_text() or "")[:400]
            print(f"[teste] título da página: {titulo[:80]!r}")

            if ("cloudflare" in titulo.lower()
                    or "blocked" in corpo.lower()
                    or "attention required" in titulo.lower()):
                print(f"[teste] corpo: {corpo[:200]!r}")
                return "bloqueado"

            if page.locator("#txtProtocoloPesquisa").count() == 0:
                print(f"[teste] corpo inesperado: {corpo[:200]!r}")
                return "estranho"

            return "ok"
        finally:
            try:
                browser.close()
            except Exception:
                pass


def main():
    import time
    t0 = time.time()
    print(f"[teste] importando dependências (cv2/sklearn/pkl 52MB)...", flush=True)
    modelo, templates = _carregar_reconhecedor()
    print(f"[teste] dependências prontas em {time.time() - t0:.0f}s", flush=True)
    print(f"[teste] reconhecedor: {'SVM' if modelo is not None else 'templates'}", flush=True)
    print(f"[teste] processo de teste: {PROCESSO_TESTE}", flush=True)

    resultado = ip_passa_cloudflare()
    if resultado == "bloqueado":
        veredito("BLOQUEADO - Cloudflare barrou este IP "
                 "(precisa proxy residencial)", False)
    if resultado == "estranho":
        veredito("PÁGINA ESTRANHA - nem bloqueio nem formulário "
                 "(link expirado?)", False)

    print("[teste] formulário carregou - IP passou pelo Cloudflare!")

    # Etapa 2 (bônus): busca completa pelo fluxo de produção, que recarrega
    # o captcha pelo botão do SEI a cada erro.
    print("[teste] rodando busca completa com o fluxo de produção...")
    url = buscar_link(PROCESSO_TESTE, orgao=ORGAO, oculto=True,
                      max_tentativas=4,
                      ao_progresso=lambda m: print(f"[teste] {m}"))
    if url:
        veredito("PASSOU - o IP desta máquina consegue buscar no SEI "
                 "(captcha resolvido e processo encontrado)", True)
    veredito("IP PASSOU (formulário carregou sem bloqueio), mas o captcha "
             "não foi resolvido em 4 tentativas — a leitura do SVM errou; "
             "para o deploy isso não bloqueia", True)


if __name__ == "__main__":
    main()
