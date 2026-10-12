import os

bind = '0.0.0.0:' + os.environ.get('PORT', '8000')
# Limiter em memória: uma instância, um worker; threads compartilham contadores.
workers = 1
worker_class = 'gthread'
threads = 4
timeout = 120
graceful_timeout = 30
accesslog = '-'
# Não registrar query strings, cookies ou cabeçalhos de autenticação.
access_log_format = '%(h)s %(m)s %(U)s %(s)s %(L)s'
errorlog = '-'
capture_output = True
# ProxyFix trata exatamente um salto quando TRUST_PROXY=true.
forwarded_allow_ips = ''
