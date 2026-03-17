"""
fsl.py - Especialização para Campus Digital FSL
(Faculdade Sírio-Libanês)

Login via AWS Cognito com redirect externo.
"""

from playwright.async_api import Page, BrowserContext
from .base import UolEdtechTranscriptor


class FSLTranscriptor(UolEdtechTranscriptor):
    """
    Extrator de transcrições para o Campus Digital da
    Faculdade Sírio-Libanês (FSL).

    Autenticação: AWS Cognito via redirect externo.
    O fluxo deve começar em /login (não diretamente no Cognito)
    para que o nonce seja gerado pela sessão Next.js da plataforma.

    Uso:
        fsl = FSLTranscriptor(email="...", password="...")
        asyncio.run(fsl.run([
            "https://campusdigital.faculdadesiriolibanes.org.br/courses/49/discipline/20738/period/35?index=0",
            "https://campusdigital.faculdadesiriolibanes.org.br/courses/49/discipline/20338/period/35?index=0",
        ]))
    """

    BASE_URL = "https://campusdigital.faculdadesiriolibanes.org.br"
    PLATFORM_NAME = "Campus Digital FSL"

    async def login(self, context: BrowserContext, page: Page) -> None:
        """
        Realiza login via AWS Cognito.
        Fluxo:
            1. Acessa /login → clica "Entrar" → redireciona para Cognito
            2. Preenche email e senha no Cognito
            3. Aguarda redirect de volta para a plataforma
        """
        login_url = f"{self.BASE_URL}/login"
        await page.goto(login_url, wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # Clica no botão "Entrar" que dispara o redirect para o Cognito
        entrar_btn = await page.query_selector("button:has-text('Entrar'), a:has-text('Entrar')")
        if entrar_btn:
            await entrar_btn.click()
        else:
            # Fallback: procura qualquer link de login
            await page.click("text=Entrar")

        # Aguarda redirecionamento para a página do Cognito
        await page.wait_for_url("**/login**", timeout=15000)
        await page.wait_for_timeout(1000)

        # Preenche email
        email_input = await page.wait_for_selector(
            "input[type='email'], input[name='email'], input[id*='email'], input[placeholder*='email' i]",
            timeout=10000
        )
        await email_input.fill(self.email)

        # Preenche senha
        password_input = await page.wait_for_selector(
            "input[type='password']",
            timeout=10000
        )
        await password_input.fill(self.password)

        # Clica em Sign in / Entrar
        submit_btn = await page.query_selector(
            "button[type='submit'], input[type='submit'], button:has-text('Sign in'), button:has-text('Entrar')"
        )
        if submit_btn:
            await submit_btn.click()
        else:
            await page.keyboard.press("Enter")

        # Aguarda redirect de volta para a plataforma
        await page.wait_for_url(f"{self.BASE_URL}/**", timeout=30000)
        await page.wait_for_timeout(2000)
        print(f"  Login FSL OK — URL atual: {page.url}")
