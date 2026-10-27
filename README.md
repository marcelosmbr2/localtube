# LocalTube

Aplicação desktop em Python com PySide6 (Qt Widgets) para baixar e converter mídia localmente:

- **Baixar**: cole um link, veja todos os formatos disponíveis (via yt-dlp) e escolha qualidade, contêiner, pasta, nome, miniatura, metadados, legendas, capítulos e intervalo. "Copiar comando" gera o comando equivalente do yt-dlp.
- **Fila**: downloads simultâneos com progresso, velocidade, pausar/retomar, tentar de novo e limite de banda.
- **Converter**: arraste arquivos e converta com o ffmpeg para MP4, MKV, WEBM, MOV, GIF, MP3, M4A, WAV, FLAC ou OGG. A saída fica ao lado do original.
- **Biblioteca**: os arquivos da pasta de downloads, com filtro e ordenação.
- **Configurações**: salvas automaticamente; inclui atualização do yt-dlp e caminho do ffmpeg.
- Paleta de comandos (`Ctrl+K`), atalhos `Ctrl+1`–`Ctrl+4` e `Ctrl+,`, monitor da área de transferência e notificações.

Salve apenas conteúdo que seja seu ou que você tenha permissão para baixar.

## Requisitos

- Python 3.11 ou mais novo
- ffmpeg e ffprobe — no Windows: `winget install --id Gyan.FFmpeg -e`

## Configuração

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Execução

```powershell
python -m localtube
# ou
localtube
```

## Testes

```powershell
python -m pytest
```

As fontes Inter e JetBrains Mono são distribuídas sob a SIL Open Font License (veja `src/localtube/resources/fonts`).
