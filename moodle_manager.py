#!/usr/bin/env python3
"""
moodle_manager.py — Motor genérico y portable de conexión con Moodle UVA y Educacyl.

Permite:
  1. Consultar tareas, plazos y estados de entrega reales.
  2. Consultar notas y calificaciones detalladas del libro de calificaciones.
  3. Extraer enunciados completos de tareas y leer texto de PDFs adjuntos.
  4. Revisar foros de avisos y novedades de profesores.
  5. Sincronizar y descargar apuntes/recursos a carpetas locales.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

try:
    import pypdf
except ImportError:
    pypdf = None

urllib3.disable_warnings()

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def text_clean(html_or_soup: Any) -> str:
    """Limpia y normaliza texto de elementos HTML."""
    if not html_or_soup:
        return ""
    if hasattr(html_or_soup, "get_text"):
        t = html_or_soup.get_text(" ", strip=True)
    else:
        t = BeautifulSoup(str(html_or_soup), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", t).strip()


def post_form(
    session: requests.Session,
    resp: requests.Response,
    extra: Dict[str, str],
    form_idx: Optional[int] = None,
    by_id: Optional[str] = None,
) -> requests.Response:
    """Envía formularios de autenticación SAML/ADFS de forma genérica."""
    soup = BeautifulSoup(resp.text, "html.parser")
    form = None
    if by_id:
        form = soup.find("form", id=by_id)
    if form is None:
        forms = soup.find_all("form")
        form = forms[form_idx if form_idx is not None and form_idx < len(forms) else 0]
    action = urljoin(resp.url, form.get("action") or resp.url)
    data = {
        i.get("name"): (i.get("value") or "")
        for i in form.find_all("input")
        if i.get("name")
    }
    data.update({k: v for k, v in extra.items() if k})
    return session.post(action, data=data, allow_redirects=True, timeout=30)


class MoodleClient:
    """Cliente para interactuar con los campus virtuales Moodle UVa y Educacyl."""

    def __init__(
        self,
        creds: Optional[Dict[str, Any]] = None,
        creds_path: Optional[str | Path] = None,
        uva_base: str = "https://campusvirtual.uva.es",
        educacyl_base: str = "https://aulavirtual.educa.jcyl.es/cifpjuandeherrera",
    ):
        self.uva_base = uva_base.rstrip("/")
        self.educacyl_base = educacyl_base.rstrip("/")
        self.uva_session: Optional[requests.Session] = None
        self.educacyl_session: Optional[requests.Session] = None

        if creds:
            self.creds = creds
        else:
            path = Path(creds_path or Path("./moodle_creds.json"))
            if path.exists():
                try:
                    self.creds = json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    raise ValueError(f"No se pudo leer el archivo de credenciales: {type(exc).__name__}") from None
            else:
                # Soporte para variables de entorno
                self.creds = {
                    "uva": {
                        "user": os.getenv("UVA_USER", ""),
                        "pass": os.getenv("UVA_PASS", ""),
                    },
                    "educacyl": {
                        "user": os.getenv("EDUCACYL_USER", ""),
                        "pass": os.getenv("EDUCACYL_PASS", ""),
                    },
                }

    def get_uva(self) -> requests.Session:
        """Autenticación SAML2 para Universidad de Valladolid."""
        if self.uva_session:
            return self.uva_session
        user = self.creds.get("uva", {}).get("user", "").strip()
        pwd = self.creds.get("uva", {}).get("pass", "").strip()
        if not user or not pwd:
            raise ValueError("Faltan credenciales de UVA (user/pass)")

        s = requests.Session()
        s.verify = False
        s.headers["User-Agent"] = UA
        login_url = (
            f"{self.uva_base}/auth/saml2/login.php"
            "?idp=728c92232de3ee2b9550501a4529466a&passive=off"
        )
        r = s.get(login_url, timeout=30)
        r = post_form(
            s,
            r,
            {
                "adAS_username": user,
                "adAS_password": pwd,
                "adAS_submit": "Acceder",
            },
        )
        if "SAMLResponse" in r.text:
            r = post_form(s, r, {})
        ok = (
            ("/my/" in r.url)
            or ("login" not in r.url.split("?")[0])
            and ("SAML" not in r.url)
            and "sesskey" in r.text
        )
        if not ok:
            raise RuntimeError("Error de autenticación en Moodle UVA por SAML2 (comprueba usuario y contraseña)")
        self.uva_session = s
        return s

    def get_educacyl(self) -> requests.Session:
        """Autenticación ADFS para Educacyl."""
        if self.educacyl_session:
            return self.educacyl_session
        user = self.creds.get("educacyl", {}).get("user", "").strip()
        pwd = self.creds.get("educacyl", {}).get("pass", "").strip()
        if not user or not pwd:
            raise ValueError("Faltan credenciales de Educacyl (user/pass)")

        s = requests.Session()
        s.verify = False
        s.headers["User-Agent"] = UA
        r = s.get(f"{self.educacyl_base}/login/index.php", timeout=30)
        if "adfs" not in r.url or "userNameInput" not in r.text and "UserName" not in r.text:
            r = s.get(r.url, timeout=30)
        r = post_form(
            s,
            r,
            {
                "UserName": user,
                "Password": pwd,
                "Kmsi": "true",
                "AuthMethod": "FormsAuthentication",
            },
            by_id="loginForm",
        )
        if "SAMLResponse" in r.text:
            r = post_form(s, r, {})
        ok = "/my/" in r.url or "aria-label" in r.text and "Área personal" in r.text
        if not ok:
            raise RuntimeError("Error de autenticación en Moodle Educacyl por ADFS (comprueba usuario y contraseña)")
        self.educacyl_session = s
        return s

    def get_courses(self, centro: str = "all") -> List[Dict[str, Any]]:
        """Descubre dinámicamente todas las asignaturas matriculadas del estudiante."""
        courses = []
        if centro in ("all", "uva") and self.creds.get("uva", {}).get("user"):
            try:
                s = self.get_uva()
                r = s.get(f"{self.uva_base}/my/", timeout=30)
                sk = re.search(r'"sesskey"\s*:\s*"([^"]+)"', r.text)
                if sk:
                    payload = [
                        {
                            "index": 0,
                            "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
                            "args": {
                                "offset": 0,
                                "limit": 0,
                                "classification": "all",
                                "sort": "fullname",
                            },
                        }
                    ]
                    rr = s.post(
                        f"{self.uva_base}/lib/ajax/service.php?sesskey={sk.group(1)}",
                        json=payload,
                        timeout=30,
                    ).json()
                    for c in rr[0].get("data", {}).get("courses", []):
                        courses.append(
                            {
                                "id": c["id"],
                                "centro": "UVA",
                                "fullname": c.get("fullname", ""),
                                "shortname": c.get("shortname", ""),
                                "url": f"{self.uva_base}/course/view.php?id={c['id']}",
                            }
                        )
            except Exception as exc:
                sys.stderr.write(f"[moodle] Advertencia al obtener cursos UVA: {type(exc).__name__}\n")

        if centro in ("all", "educacyl") and self.creds.get("educacyl", {}).get("user"):
            try:
                s = self.get_educacyl()
                r = s.get(f"{self.educacyl_base}/my/", timeout=30)
                sk = re.search(r'"sesskey"\s*:\s*"([^"]+)"', r.text)
                if sk:
                    payload = [
                        {
                            "index": 0,
                            "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
                            "args": {
                                "offset": 0,
                                "limit": 0,
                                "classification": "all",
                                "sort": "fullname",
                            },
                        }
                    ]
                    rr = s.post(
                        f"{self.educacyl_base}/lib/ajax/service.php?sesskey={sk.group(1)}",
                        json=payload,
                        timeout=30,
                    ).json()
                    for c in rr[0].get("data", {}).get("courses", []):
                        courses.append(
                            {
                                "id": c["id"],
                                "centro": "Educacyl",
                                "fullname": c.get("fullname", ""),
                                "shortname": c.get("shortname", ""),
                                "url": f"{self.educacyl_base}/course/view.php?id={c['id']}",
                            }
                        )
            except Exception as exc:
                sys.stderr.write(f"[moodle] Advertencia al obtener cursos Educacyl: {type(exc).__name__}\n")

        return courses

    def list_tasks(self, filter_subject: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todas las tareas, estados de entrega y plazos en los cursos matriculados."""
        courses = self.get_courses()
        results = []
        for c in courses:
            if filter_subject and filter_subject.lower() not in c["fullname"].lower():
                continue
            try:
                s = self.get_uva() if c["centro"] == "UVA" else self.get_educacyl()
                r = s.get(c["url"], timeout=30)
                soup = BeautifulSoup(r.text, "html.parser")
                assign_links = []
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    if "/mod/assign/view.php" in href:
                        m = re.search(r"id=(\d+)", href)
                        if m:
                            cmid = m.group(1)
                            name = a.get_text(strip=True)
                            if not any(x["cmid"] == cmid for x in assign_links):
                                assign_links.append({"cmid": cmid, "name": name, "href": href})

                for item in assign_links:
                    ra = s.get(item["href"], timeout=30)
                    asoup = BeautifulSoup(ra.text, "html.parser")
                    atext = asoup.get_text(" ", strip=True)

                    def grab(anchor: str, n: int = 120) -> str:
                        i = atext.find(anchor)
                        return atext[i + len(anchor) : i + len(anchor) + n].strip() if i != -1 else ""

                    estado = grab("Estado de la entrega")
                    for cut in ("Estado de la calificación", "Fecha de entrega", "Tiempo restante", "Última modificación"):
                        if cut in estado:
                            estado = estado[: estado.find(cut)].strip()
                    calif = grab("Estado de la calificación")
                    for cut in ("Fecha de entrega", "Tiempo restante", "Última modificación"):
                        if cut in calif:
                            calif = calif[: calif.find(cut)].strip()
                    venc = grab("Tiempo restante")
                    for cut in ("Última modificación", "Comentarios", "Archivos enviados"):
                        if cut in venc:
                            venc = venc[: venc.find(cut)].strip()

                    fecha = ""
                    m = re.search(r"(\d{1,2})\s+de\s+([a-zñ]+)\s+de\s+(\d{4}),\s+(\d{1,2}):(\d{2})", atext, re.I)
                    if m:
                        fecha = f"{m.group(1)} {m.group(2)} {m.group(3)} a las {m.group(4)}:{m.group(5)}"

                    results.append(
                        {
                            "cmid": item["cmid"],
                            "title": item["name"],
                            "course": c["fullname"],
                            "centro": c["centro"],
                            "url": item["href"],
                            "estado": estado or "No entregado",
                            "calif": calif or "Sin calificar",
                            "tiempo_restante": venc or "Sin plazo explícito",
                            "fecha_entrega": fecha or "No especificada",
                        }
                    )
            except Exception as exc:
                sys.stderr.write(f"[moodle] Error extrayendo tareas de {c['fullname']}: {type(exc).__name__}\n")
        return results

    def get_task_detail(self, query: str | int) -> Dict[str, Any]:
        """Obtiene enunciado completo y extrae texto de PDFs adjuntos de una tarea."""
        query_str = str(query).strip()
        match = None

        if query_str.isdigit():
            cmid = query_str
            for centro, base, sess_getter in [
                ("Educacyl", self.educacyl_base, self.get_educacyl),
                ("UVA", self.uva_base, self.get_uva),
            ]:
                try:
                    s = sess_getter()
                    url = f"{base}/mod/assign/view.php?id={cmid}"
                    r = s.get(url, timeout=35)
                    if r.status_code == 200 and (
                        "Estado de la entrega" in r.text or "Submission status" in r.text or "id=" in r.url
                    ):
                        soup = BeautifulSoup(r.text, "html.parser")
                        h1 = soup.find("h1") or soup.find("div", class_=re.compile("page-header-headings"))
                        title = text_clean(h1) or f"Tarea {cmid}"
                        match = {
                            "cmid": cmid,
                            "title": title,
                            "course": "Curso Moodle",
                            "centro": centro,
                            "url": url,
                            "estado": "Consultado",
                            "fecha_entrega": "",
                            "tiempo_restante": "",
                        }
                        break
                except Exception:
                    continue

        if not match:
            tasks = self.list_tasks()
            for t in tasks:
                if query_str == t["cmid"] or query_str.lower() in t["title"].lower():
                    match = t
                    break

        if not match:
            return {"error": f"No se encontró ninguna tarea que coincida con '{query}'"}

        s = self.get_uva() if match["centro"] == "UVA" else self.get_educacyl()
        r = s.get(match["url"], timeout=35)
        soup = BeautifulSoup(r.text, "html.parser")

        intro_div = (
            soup.find("div", id="intro")
            or soup.find("div", class_="activity-description")
            or soup.find("div", class_="box generalbox")
        )
        intro_text = text_clean(intro_div) if intro_div else "Sin descripción de texto en el encabezado."

        attachments = []
        if intro_div:
            for a in intro_div.find_all("a"):
                href = a.get("href", "")
                if "pluginfile.php" in href or any(
                    href.lower().endswith(ext) for ext in [".pdf", ".docx", ".zip", ".png"]
                ):
                    fname = a.get_text(strip=True) or Path(unquote(href.split("?")[0])).name
                    attachments.append({"name": fname, "url": href})

        extracted_files_content = []
        for att in attachments:
            if ".pdf" in att["name"].lower() or ".pdf" in att["url"].lower():
                try:
                    resp_file = s.get(att["url"], timeout=35)
                    if pypdf:
                        reader = pypdf.PdfReader(io.BytesIO(resp_file.content))
                        pages_text = []
                        for i, p in enumerate(reader.pages[:6]):
                            pt = p.extract_text()
                            if pt:
                                pages_text.append(f"--- Página {i+1} ---\n{pt.strip()}")
                        extracted_files_content.append({"name": att["name"], "text": "\n".join(pages_text)})
                    else:
                        extracted_files_content.append(
                            {"name": att["name"], "error": "Librería pypdf no instalada en el entorno"}
                        )
                except Exception as ex:
                    extracted_files_content.append({"name": att["name"], "error": str(ex)})

        return {
            "cmid": match["cmid"],
            "title": match["title"],
            "course": match.get("course", "Curso Moodle"),
            "centro": match["centro"],
            "url": match["url"],
            "estado": match.get("estado", ""),
            "fecha_entrega": match.get("fecha_entrega", ""),
            "tiempo_restante": match.get("tiempo_restante", ""),
            "descripcion": intro_text,
            "archivos_adjuntos": [a["name"] for a in attachments],
            "archivos_leidos": extracted_files_content,
        }

    def list_grades(self, filter_subject: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extrae calificaciones detalladas del libro de notas de cada curso."""
        courses = self.get_courses()
        all_grades = []
        for c in courses:
            if filter_subject and filter_subject.lower() not in c["fullname"].lower():
                continue
            try:
                s = self.get_uva() if c["centro"] == "UVA" else self.get_educacyl()
                base = self.uva_base if c["centro"] == "UVA" else self.educacyl_base
                r = s.get(f"{base}/grade/report/user/index.php?id={c['id']}", timeout=30)
                soup = BeautifulSoup(r.text, "html.parser")
                table = soup.find("table", class_="user-grade") or soup.find("table", class_="generaltable")
                course_items = []
                if table:
                    for tr in table.find_all("tr"):
                        tds = tr.find_all("td")
                        if len(tds) >= 2:
                            name = text_clean(tr.find(["th"], class_=re.compile("itemname")) or tds[0])
                            grade = text_clean(tds[1] if len(tds) > 1 else tds[0])
                            for td in tds:
                                if "column-grade" in " ".join(td.get("class", [])):
                                    grade = text_clean(td)
                            if name and grade and not grade.startswith("–"):
                                course_items.append({"item": name, "grade": grade})
                if course_items:
                    all_grades.append(
                        {
                            "course": c["fullname"],
                            "centro": c["centro"],
                            "items": course_items,
                        }
                    )
            except Exception as exc:
                sys.stderr.write(f"[moodle] Error leyendo notas de {c['fullname']}: {type(exc).__name__}\n")
        return all_grades

    def list_forums(self, days: int = 15) -> List[Dict[str, Any]]:
        """Revisa foros de novedades y avisos docentes de los cursos matriculados."""
        courses = self.get_courses()
        discussions_found = []
        for c in courses:
            try:
                s = self.get_uva() if c["centro"] == "UVA" else self.get_educacyl()
                r = s.get(c["url"], timeout=30)
                soup = BeautifulSoup(r.text, "html.parser")
                forum_links = []
                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    if "/mod/forum/view.php" in href:
                        m = re.search(r"id=(\d+)", href)
                        if m and href not in forum_links:
                            forum_links.append(href)

                for flink in forum_links:
                    rf = s.get(flink, timeout=30)
                    fsoup = BeautifulSoup(rf.text, "html.parser")
                    for tr in fsoup.find_all("tr", class_="discussion"):
                        topic_el = tr.find("th", class_="topic")
                        author_el = tr.find("td", class_="author")
                        topic = text_clean(topic_el)
                        author = text_clean(author_el)
                        link = (
                            topic_el.find("a").get("href")
                            if topic_el and topic_el.find("a")
                            else flink
                        )
                        discussions_found.append(
                            {
                                "course": c["fullname"],
                                "centro": c["centro"],
                                "topic": topic,
                                "author": author,
                                "url": link,
                            }
                        )
            except Exception as exc:
                sys.stderr.write(f"[moodle] Error leyendo foros de {c['fullname']}: {type(exc).__name__}\n")
        return discussions_found

    def sync_resources(
        self, download: bool = False, base_dir: str = "./apuntes_moodle"
    ) -> Dict[str, Any]:
        """Escanea y descarga organizadamente apuntes y recursos docentes a disco."""
        base_path = Path(os.path.expanduser(base_dir))
        courses = self.get_courses()
        cache_file = base_path / ".moodle_download_cache.json"
        history = {}
        if cache_file.exists():
            try:
                history = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                history = {}

        discovered = []
        for c in courses:
            try:
                s = self.get_uva() if c["centro"] == "UVA" else self.get_educacyl()
                r = s.get(c["url"], timeout=30)
                soup = BeautifulSoup(r.text, "html.parser")

                clean_cname = re.sub(r"[^\w\s-]", "", c["fullname"]).strip()
                target_folder = base_path / c["centro"] / clean_cname

                for a in soup.find_all("a"):
                    href = a.get("href", "")
                    if "/mod/resource/view.php" in href:
                        m = re.search(r"id=(\d+)", href)
                        if m:
                            cmid = m.group(1)
                            name = text_clean(a) or f"recurso_{cmid}"
                            discovered.append(
                                {
                                    "cmid": cmid,
                                    "type": "resource",
                                    "name": name,
                                    "course": c["fullname"],
                                    "centro": c["centro"],
                                    "url": href,
                                    "dest_dir": str(target_folder),
                                }
                            )
            except Exception as exc:
                sys.stderr.write(f"[moodle] Error escaneando recursos de {c['fullname']}: {type(exc).__name__}\n")

        downloaded_count = 0
        if download:
            for item in discovered:
                cmid = item["cmid"]
                if cmid in history:
                    continue
                s = self.get_uva() if item["centro"] == "UVA" else self.get_educacyl()
                try:
                    resp = s.get(item["url"], allow_redirects=True, timeout=40)
                    cd = resp.headers.get("content-disposition", "")
                    filename = None
                    if "filename=" in cd:
                        filename = re.findall(r'filename="?([^";]+)"?', cd)[0]
                    if not filename:
                        filename = unquote(Path(resp.url.split("?")[0]).name)
                    if not filename or filename == "view.php":
                        filename = f"{item['name']}.pdf"

                    dest_dir = Path(item["dest_dir"])
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    out_file = dest_dir / filename
                    out_file.write_bytes(resp.content)
                    history[cmid] = {"filename": str(out_file), "ts": time.time()}
                    downloaded_count += 1
                except Exception as ex:
                    sys.stderr.write(f"Error descargando {item['name']}: {ex}\n")

            try:
                base_path.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
            except Exception:
                pass

        return {
            "total_discovered": len(discovered),
            "new_downloaded": downloaded_count,
            "items": discovered,
        }
