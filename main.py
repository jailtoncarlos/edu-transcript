"""
main.py - Ponto de entrada do edu-transcript

Exemplo de uso:
    python main.py

Ou em Google Colab (após instalar dependências):
    !pip install playwright
    !playwright install chromium
    !playwright install-deps chromium
    %run main.py
"""

import asyncio
from edu_transcript import FSLTranscriptor, UninassauTranscriptor

# =============================================================
# Configuração FSL (Faculdade Sírio-Libanês)
# =============================================================
FSL_EMAIL = "seu_email@exemplo.com"
FSL_PASSWORD = "sua_senha"

FSL_DISCIPLINE_URLS = [
    "https://campusdigital.faculdadesiriolibanes.org.br/courses/49/discipline/20738/period/35?index=0",
    "https://campusdigital.faculdadesiriolibanes.org.br/courses/49/discipline/20338/period/35?index=0",
]

# =============================================================
# Configuração UNINASSAU (usar cookies — reCAPTCHA bloqueia headless)
# =============================================================
# Exporte os cookies após login manual em https://campusdigital.uninassau.edu.br
# Formato: lista de dicts com keys: name, value, domain, path
UNINASSAU_COOKIES = [
    # {"name": "session", "value": "...", "domain": ".uninassau.edu.br", "path": "/"},
]

UNINASSAU_DISCIPLINE_URLS = [
    "https://campusdigital.uninassau.edu.br/courses/5046/discipline/316?index=1",
]


# =============================================================
# Execução
# =============================================================

async def run_fsl():
    transcriptor = FSLTranscriptor(email=FSL_EMAIL, password=FSL_PASSWORD)
    zip_path = await transcriptor.run(FSL_DISCIPLINE_URLS, zip_name="fsl_transcricoes.zip")
    print(f"FSL concluído: {zip_path}")


async def run_uninassau():
    transcriptor = UninassauTranscriptor(cookies=UNINASSAU_COOKIES)
    zip_path = await transcriptor.run(UNINASSAU_DISCIPLINE_URLS, zip_name="uninassau_transcricoes.zip")
    print(f"UNINASSAU concluído: {zip_path}")


if __name__ == "__main__":
    # Escolha qual plataforma executar:
    asyncio.run(run_fsl())
    # asyncio.run(run_uninassau())
