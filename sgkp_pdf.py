"""Export a browser conversation as a readable, source-linked PDF."""
from __future__ import annotations

import html
import re
import threading
from datetime import datetime
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from sgkp_services import scan_url


MAX_EXPORT_TURNS = 200
MAX_EXPORT_BYTES = 8_000_000
_font_lock = threading.Lock()
_fonts_ready = False
_font_files = {
    "SGKP": "DejaVuSans.ttf",
    "SGKP-Bold": "DejaVuSans-Bold.ttf",
    "SGKP-Oblique": "DejaVuSans-Oblique.ttf",
    "SGKP-BoldOblique": "DejaVuSans-BoldOblique.ttf",
}


def validate_export_turns(raw: object) -> list[dict]:
    """Bound browser-provided content before passing it to ReportLab."""
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_EXPORT_TURNS:
        raise ValueError("Eksport wymaga od 1 do 200 ukończonych odpowiedzi")
    turns = []
    for turn in raw:
        if not isinstance(turn, dict):
            raise ValueError("Nieprawidłowy wpis konwersacji")
        question, answer, sources = turn.get("question"), turn.get("answer"), turn.get("sources")
        if (not isinstance(question, str) or not 1 <= len(question.strip()) <= 500
                or not isinstance(answer, str) or not 1 <= len(answer.strip()) <= 40_000
                or not isinstance(sources, list) or len(sources) > 20):
            raise ValueError("Nieprawidłowy wpis konwersacji")
        checked_sources = []
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("Nieprawidłowe źródło w eksporcie")
            citation, name, volume, page = (
                source.get("citation"), source.get("nazwa"), source.get("tom"), source.get("strona"))
            if (type(citation) is not int or not 1 <= citation <= 20
                    or not isinstance(name, str) or not 1 <= len(name.strip()) <= 200
                    or (volume is not None and (not isinstance(volume, str)
                        or not re.fullmatch(r"(?:0[1-9]|1[0-6])", volume)))
                    or (page is not None and (type(page) is not int or not 1 <= page <= 1000))):
                raise ValueError("Nieprawidłowe źródło w eksporcie")
            checked_sources.append({"citation": citation, "nazwa": name.strip(),
                                    "tom": volume, "strona": page})
        provider = turn.get("provider")
        model = turn.get("model")
        turns.append({"question": question.strip(), "answer": answer.strip(),
                      "sources": checked_sources,
                      "provider": provider if provider in ("local", "openai") else None,
                      "model": model if isinstance(model, str) and len(model) <= 100 else None})
    return turns


def _ensure_fonts() -> None:
    global _fonts_ready
    with _font_lock:
        if _fonts_ready:
            return
        candidates = (Path("/usr/share/fonts/truetype/dejavu"),
                      Path("/usr/local/share/fonts/dejavu"))
        directory = next((path for path in candidates
                          if all((path / filename).is_file() for filename in _font_files.values())), None)
        if directory is None:
            raise RuntimeError("Do eksportu PDF potrzebne są czcionki DejaVu Sans (fonts-dejavu-core)")
        for family, filename in _font_files.items():
            pdfmetrics.registerFont(TTFont(family, str(directory / filename)))
        pdfmetrics.registerFontFamily("SGKP", normal="SGKP", bold="SGKP-Bold",
                                      italic="SGKP-Oblique", boldItalic="SGKP-BoldOblique")
        _fonts_ready = True


def _styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName="SGKP", fontSize=9.5, leading=15, textColor=colors.HexColor("#173352"),
                spaceAfter=7)
    return {
        "title": ParagraphStyle("SGKPTitle", **{**base, "fontName": "SGKP-Bold", "fontSize": 19,
                                        "leading": 24, "spaceAfter": 6}),
        "meta": ParagraphStyle("SGKPMeta", **{**base, "fontSize": 8, "textColor": colors.HexColor("#667d95"),
                                      "spaceAfter": 15}),
        "label": ParagraphStyle("SGKPLabel", **{**base, "fontName": "SGKP-Bold", "fontSize": 8,
                                       "leading": 12, "textColor": colors.HexColor("#32649b"),
                                       "spaceBefore": 10, "spaceAfter": 5}),
        "question": ParagraphStyle("SGKPQuestion", **{**base, "fontName": "SGKP-Bold",
                                          "fontSize": 10.5, "leading": 16, "spaceAfter": 10}),
        "body": ParagraphStyle("SGKPBody", **base),
        "heading": ParagraphStyle("SGKPHeading", **{**base, "fontName": "SGKP-Bold",
                                        "fontSize": 10.5, "spaceBefore": 7}),
        "list": ParagraphStyle("SGKPList", **{**base, "leftIndent": 17, "firstLineIndent": -14,
                                     "spaceAfter": 5}),
        "source": ParagraphStyle("SGKPSource", **{**base, "fontSize": 8.5, "leading": 13,
                                        "spaceAfter": 4}),
        "note": ParagraphStyle("SGKPNote", **{**base, "fontSize": 8,
                                      "textColor": colors.HexColor("#667d95")}),
    }


