# Deploy: busca automática de processos no SEI (com captcha) no Railway
# + dados no Supabase
# ============================================================================
# Sim, é possível — e o Railway é a melhor opção para o worker de busca:
# ele roda container 24h com Chromium de verdade, ao contrário do Supabase
# (não roda navegador) e do GitHub Actions (efêmero, IP de datacenter que o
# Cloudflare barra).
#
# Arquitetura:
#   painel/APP  -> insere linha em `buscas` (status 'pendente') no Supabase
#   Railway     -> worker_supabase.py consome a fila, resolve o captcha
#                  (SVM treinado nos rótulos), devolve a URL e cadastra
#                  o processo em `processos`
#
# ------------------------------------------------------------------ 1. Supabase
# 1. Crie um projeto em https://supabase.com (grátis para começar).
# 2. SQL Editor -> cole o conteúdo de supabase_schema.sql -> Run.
# 3. Settings -> API: copie a Project URL e a service_role key
#    (NUNCA a anon key no worker — a service_role bypassa RLS).
#
# ------------------------------------------------------------------ 2. Railway
# 1. Suba esta pasta num repositório Git (GitHub/GitLab).
#    .gitignore já exclui o que não deve ir (modelo, db, prints).
# 2. Em https://railway.app -> New Project -> Deploy from GitHub repo.
# 3. Variables -> adicione:
#      SUPABASE_URL   = https://xxxx.supabase.co
#      SUPABASE_KEY   = service_role key
#      ORGAO          = SEMCAS
#      INTERVALO_SEGUNDOS = 20
# 4. Deploy. O container instala tudo, treina o SVM com os rótulos
#    atuais e fica em loop esperando buscas.
# 5. Logs: "worker iniciado — aguardando buscas pendentes..."
#
# ------------------------------------------------------ 3. Usar (qualquer app)
# Painel web, script, celular — basta inserir na fila:
#   supabase.table('buscas').insert({'numero': '25101.006859/2026',
#                                    'apelido': 'Casa do Bairro'}).execute()
# e acompanhar o status em `buscas` (pendente -> rodando -> achou).
# O worker salva a URL e cadastra o processo sozinho em `processos`.
#
# ------------------------------------------------------- 4. Melhorar o captcha
# Cada acerto no worker salva um rótulo novo (captchas/ + rotulos.txt).
# No container isso some no restart — para persistir:
#   - monte um volume do Railway em /app/captchas e /app/rotulos.txt, ou
#   - depois de algumas buscas, rode o retreino e faça upload do novo
#     modelo_svm.pkl para o volume /app/modelo_svm.pkl.
# Na sua máquina: python sei_captcha_pipeline.py --treinar
#
# --------------------------------------------------------- 5. Se o Cloudflare
# O worker roda Chromium headful dentro de Xvfb (é o que passa pelo
# Cloudflare). Se um dia o Railway for bloqueado por IP de datacenter,
# o caminho é proxy residencial — aí me chama que eu adapto.
