from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .catalog import currents
from .engine import activate, activate_with_llm, build_prompt
from .model_config import ModelSettings, load_model_settings
from .model_runtime import enhance_criba_packet, enhance_ideas_with_model
from .storage import Storage


def _query(args: argparse.Namespace) -> str:
    """Read the activation query from --query or --file."""
    if args.query:
        return str(args.query)
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    raise ValueError("Indica --query o --file.")


def _run(args: argparse.Namespace, prompt: bool = False) -> int:
    query = _query(args)

    # Construir kwargs para LLM si se especifica
    llm_kwargs = {}
    if getattr(args, "llm_model", None):
        llm_kwargs["model"] = args.llm_model
    if getattr(args, "llm_url", None):
        llm_kwargs["url"] = args.llm_url
    if getattr(args, "llm_api_key", None):
        llm_kwargs["api_key"] = args.llm_api_key

    llm_mode = getattr(args, "llm", "none")

    use_configured_model = bool(getattr(args, "use_configured_model", False))
    if use_configured_model and llm_mode != "none":
        raise ValueError("Elige --use-configured-model o --llm, no ambos.")

    # Contexto para interprete-serendipia (P2): api_key + seed
    ctx: dict[str, Any] = {}
    if getattr(args, "llm_api_key", None):
        ctx["zai_api_key"] = args.llm_api_key
    if getattr(args, "seed", None) is not None:
        ctx["seed"] = args.seed

    if use_configured_model:
        packet = activate(query, args.current, args.mode, args.supporting_methods, context=ctx)
        packet = enhance_criba_packet(packet, _configured_model_settings(args))
    elif llm_mode != "none":
        packet = activate_with_llm(query, args.current, args.mode, args.supporting_methods,
                                   llm_mode=llm_mode, llm_kwargs=llm_kwargs, context=ctx)
    else:
        packet = activate(query, args.current, args.mode, args.supporting_methods, context=ctx)

    store = Storage(args.database)
    store.save(query, packet, {
        "current": args.current,
        "mode": args.mode,
        "supporting_methods": args.supporting_methods,
        "llm_mode": llm_mode,
        "use_configured_model": use_configured_model,
    })
    output = build_prompt(packet) if prompt else json.dumps(packet, ensure_ascii=False, indent=2)
    if getattr(args, "output", None):
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


