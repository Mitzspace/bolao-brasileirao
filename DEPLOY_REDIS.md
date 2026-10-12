# Redis não é necessário para a implantação gratuita

O Flask-Limiter funciona em memória com **um único worker**, mantendo os limites
de login/cadastro e requisições. Configure RATELIMIT_STORAGE_URI=memory:// e
RATELIMIT_SINGLE_PROCESS=true. O Gunicorn fornecido usa um worker com threads.
Contadores reiniciam com o processo; não são dados de usuários ou bolões.

Redis foi removido das dependências e do Blueprint. Não crie Key Value no Render.
As variáveis antigas ainda são reconhecidas para compatibilidade, mas o driver
Redis não é instalado pelo deploy gratuito. Remova REDIS_URL e a variável antiga
RATELIMIT_STORAGE_URL do painel. Não aumente workers/réplicas sem revisar o limiter.

O guia vigente é [DEPLOY.md](DEPLOY.md): Render Free + Neon Free, sem disco pago,
sem banco Render com expiração e sem contratação de serviços.
