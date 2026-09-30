#!/usr/bin/env python3
"""
moodle_cli.py — Interfaz de línea de comandos para interactuar con Moodle UVA y Educacyl.

Uso:
  python3 moodle_cli.py tasks [--subject <texto>] [--json]
  python3 moodle_cli.py grades [--subject <texto>] [--json]
  python3 moodle_cli.py task-detail <cmid_o_palabra_clave> [--json]
  python3 moodle_cli.py forums [--days 15] [--json]
  python3 moodle_cli.py sync-resources [--download] [--json] [--dir <directorio>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from moodle_manager import MoodleClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CLI Moodle UVA + Educacyl")
    parser.add_argument(
        "--creds",
        default="./moodle_creds.json",
        help="Ruta al archivo de credenciales JSON (predeterminado: ./moodle_creds.json)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando: tasks
    p_tasks = subparsers.add_parser("tasks", help="Listar tareas pendientes y plazos")
    p_tasks.add_argument("--subject", help="Filtrar por asignatura")
    p_tasks.add_argument("--json", action="store_true", help="Salida en formato JSON")

    # Subcomando: grades
    p_grades = subparsers.add_parser("grades", help="Consultar calificaciones publicadas")
    p_grades.add_argument("--subject", help="Filtrar por asignatura")
    p_grades.add_argument("--json", action="store_true", help="Salida en formato JSON")

    # Subcomando: task-detail
    p_detail = subparsers.add_parser(
        "task-detail", help="Obtener enunciado completo y texto de PDFs de una tarea"
    )
    p_detail.add_argument("query", help="CMID numérico o parte del título de la tarea")
    p_detail.add_argument("--json", action="store_true", help="Salida en formato JSON")

    # Subcomando: forums
    p_forums = subparsers.add_parser("forums", help="Listar avisos y novedades en foros docentes")
    p_forums.add_argument("--days", type=int, default=15, help="Días hacia atrás")
    p_forums.add_argument("--json", action="store_true", help="Salida en formato JSON")

    # Subcomando: sync-resources
    p_sync = subparsers.add_parser(
        "sync-resources", help="Escanear y descargar apuntes/recursos de asignaturas"
    )
    p_sync.add_argument("--download", action="store_true", help="Descargar archivos nuevos a disco")
    p_sync.add_argument(
        "--dir", default="./apuntes_moodle", help="Directorio destino para descargas"
    )
    p_sync.add_argument("--json", action="store_true", help="Salida en formato JSON")

    args = parser.parse_args(argv)

    try:
        client = MoodleClient(creds_path=args.creds)
    except Exception as exc:
        print(f"Error inicializando cliente Moodle: {exc}", file=sys.stderr)
        return 1

    if args.command == "tasks":
        try:
            tasks = client.list_tasks(filter_subject=args.subject)
        except Exception as exc:
            print(f"Error listando tareas: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(tasks, ensure_ascii=False, indent=2))
        else:
            if not tasks:
                print("No se encontraron tareas pendientes.")
                return 0
            print(f"📋 Tareas encontradas ({len(tasks)}):")
            for t in tasks:
                print(f"\n📌 [{t['centro']}] {t['title']} (ID: {t['cmid']})")
                print(f"   📚 Asignatura: {t['course']}")
                print(f"   ⏳ Fecha límite: {t['fecha_entrega']} ({t['tiempo_restante']})")
                print(f"   📊 Estado: {t['estado']} | Calificación: {t['calif']}")

    elif args.command == "grades":
        try:
            grades = client.list_grades(filter_subject=args.subject)
        except Exception as exc:
            print(f"Error consultando notas: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(grades, ensure_ascii=False, indent=2))
        else:
            if not grades:
                print("No hay calificaciones registradas aún.")
                return 0
            for c in grades:
                print(f"\n📘 [{c['centro']}] {c['course']}")
                for it in c["items"]:
                    print(f"   • {it['item']}: {it['grade']}")

    elif args.command == "task-detail":
        try:
            detail = client.get_task_detail(args.query)
        except Exception as exc:
            print(f"Error obteniendo detalle de tarea: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(detail, ensure_ascii=False, indent=2))
        else:
            if "error" in detail:
                print(f"❌ Error: {detail['error']}")
                return 1
            print(f"📝 DETALLE DE TAREA: {detail['title']} (CMID: {detail['cmid']})")
            print(f"📚 Asignatura: {detail['course']} ({detail['centro']})")
            print(f"⏳ Entrega: {detail['fecha_entrega']} ({detail['tiempo_restante']})")
            print(f"📊 Estado: {detail['estado']}")
            print(f"\n📖 Enunciado / Descripción en Moodle:\n{detail['descripcion']}")
            if detail.get("archivos_adjuntos"):
                print(f"\n📎 Archivos adjuntos: {', '.join(detail['archivos_adjuntos'])}")
            if detail.get("archivos_leidos"):
                print("\n📄 Contenido extraído de documentos adjuntos:")
                for doc in detail["archivos_leidos"]:
                    print(f"\n--- Archivo: {doc['name']} ---")
                    if "text" in doc:
                        print(
                            doc["text"][:1500]
                            + ("\n... [Truncado]" if len(doc["text"]) > 1500 else "")
                        )
                    else:
                        print(f"Error extrayendo texto: {doc.get('error')}")

    elif args.command == "forums":
        try:
            forums = client.list_forums(days=args.days)
        except Exception as exc:
            print(f"Error consultando foros: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(forums, ensure_ascii=False, indent=2))
        else:
            if not forums:
                print("No hay avisos recientes en los foros.")
                return 0
            print(f"📢 Avisos y novedades en foros ({len(forums)}):")
            for f in forums:
                print(f"\n📣 [{f['centro']}] {f['topic']}")
                print(f"   📚 Asignatura: {f['course']}")
                print(f"   👤 Publicado por: {f['author']}")
                print(f"   🔗 Enlace: {f['url']}")

    elif args.command == "sync-resources":
        try:
            res = client.sync_resources(download=args.download, base_dir=args.dir)
        except Exception as exc:
            print(f"Error sincronizando recursos: {exc}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"📦 Recursos encontrados en Moodle: {res['total_discovered']}")
            if args.download:
                print(f"✅ Nuevos recursos descargados y guardados: {res['new_downloaded']}")
            else:
                print("ℹ️ Modo escaneo: ejecuta con --download para guardar los archivos en disco.")
            for it in res["items"][:15]:
                print(f"   • [{it['centro']}] {it['name']} -> {it['dest_dir']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