def _configured_model_settings(args: argparse.Namespace) -> ModelSettings:
    """Load GUI-shared profiles and apply a transient CLI reasoning override."""

    settings = load_model_settings()
    settings.enabled = True
    profile = settings.active_profile()
    reasoning = getattr(args, "reasoning", None)
    if profile is not None and reasoning:
        profile.reasoning = reasoning
    return settings


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CRIBA command-line interface and return a process exit code."""
    parser = argparse.ArgumentParser(
        prog="criba",
        description="CRIBA Current Engine - 3 modos de innovación:\n"
                   "  1. activate/run: Selección determinista (original)\n"
                   "  2. lottery: Doble lotería (asociativa + pura)\n"
                   "  3. blackforge: Pipeline BLACKFORGE",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--database", default=None, help="Ruta SQLite (por defecto artifacts/criba.sqlite3)")
    sub = parser.add_subparsers(dest="command", required=True)

    def activation(name: str) -> argparse.ArgumentParser:
        command_parser = sub.add_parser(name)
        command_parser.add_argument("--query")
        command_parser.add_argument("--file")
        command_parser.add_argument("--current", default="auto")
        command_parser.add_argument("--mode", default="balanced")
        command_parser.add_argument("--supporting-methods", type=int, default=8)
        command_parser.add_argument("--llm", choices=["none", "offline", "cloud"],
                                   default="none", help="Modo LLM: none (determinista), offline (Ollama), cloud (API)")
        command_parser.add_argument("--llm-model", default=None, help="Nombre del modelo LLM")
        command_parser.add_argument("--llm-url", default=None, help="URL del servidor LLM (Ollama: http://localhost:11434)")
        command_parser.add_argument("--llm-api-key", default=None, help="API key para modo cloud")
        command_parser.add_argument(
            "--use-configured-model",
            action="store_true",
            help="Usa el perfil GGUF/Ollama guardado en la pestaña Modelos IA",
        )
        command_parser.add_argument(
            "--reasoning",
            choices=["fast", "balanced", "deep"],
            default=None,
            help="Sobrescribe temporalmente el reasoning del perfil configurado",
        )
        return command_parser

    activation("activate").add_argument("--json", action="store_true")
    activation("run")
    build_parser = activation("build-prompt")
    build_parser.add_argument("--output")
    sub.add_parser("list-currents")
    explain_parser = sub.add_parser("explain")
    explain_parser.add_argument("--session", required=True)
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--session-a", required=True)
    compare_parser.add_argument("--session-b", required=True)
    blackforge_parser = sub.add_parser("blackforge", help="Ejecuta el pipeline BLACKFORGE determinista")
    blackforge_parser.add_argument("--query", help="Consulta que se incluirá en el packet BLACKFORGE")
    blackforge_parser.add_argument("--seed", type=int, default=1)
    blackforge_parser.add_argument("--session-size", type=int, default=12)
    blackforge_parser.add_argument("--profile", default="hybrid")
    blackforge_parser.add_argument("--session-id", default="blackforge-cli")
    blackforge_parser.add_argument(
        "--use-configured-model",
        action="store_true",
        help="Redacta las ideas con el perfil GGUF/Ollama compartido con la GUI",
    )
    blackforge_parser.add_argument(
        "--enhance-semantics",
        action="store_true",
        help="Sintetiza los resultados con el LLM local (resumen + semillas evolutivas)",
    )
    blackforge_parser.add_argument(
        "--reasoning", choices=["fast", "balanced", "deep"], default=None
    )
    # Hybrid pipeline command
    hybrid_parser = sub.add_parser("hybrid", help="Pipeline híbrido completo (ensemble -> cadena -> adversarial + opcional LLM)")
    hybrid_parser.add_argument("--query", required=True, help="Pregunta o problema a analizar")
    hybrid_parser.add_argument(
        "--enhance-semantics",
        action="store_true",
        help="Sintetiza los resultados con el LLM local (resumen + semillas evolutivas)",
    )
    hybrid_parser.add_argument(
        "--reasoning", choices=["fast", "balanced", "deep"], default=None
    )
    # Lottery command
    lottery_parser = sub.add_parser("lottery", help="Ejecuta la Doble Lotería: Asociativa + Pura")
    lottery_parser.add_argument("--query", help="Consulta para modo asociativo")
    lottery_parser.add_argument("--rounds", type=int, default=20, help="Número de rondas")
    lottery_parser.add_argument("--batch-size", type=int, default=20, help="Métodos por ronda")
    lottery_parser.add_argument("--mode", choices=["optimized", "alternating", "associative", "pure"],
                               default="alternating", help="Modo de lotería")
    lottery_parser.add_argument("--seed", type=int, default=42, help="Semilla aleatoria")
    lottery_parser.add_argument("--methods-file", default=None,
                               help="Ruta al archivo de métodos JSON")
    lottery_parser.add_argument(
        "--output-dir",
        default=None,
        help="Directorio de resultados (por defecto, datos locales del usuario)",
    )

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    sub.add_parser("mcp")
    sub.add_parser("gui")
    sub.add_parser("blackforge-gui", help="Lanza la aplicación de escritorio nativa BLACKFORGE")
    args = parser.parse_args(argv)

    try:
        if args.command in {"activate", "run"}:
            return _run(args)
        if args.command == "build-prompt":
            return _run(args, True)
        if args.command == "list-currents":
            print(json.dumps(currents(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "explain":
            print(json.dumps(Storage(args.database).get(args.session), ensure_ascii=False, indent=2))
            return 0
        if args.command == "compare":
            print(json.dumps(Storage(args.database).compare(args.session_a, args.session_b), ensure_ascii=False, indent=2))
            return 0
        if args.command == "blackforge":
            from .blackforge_pipeline import run_headless

            if args.query is None:
                packet = run_headless(
                    seed=args.seed,
                    session_size=args.session_size,
                    profile=args.profile,
                    session_id=args.session_id,
                )
            else:
                packet = run_headless(
                    query=args.query,
                    seed=args.seed,
                    session_size=args.session_size,
                    profile=args.profile,
                    session_id=args.session_id,
                )
            if args.use_configured_model:
                raw_ideas = packet.get("ideas", [])
                if isinstance(raw_ideas, list):
                    enhanced, semantic = enhance_ideas_with_model(
                        str(packet.get("query") or args.query or ""),
                        [idea for idea in raw_ideas if isinstance(idea, dict)],
                        product="BLACKFORGE",
                        settings=_configured_model_settings(args),
                    )
                    packet["ideas"] = enhanced
                    packet["semantic_generation"] = semantic
            print(json.dumps(packet, ensure_ascii=False, indent=2))
            return 0
        if args.command == "serve":
            from .api import serve

            serve(args.host, args.port, args.database)
            return 0
        if args.command == "mcp":
            from .mcp_server import run_stdio

            run_stdio(args.database)
            return 0
        if args.command == "lottery":
            from .lottery import run_lottery

            methods_file = args.methods_file
            if methods_file is not None and not Path(methods_file).is_file():
                print(f"Error: No se encontró el archivo de métodos: {methods_file}", file=sys.stderr)
                return 1

            run_lottery(
                methods_file=methods_file,
                rounds=args.rounds,
                batch_size=args.batch_size,
                mode=args.mode,
                seed=args.seed,
                query=args.query,
                output_dir=args.output_dir,
            )
            return 0

        if args.command == "gui":
            from .gui import run

            result = run(args.database)
            return result if isinstance(result, int) else 0

        if args.command in {"blackforge-gui", "blackforge_gui"}:
            from PySide6.QtWidgets import QApplication
            from .ui.blackforge_window import BlackforgeWindow

            app = QApplication.instance() or QApplication(sys.argv)
            win = BlackforgeWindow()
            win.show()
            return app.exec()
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Comando desconocido: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
