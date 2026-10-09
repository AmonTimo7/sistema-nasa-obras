# Regera a demonstracao estatica (pasta docs/, publicada no GitHub Pages).
# Usa um banco DESCARTAVEL so com dados ficticios: o banco de trabalho nao e tocado.
# Login da demonstracao: .\publicar_demo.ps1 -Usuario <usuario> -Senha <senha>
param([string]$Usuario = "", [string]$Senha = "")
$ErrorActionPreference = "Stop"
$env:SQLITE_PATH = Join-Path $env:TEMP "nasa-demo.sqlite3"
if (Test-Path $env:SQLITE_PATH) { Remove-Item $env:SQLITE_PATH }
.venv\Scripts\python manage.py migrate -v 0
.venv\Scripts\python manage.py dados_exemplo
.venv\Scripts\python manage.py gerar_site_estatico --saida docs --base /sistema-nasa-obras/ --repositorio https://github.com/AmonTimo7/sistema-nasa-obras --usuario $Usuario --senha $Senha
Remove-Item Env:SQLITE_PATH
Write-Host "Pronto. Confira e publique: git add docs; git commit -m 'Atualiza a demonstracao'; git push"
