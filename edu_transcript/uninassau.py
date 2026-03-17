"""
uninassau.py - Especialização para Campus Digital UNINASSAU

Login via injeção de cookies (reCAPTCHA bloqueia automação headless).
O usuário deve exportar os cookies após login manual e fornecê-los
como lista de dicts no padrão Playwright/Netscape.
"""

from playwright.async_api import Page, BrowserContext
from .base import UolEdtechTranscriptor


class UninassauTranscriptor(UolEdtechTranscriptor):
    """
    Extrator de transcrições para o Campus Digital UNINASSAU.

    ⚠ IMPORTANTE: O login automático com usuário/senha não é possível
    porque a plataforma usa reCAPTCHA v2 que bloqueia navegadores headless.

    Para usar, exporte os cookies após fazer login manualmente no navegador
    e passe-os como lista de dicts para o construtor.

    Como exportar os cookies:
        1. Faça login em https://campusdigital.uninassau.edu.br
        2. Abra DevTools (F12) → Application → Cookies
        3. Copie todos os cookies como JSON (ou use extensão "EditThisCookie")
        4. Passe a lista para o parâmetro cookies=

    Uso:
        cookies = [
            {"name": "session", "value": "...", "domain": ".uninassau.edu.br", "path": "/"},
            # ... outros cookies
        ]
        uninassau = UninassauTranscriptor(cookies=cookies)
        asyncio.run(uninassau.run([
            "https://campusdigital.uninassau.edu.br/courses/5046/discipline/316?index=1",
        ]))
    """

    BASE_URL = "https://campusdigital.uninassau.edu.br"
    PLATFORM_NAME = "Campus Digital UNINASSAU"

    async def login(self, context: BrowserContext, page: Page) -> None:
        """
        Autentica via injeção de cookies no contexto do navegador.
        Os cookies devem ter sido exportados após login manual.
        """
        if not self.cookies:
            raise ValueError(
                "UninassauTranscriptor requer cookies para autenticação.\n"
                "Faça login manualmente em https://campusdigital.uninassau.edu.br\n"
                "e exporte os cookies como lista de dicts."
            )

        # Injeta cookies no contexto do Playwright
        await context.add_cookies(self.cookies)

        # Verifica se o login funcionou navegando para a home
        await page.goto(f"{self.BASE_URL}/home", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        current_url = page.url
        if "/login" in current_url:
            raise RuntimeError(
                "Cookie inválido ou expirado. Faça login novamente e exporte novos cookies."
            )

        print(f"  Login UNINASSAU OK via cookies — URL atual: {current_url}")
