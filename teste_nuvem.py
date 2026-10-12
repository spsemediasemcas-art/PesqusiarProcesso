"""
teste_nuvem.py
--------------
Teste de conectividade para rodar na nuvem (Railway, VPS, etc.).

Responde UMA pergunta: o Cloudflare do SEI bloqueia este IP de datacenter?

Uso:
    python teste_nuvem.py [numero_processo]

Saída (procure a linha VEREDITO):
    VEREDITO: PASSOU  - o IP desta máquina consegue buscar no SEI
    VEREDITO: BLOQUEADO - Cloudflare barrou este IP (precisa proxy residencial)
"""

import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))

from buscar_link_processo import (  # noqa: E402
    URL_PESQUISA, LINKS_PROCESSO, _carregar_reconhecedor, _resolver_captcha,
    _preparar_formulario,
)
from playwright.sync_api import sync_playwright  # noqa: E402

PROCESSO_TESTE = sys.argv[1] if len(sys.argv) > 1 else "25101.006859/2026"
ORGAO = "SEMCAS"


def veredito(texto, ok):
    print("\n" + "=" * 62)
    print(f"VEREDITO: {texto}")
    print("=" * 62)
    sys.exit(0 if ok else 1)


def main():
    modelo, templates = _carregar_reconhecedor()
    print(f"[teste] reconhecedor: {'SVM' if modelo is not None else 'templates'}")
    print(f"[teste] processo de teste: {PROCESSO_TESTE}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            page = browser.new_context(
                viewport={"width": 1366, "height": 800}).new_page()
            try:
                page.goto(URL_PESQUISA, wait_until="networkidle")
            except Exception as e:
                print(f"[teste] erro ao abrir a página: {e}")
                veredito(f"FALHA DE REDE - {e}", False)

            titulo = page.title()
            corpo = (page.locator("body").inner_text() or "")[:400]
            print(f"[teste] título da página: {titulo[:80]!r}")

            if ("cloudflare" in titulo.lower()
                    or "blocked" in corpo.lower()
                    or "attention required" in titulo.lower()):
                print(f"[teste] corpo: {corpo[:200]!r}")
                veredito("BLOQUEADO - Cloudflare barrou este IP "
                         "(precisa proxy residencial)", False)

            if page.locator("#txtProtocoloPesquisa").count() == 0:
                print(f"[teste] corpo inesperado: {corpo[:200]!r}")
                veredito("PÁGINA ESTRANHA - nem bloqueio nem formulário "
                         "(link expirado?)", False)

            print("[teste] formulário carregou - IP passou pelo Cloudflare!")

            # O que interessa neste teste é o IP. O captcha entra como
            # bônus: até 4 tentativas, pois uma leitura fraca (conf < 0.4)
            # pode errar e o SEI recusa em silêncio.
            _preparar_formulario(page, PROCESSO_TESTE, ORGAO)
            captcha_ok = False
            for tent in range(1, 5):
                captcha_el = page.locator("#imgCaptcha, #imgInfraCaptcha")
                if captcha_el.count() == 0:
                    break
                result = _resolver_captcha(
                    captcha_el.first.screenshot(), modelo, templates)
                print(f"[teste] tentativa {tent}: leu {result['codigo']!r} "
                      f"(conf {result['confianca']:.2f})")
                page.fill("#txtInfraCaptcha", result["codigo"][:6])
                page.click("#sbmPesquisar")
                page.wait_for_timeout(5000)
                if page.locator(LINKS_PROCESSO).count() > 0:
                    captcha_ok = True
                    break
                # SEI recusou: gera captcha novo e tenta de novo
                _preparar_formulario(page, PROCESSO_TESTE, ORGAO)
                page.wait_for_timeout(1000)

            if captcha_ok:
                veredito("PASSOU - o IP desta máquina consegue buscar no SEI "
                         "(captcha resolvido e processo encontrado)", True)
            veredito("IP PASSOU (formulário carregou sem bloqueio), mas o "
                     "captcha não foi resolvido em 4 tentativas — prove seu "
                     "máquina, o SVM precisa de mais rótulos; para o deploy "
                     "isso não bloqueia", True)
        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
