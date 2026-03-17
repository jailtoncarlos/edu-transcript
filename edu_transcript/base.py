"""
base.py - Classe base abstrata para extração de transcrições
em plataformas UOL Edtech (Campus Digital FSL, UNINASSAU, etc.)
"""

import asyncio
import os
import re
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

from playwright.async_api import async_playwright, Page, BrowserContext


class UolEdtechTranscriptor(ABC):
    """
    Classe base abstrata para extratores de transcrição das plataformas
    UOL Edtech (Campus Digital). Subclasses devem implementar o método login().

    Fluxo:
        1. login() - autenticação na plataforma
        2. discover_lessons() - descobre todas as aulas de uma URL de disciplina
        3. collect_transcript() - extrai a transcrição de um vídeo Vimeo
        4. save_transcript() - salva como .txt
        5. run() - orquestra tudo e gera um .zip final
    """

    # Subclasses devem definir estes atributos
    BASE_URL: str = ""
    PLATFORM_NAME: str = "UOL Edtech"

    def __init__(self, email: str = "", password: str = "", cookies: list = None):
        self.email = email
        self.password = password
        self.cookies = cookies or []
        self.output_dir = Path("transcricoes")
        self.output_dir.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Método abstrato — cada plataforma implementa sua própria autenticação
    # ------------------------------------------------------------------

    @abstractmethod
    async def login(self, context: BrowserContext, page: Page) -> None:
        """Realiza o login na plataforma."""
        ...

    # ------------------------------------------------------------------
    # Métodos concretos compartilhados por todas as plataformas
    # ------------------------------------------------------------------

    async def discover_lessons(self, page: Page, discipline_url: str) -> list[dict]:
        """
        Navega até a URL da disciplina e descobre todos os itens de aula
        (elementos [data-cy='partLesson']) na barra lateral.

        Retorna lista de dicts: [{title, url, group}, ...]
        """
        await page.goto(discipline_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Expande todos os grupos de aula
        groups = await page.query_selector_all("[data-cy='groupLesson']")
        for group in groups:
            try:
                await group.click()
                await page.wait_for_timeout(500)
            except Exception:
                pass

        # Coleta todos os itens de aula
        lessons = await page.evaluate(r"""
            () => {
                const items = document.querySelectorAll("[data-cy='partLesson']");
                return Array.from(items).map(el => {
                    const title = el.querySelector('.title, [class*="title"], span')?.innerText?.trim()
                               || el.innerText?.trim()
                               || 'Sem título';
                    const link = el.closest('a');
                    const url = link ? link.href : window.location.href;
                    return { title, url };
                });
            }
        """)
        return lessons

    async def collect_transcript(self, page: Page, lesson_url: str) -> list[str]:
        """
        Navega até a URL da aula, aguarda o iframe Vimeo carregar,
        extrai o video_id e coleta as legendas via postMessage.

        Retorna lista de strings com as linhas da transcrição.
        """
        await page.goto(lesson_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Aguarda o iframe Vimeo aparecer
        iframe_el = await page.wait_for_selector(
            "iframe[src*='player.vimeo.com']",
            timeout=30000
        )
        iframe_src = await iframe_el.get_attribute("src")

        # Extrai video_id e hash do src
        video_id_match = re.search(r"player\.vimeo\.com/video/(\d+)", iframe_src)
        hash_match = re.search(r"[?&]h=([a-f0-9]+)", iframe_src)

        if not video_id_match:
            raise ValueError(f"video_id não encontrado em: {iframe_src}")

        video_id = video_id_match.group(1)
        video_hash = hash_match.group(1) if hash_match else ""

        embed_url = f"https://player.vimeo.com/video/{video_id}"
        if video_hash:
            embed_url += f"?h={video_hash}"

        # Abre player Vimeo diretamente para coletar legendas via postMessage
        vimeo_page = await page.context.new_page()
        cues: list[str] = []
        finished = asyncio.Event()

        def handle_message(msg):
            import json
            try:
                data = json.loads(msg)
                event = data.get("event", "")

                if event == "cuechange":
                    payload = data.get("data", {})
                    # Formato 1: data.text (string direta)
                    text = payload.get("text", "")
                    if text and text.strip():
                        cues.append(text.strip())
                    # Formato 2: data.cues (array)
                    for cue in payload.get("cues", []):
                        t = cue.get("text", "")
                        if t and t.strip():
                            cues.append(t.strip())

                elif event in ("finish", "ended"):
                    finished.set()

            except Exception:
                pass

        await vimeo_page.expose_function("__onPostMessage__", handle_message)

        await vimeo_page.goto(embed_url, wait_until="domcontentloaded")
        await vimeo_page.wait_for_timeout(2000)

        # Injeta listener de postMessage e ativa legenda pt-x-autogen
        await vimeo_page.evaluate(r"""
            () => {
                window.addEventListener('message', (e) => {
                    if (e.data) {
                        try {
                            window.__onPostMessage__(
                                typeof e.data === 'string' ? e.data : JSON.stringify(e.data)
                            );
                        } catch(err) {}
                    }
                });

                function sendVimeo(data) {
                    const iframe = document.querySelector('iframe');
                    if (iframe) iframe.contentWindow.postMessage(JSON.stringify(data), '*');
                }

                // Ativa legenda automática em português
                sendVimeo({ method: 'enableTextTrack', value: { language: 'pt-x-autogen' } });

                // Velocidade máxima
                sendVimeo({ method: 'setPlaybackRate', value: 2 });

                // Começa do início
                sendVimeo({ method: 'seekTo', value: 0 });
                sendVimeo({ method: 'play' });
            }
        """)

        # Aguarda o vídeo terminar (timeout de 10 minutos)
        try:
            await asyncio.wait_for(finished.wait(), timeout=600)
        except asyncio.TimeoutError:
            pass

        await vimeo_page.close()

        # Deduplica mantendo ordem
        seen = set()
        unique_cues = []
        for cue in cues:
            if cue not in seen:
                seen.add(cue)
                unique_cues.append(cue)

        return unique_cues

    async def save_transcript(self, lines: list[str], title: str, index: int) -> Path:
        """Salva a transcrição como arquivo .txt."""
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filename = self.output_dir / f"{index:02d}_{safe_title}.txt"
        filename.write_text("\n".join(lines), encoding="utf-8")
        print(f"  ✓ Salvo: {filename.name} ({len(lines)} linhas)")
        return filename

    async def run(self, discipline_urls: list[str], zip_name: str = "transcricoes.zip") -> str:
        """
        Método principal. Recebe uma lista de URLs de disciplina,
        extrai transcrições de todos os vídeos e salva em .zip.
        """
        saved_files = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            print(f"[{self.PLATFORM_NAME}] Fazendo login...")
            await self.login(context, page)
            print("Login realizado com sucesso!")

            lesson_counter = 1

            for url in discipline_urls:
                print(f"\nProcessando disciplina: {url}")
                lessons = await self.discover_lessons(page, url)
                print(f"  Encontradas {len(lessons)} aulas")

                for lesson in lessons:
                    print(f"  → {lesson['title']}")
                    try:
                        lines = await self.collect_transcript(page, lesson["url"])
                        if lines:
                            path = await self.save_transcript(
                                lines, lesson["title"], lesson_counter
                            )
                            saved_files.append(path)
                            lesson_counter += 1
                        else:
                            print(f"    ⚠ Nenhuma legenda encontrada")
                    except Exception as e:
                        print(f"    ✗ Erro: {e}")

            await browser.close()

        # Compacta tudo em .zip
        zip_path = Path(zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in saved_files:
                zf.write(f, f.name)

        print(f"\n✅ Concluído! {len(saved_files)} transcrições salvas em '{zip_path}'")
        return str(zip_path)
