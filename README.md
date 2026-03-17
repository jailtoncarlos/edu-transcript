# edu-transcript

Extrator automático de transcrições de vídeos em plataformas **UOL Edtech** (Campus Digital FSL, UNINASSAU e similares).

## Funcionalidades

- Extrai transcrições automáticas (legendas) de todos os vídeos de uma disciplina
- Suporte a múltiplas URLs de disciplina em uma única execução
- Arquitetura orientada a objetos com classe base + especializações por plataforma
- Salva cada transcrição como arquivo `.txt` e compacta tudo em um `.zip`
- Funciona em Google Colab e localmente

## Estrutura do Projeto

```
edu-transcript/
├── edu_transcript/
│   ├── __init__.py          # Exporta as classes principais
│   ├── base.py              # Classe abstrata UolEdtechTranscriptor
│   ├── fsl.py               # FSLTranscriptor (Campus Digital FSL)
│   └── uninassau.py         # UninassauTranscriptor (Campus Digital UNINASSAU)
├── main.py                  # Ponto de entrada / exemplo de uso
├── requirements.txt         # Dependências
└── README.md
```

## Instalação

```bash
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium
```

## Uso — Campus Digital FSL

```python
import asyncio
from edu_transcript import FSLTranscriptor

fsl = FSLTranscriptor(
    email="seu_email@fsl.org.br",
    password="sua_senha"
)

asyncio.run(fsl.run([
    "https://campusdigital.faculdadesiriolibanes.org.br/courses/49/discipline/20738/period/35?index=0",
    "https://campusdigital.faculdadesiriolibanes.org.br/courses/49/discipline/20338/period/35?index=0",
]))
```

## Uso — Campus Digital UNINASSAU

O login automático não é possível porque a plataforma usa reCAPTCHA v2.
É necessário exportar os cookies após login manual.

```python
import asyncio
from edu_transcript import UninassauTranscriptor

# Cookies exportados após login manual
cookies = [
    {"name": "session", "value": "...", "domain": ".uninassau.edu.br", "path": "/"},
    # ... outros cookies
]

uninassau = UninassauTranscriptor(cookies=cookies)

asyncio.run(uninassau.run([
    "https://campusdigital.uninassau.edu.br/courses/5046/discipline/316?index=1",
]))
```

## Uso no Google Colab

```python
# Célula 1 — Instalação
!pip install playwright
!playwright install chromium
!playwright install-deps chromium

# Célula 2 — Clone e execução
!git clone https://github.com/jailtoncarlos/edu-transcript.git
%cd edu-transcript

from edu_transcript import FSLTranscriptor
import asyncio

fsl = FSLTranscriptor(email="seu@email.com", password="sua_senha")
await fsl.run(["https://campusdigital.faculdadesiriolibanes.org.br/..."])
```

## Como Funciona

1. **Login** — autentica na plataforma (Cognito para FSL / cookies para UNINASSAU)
2. **Descoberta** — navega pela barra lateral e clica em cada `[data-cy="partLesson"]`
3. **Coleta** — abre o player Vimeo diretamente e coleta as legendas via `postMessage`
4. **Legenda** — ativa a faixa `pt-x-autogen` (gerada automaticamente em português)
5. **Playback** — executa a 2x (velocidade máxima permitida pelo Vimeo)
6. **Deduplicação** — remove cues duplicados preservando a ordem
7. **Exportação** — salva `.txt` por vídeo e gera `.zip` final

## Plataformas Suportadas

| Plataforma | Autenticação | Status |
|---|---|---|
| Campus Digital FSL | AWS Cognito (email/senha) | ✅ Funcionando |
| Campus Digital UNINASSAU | Cookies manuais | ✅ Implementado |

## Extensibilidade

Para adicionar uma nova plataforma, crie uma subclasse de `UolEdtechTranscriptor`:

```python
from edu_transcript.base import UolEdtechTranscriptor

class MinhaPlataformaTranscriptor(UolEdtechTranscriptor):
    BASE_URL = "https://minha-plataforma.edu.br"
    PLATFORM_NAME = "Minha Plataforma"

    async def login(self, context, page):
        # Implemente o login específico da plataforma
        await page.goto(f"{self.BASE_URL}/login")
        await page.fill("#email", self.email)
        await page.fill("#password", self.password)
        await page.click("button[type=submit]")
        await page.wait_for_url(f"{self.BASE_URL}/**")
```

## Dependências

- [Playwright](https://playwright.dev/python/) — automação de browser
- Python 3.10+

## Licença

MIT
# edu-transcript
Extrator automático de transcrições de vídeos em plataformas UOL Edtech (Campus Digital FSL, UNINASSAU)