class _MarkdownBlocks(HTMLParser):
    """Keep common Markdown structure and only safe inline markup for Paragraph."""

    def __init__(self, styles: dict[str, ParagraphStyle]):
        super().__init__(convert_charrefs=True)
        self.styles = styles
        self.flowables = []
        self.parts: list[str] = []
        self.kind = "body"
        self.lists: list[dict] = []
        self.links: list[bool] = []
        self.hidden = 0

    def _flush(self) -> None:
        value = "".join(self.parts).strip()
        if value:
            self.flowables.append(Paragraph(value, self.styles[self.kind]))
        self.parts = []
        self.kind = "body"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self.hidden += 1
            return
        if self.hidden:
            return
        if tag in ("p", "h1", "h2", "h3", "h4", "li", "tr"):
            self._flush()
            self.kind = "heading" if tag.startswith("h") else "list" if tag == "li" else "body"
            if tag == "li":
                if self.lists:
                    top = self.lists[-1]
                    if top["ordered"]:
                        top["number"] += 1
                        prefix = f"{top['number']}. "
                    else:
                        prefix = "• "
                else:
                    prefix = "• "
                self.parts.append(html.escape(prefix))
        elif tag in ("ul", "ol"):
            self.lists.append({"ordered": tag == "ol", "number": 0})
        elif tag in ("strong", "b"):
            self.parts.append("<b>")
        elif tag in ("em", "i"):
            self.parts.append("<i>")
        elif tag == "br":
            self.parts.append("<br/>")
        elif tag in ("td", "th") and self.parts:
            self.parts.append(" | ")
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            linked = href.startswith(("https://", "http://"))
            self.links.append(linked)
            if linked:
                self.parts.append(f'<link href="{html.escape(href, quote=True)}" color="#245d9d">')
        elif tag == "code":
            self.parts.append('<font name="SGKP-Oblique">')

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag in ("p", "h1", "h2", "h3", "h4", "li", "tr"):
            self._flush()
        elif tag in ("ul", "ol") and self.lists:
            self.lists.pop()
        elif tag in ("strong", "b"):
            self.parts.append("</b>")
        elif tag in ("em", "i"):
            self.parts.append("</i>")
        elif tag == "a" and self.links:
            if self.links.pop():
                self.parts.append("</link>")
        elif tag == "code":
            self.parts.append("</font>")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(html.escape(data))


def _answer_flowables(answer: str, styles: dict[str, ParagraphStyle]) -> list:
    parser = _MarkdownBlocks(styles)
    parser.feed(markdown.markdown(answer, extensions=["extra", "sane_lists"]))
    parser.close()
    parser._flush()
    return parser.flowables


def render_chat_pdf(turns: list[dict]) -> bytes:
    _ensure_fonts()
    styles = _styles()
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, leftMargin=46, rightMargin=46,
                                 topMargin=49, bottomMargin=48, title="SGKP - konwersacja",
                                 author="Wyszukiwarka SGKP")
    story = [Paragraph("SGKP · Konwersacja", styles["title"]),
             Paragraph("Eksport: " + datetime.now().strftime("%d.%m.%Y, %H:%M")
                       + " · Liczba pytań: " + str(len(turns)), styles["meta"]),
             Paragraph("Odpowiedzi wygenerowano automatycznie. Ustalenia należy sprawdzić w cytowanych hasłach i skanach.",
                       styles["note"]), Spacer(1, 11)]
    for number, turn in enumerate(turns, 1):
        story.extend([HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd9e8")),
                      KeepTogether([Paragraph(f"PYTANIE {number}", styles["label"]),
                                    Paragraph(html.escape(turn["question"]), styles["question"])]),
                      Paragraph("ODPOWIEDŹ", styles["label"])])
        story.extend(_answer_flowables(turn["answer"], styles))
        if turn["provider"] == "openai":
            model = f" ({html.escape(turn['model'])})" if turn["model"] else ""
            story.append(Paragraph("Odpowiedź przygotowana przez OpenAI" + model + ".", styles["note"]))
        if turn["sources"]:
            story.append(Paragraph("ŹRÓDŁA", styles["label"]))
            for source in turn["sources"]:
                location = ", ".join(part for part in (
                    "tom " + source["tom"] if source["tom"] else "",
                    "s. " + str(source["strona"]) if source["strona"] else "") if part)
                line = f"[{source['citation']}] {html.escape(source['nazwa'])}"
                if location:
                    line += " · " + html.escape(location)
                url = scan_url(source["tom"], source["strona"])
                if url:
                    line += f' · <link href="{html.escape(url, quote=True)}" color="#245d9d">Skan strony</link>'
                story.append(Paragraph(line, styles["source"]))
        story.append(Spacer(1, 14))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#cbd9e8"))
        canvas.line(46, 35, A4[0] - 46, 35)
        canvas.setFont("SGKP", 8)
        canvas.setFillColor(colors.HexColor("#667d95"))
        canvas.drawString(46, 23, "Słownik Geograficzny Królestwa Polskiego")
        canvas.drawRightString(A4[0] - 46, 23, f"Strona {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
