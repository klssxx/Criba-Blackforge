"""Motores de selección optimizada y lotería para CRIBA/BLACKFORGE."""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

from .constants import DATA_ROOT
from .storage import Storage

VALID_LOTTERY_MODES = {"optimized", "associative", "pure", "alternating"}


def _console_safe(value: object) -> str:
    """Replace characters unsupported by the active console encoding."""
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def default_methods_file() -> Path:
    """Return the catalog bundled with source checkouts and portable builds."""
    return DATA_ROOT / "methods" / "library_combined.json"


def default_output_dir() -> Path:
    """Return a writable, machine-independent directory for lottery results."""
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "CRIBA-Blackforge" / "lottery_results"


class LotteryEngine:
    """Select and combine methods without repeating them between rounds."""

    def __init__(self, methods_file: str, seed: int = 42, storage: Storage | None = None):
        self.methods = self._load_methods(methods_file)
        self.used_combos: set[tuple[str, str]] = set()
        self.used_methods: set[str] = set()
        self.all_ideas: list[dict[str, Any]] = []
        self.round_history: list[dict[str, Any]] = []
        self.last_round_ideas: list[dict[str, Any]] = []
        self.rng = random.Random(seed)
        self.round_number = 0
        self.storage = storage
        if self.storage is not None:
            self.sync_storage(self.storage)

    @property
    def catalog_fingerprint(self) -> str:
        """Compute a deterministic SHA-256 fingerprint of all active catalog IDs."""
        ids_sorted = sorted(str(m["id"]) for m in self.methods)
        return hashlib.sha256(",".join(ids_sorted).encode("utf-8")).hexdigest()

    def sync_storage(self, storage: Storage | None = None) -> None:
        """Load historically used combinations from SQLite store into memory."""
        self.storage = storage or Storage()
        loaded = self.storage.load_used_lottery_combinations(self.catalog_fingerprint)
        self.used_combos.update(loaded)

    @staticmethod
    def _normalize_method(item: dict[str, Any]) -> dict[str, Any]:
        """Normalize CRIBA and BLACKFORGE records to the lottery contract."""
        normalized = dict(item)
        method_id = str(
            normalized.get("id")
            or normalized.get("blackforge_id")
            or normalized.get("name")
            or normalized.get("title")
            or ""
        ).strip()
        title = str(normalized.get("title") or normalized.get("name") or method_id).strip()
        if not method_id or not title:
            raise ValueError("Cada método debe tener id/nombre y título.")
        normalized["id"] = method_id
        normalized["name"] = str(normalized.get("name") or method_id).strip()
        normalized["title"] = title
        normalized["description"] = str(
            normalized.get("description")
            or normalized.get("template")
            or normalized.get("selection_reason")
            or ""
        ).strip()
        normalized["family"] = str(
            normalized.get("family")
            or normalized.get("functional_category_primary")
            or normalized.get("source_family")
            or normalized.get("source")
            or "general"
        ).strip()
        return normalized

    @classmethod
    def _normalize_methods(
        cls, methods: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        normalized = [cls._normalize_method(item) for item in methods]
        if not normalized:
            raise ValueError("El catálogo de métodos no puede estar vacío.")
        ids = [str(method["id"]) for method in normalized]
        duplicate_ids = sorted(
            method_id for method_id, count in Counter(ids).items() if count > 1
        )
        if duplicate_ids:
            sample = ", ".join(duplicate_ids[:5])
            raise ValueError(f"El catálogo contiene ID duplicado: {sample}")
        return normalized

    @classmethod
    def _load_methods(cls, filepath: str) -> list[dict[str, Any]]:
        """Carga métodos desde JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            payload: Any = json.load(f)
        if not isinstance(payload, list) or not all(
            isinstance(item, dict) for item in payload
        ):
            raise ValueError("El archivo de métodos debe contener una lista JSON.")
        return cls._normalize_methods(payload)

    @classmethod
    def from_methods(
        cls, methods: list[dict[str, Any]], seed: int = 42, storage: Storage | None = None
    ) -> LotteryEngine:
        """Construye el motor desde una lista de métodos ya cargada en memoria.

        Evita leer un archivo (el catálogo de BLACKFORGE es una lista de dicts
        inmutable, no un JSON en disco). Es el camino limpio que usa la pantalla
        BLACKFORGE en lugar de parchear atributos con ``__new__``.
        """
        eng = cls.__new__(cls)
        eng.methods = cls._normalize_methods(methods)
        eng.used_combos = set()
        eng.used_methods = set()
        eng.all_ideas = []
        eng.round_history = []
        eng.last_round_ideas = []
        eng.rng = random.Random(seed)
        eng.round_number = 0
        eng.storage = storage
        if eng.storage is not None:
            eng.sync_storage(eng.storage)
        return eng

    def get_available_methods(self) -> list[dict[str, Any]]:
        """Retorna métodos no usados aún."""
        return [m for m in self.methods if m['id'] not in self.used_methods]

    def select_optimized_batch(self, size: int = 20) -> list[dict[str, Any]]:
        """Select the strongest available records while preserving family diversity."""
        if size < 1:
            raise ValueError("El tamaño del lote debe ser positivo.")
        available = self.get_available_methods()

        def rank(method: dict[str, Any]) -> tuple[float, str]:
            raw_score = method.get(
                "quality_score_v2",
                method.get("quality_score", method.get("selection_weight", 0)),
            )
            try:
                score = float(raw_score or 0)
            except (TypeError, ValueError):
                score = 0.0
            return (-score, str(method["id"]))

        ranked = sorted(available, key=rank)
        selected: list[dict[str, Any]] = []
        families: set[str] = set()
        for method in ranked:
            family = str(method["family"])
            if family in families:
                continue
            selected.append(method)
            families.add(family)
            if len(selected) >= size:
                return selected
        selected_ids = {method["id"] for method in selected}
        selected.extend(method for method in ranked if method["id"] not in selected_ids)
        return selected[:size]

    def select_random_batch(self, size: int = 20) -> list[dict[str, Any]]:
        """Selecciona un lote ALEATORIO de métodos (lotería pura)."""
        if size < 1:
            raise ValueError("El tamaño del lote debe ser positivo.")
        available = self.get_available_methods()
        if len(available) < size:
            return available
        return self.rng.sample(available, size)

    def select_associative_batch(
        self,
        size: int = 20,
        theme: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """Selecciona métodos buscando ASOCIACIONES temáticas (lotería asociativa)."""
        if size < 1:
            raise ValueError("El tamaño del lote debe ser positivo.")
        available = self.get_available_methods()
        if len(available) < size:
            return available

        selected: list[dict[str, Any]] = []

        # Usar query o theme para buscar asociaciones por términos. Una frase
        # completa rara vez aparece literalmente en un catálogo heterogéneo.
        search_term = query or theme
        if search_term:
            phrase = search_term.casefold().strip()
            terms = {
                token
                for token in re.findall(r"[\wáéíóúüñ]+", phrase)
                if len(token) >= 4
            }

            def association_score(method: dict[str, Any]) -> int:
                text = " ".join(
                    str(method.get(field, ""))
                    for field in ("title", "description", "family", "tags")
                ).casefold()
                return (len(terms) + 1 if phrase and phrase in text else 0) + sum(
                    term in text for term in terms
                )

            scored = [
                (association_score(method), method) for method in available
            ]
            related = sorted(
                (item for score, item in scored if score > 0),
                key=lambda item: str(item["id"]),
            )
            if related:
                # Favorecer relevancia sin convertir la lotería en un ranking
                # rígido: sortear dentro del mejor subconjunto relacionado.
                related.sort(key=association_score, reverse=True)
                candidate_pool = related[: max(size, size * 4)]
                selected = self.rng.sample(
                    candidate_pool, min(size, len(candidate_pool))
                )
                if len(selected) >= size:
                    return selected

        # Completar —o resolver una consulta sin coincidencias— por familias.
        families = sorted({str(m['family']) for m in available})
        selected_families: set[str] = set()
        selected_ids = {str(method["id"]) for method in selected}
        selected_families.update(str(method["family"]) for method in selected)

        # Tomar 1 de cada familia primero (diversidad)
        for fam in families:
            if fam in selected_families:
                continue
            fam_methods = [
                method
                for method in available
                if method['family'] == fam and str(method["id"]) not in selected_ids
            ]
            if fam_methods:
                chosen = self.rng.choice(fam_methods)
                selected.append(chosen)
                selected_ids.add(str(chosen["id"]))
                selected_families.add(fam)
                if len(selected) >= size:
                    break

        # Completar con aleatorios
        remaining = [
            method for method in available if str(method["id"]) not in selected_ids
        ]
        if remaining and len(selected) < size:
            extra = self.rng.sample(remaining, min(size - len(selected), len(remaining)))
            selected.extend(extra)

        return selected[:size]

    def generate_ideas_from_batch(
        self, batch: list[dict[str, Any]], mode: str = "associative"
    ) -> list[dict[str, Any]]:
        """Genera ideas de un lote de métodos y persiste los pares usados en SQLite."""
        ideas: list[dict[str, Any]] = []
        pairs = list(combinations(batch, 2))
        new_combos: list[tuple[str, str]] = []

        for m1, m2 in pairs:
            left_id, right_id = sorted((str(m1['id']), str(m2['id'])))
            combo_key = (left_id, right_id)

            # No repetir combinaciones
            if combo_key in self.used_combos:
                continue

            self.used_combos.add(combo_key)
            new_combos.append(combo_key)

            # Generar idea
            idea = self._create_idea(m1, m2, mode)
            ideas.append(idea)
            self.all_ideas.append(idea)

        if hasattr(self, "storage") and self.storage is not None and new_combos:
            self.storage.save_lottery_combinations(
                self.catalog_fingerprint,
                new_combos,
                run_id=f"run-{self.round_number}",
                mode=mode,
            )

        return ideas

    def _create_idea(
        self, m1: dict[str, Any], m2: dict[str, Any], mode: str
    ) -> dict[str, Any]:
        """Crea una idea a partir de dos métodos usando el motor real de CRIBA."""
        from .engine import _BASE_VALUES, _evaluate_idea

        # Generar título descriptivo
        if mode == "associative":
            title = f"{m1['title'][:30]} -> {m2['title'][:30]}"
            description = f"Asociar '{m1['family']}' con '{m2['family']}'"
        else:
            title = f"{m1['title'][:30]} x {m2['title'][:30]}"
            description = f"Combinar '{m1['family']}' + '{m2['family']}'"

        # Construir idea dict para el motor real de CRIBA
        # Simular causal_variables basado en las familias de los métodos
        fam1 = m1.get('family', 'verificacion')
        fam2 = m2.get('family', 'verificacion')

        # Mapeo familia → eje causal (simplificado)
        family_to_axis = {
            'inversion': 'quien_decide',
            'diagnostico': 'evidencia_requerida',
            'sustraccion': 'si_falla',
            'restricciones': 'cuando',
            'actores_roles': 'quien_decide',
            'incentivos': 'evidencia_requerida',
            'morfologia': 'topologia',
            'recombinacion': 'topologia',
            'analogias': 'evidencia_requerida',
            'arquitectura': 'topologia',
            'gobernanza': 'quien_decide',
            'diseno_adversarial': 'si_falla',
            'escenarios': 'cuando',
            'prototipado': 'cuando',
            'verificacion': 'evidencia_requerida',
            'decision_riesgo': 'si_falla',
        }

        # Crear causal_variables: mover ejes basado en las familias
        cv = dict(_BASE_VALUES)
        axis1 = family_to_axis.get(fam1, 'evidencia_requerida')
        axis2 = family_to_axis.get(fam2, 'evidencia_requerida')

        # Aplicar valores diferentes para simular divergencia
        axis_values = {
            'quien_decide': ['externo', 'comunidad', 'algoritmo'],
            'cuando': ['antes', 'durante', 'despues'],
            'evidencia_requerida': ['reproducible', 'testable', 'adversarial'],
            'si_falla': ['aislado', 'reversible', 'degradado'],
            'topologia': ['distribuida', 'descentralizada', 'federada'],
        }

        if axis1 in axis_values:
            cv[axis1] = self.rng.choice(axis_values[axis1])
        if axis2 in axis_values and axis2 != axis1:
            cv[axis2] = self.rng.choice(axis_values[axis2])

        # Construir idea para el motor CRIBA
        idea_for_engine = {
            'causal_variables': cv,
            'method1_name': m1['title'][:60],
            'method2_name': m2['title'][:60],
            'method1_desc': m1.get('description', '')[:200],
            'method2_desc': m2.get('description', '')[:200],
            'family': fam1,
            'family2': fam2,
            'extreme': self.rng.random() < 0.2,  # 20% chance de extremo
        }

        # Usar el motor real de CRIBA para scoring
        conv = _evaluate_idea(idea_for_engine)
        score = conv['value_score']

        # Clasificar calidad basado en el score real
        if score >= 0.9:
            quality = "EXTRAORDINARIA"
        elif score >= 0.7:
            quality = "BUENA"
        else:
            quality = "BASURA"

        return {
            'title': title,
            'description': description,
            'method1': m1['title'][:60],
            'method2': m2['title'][:60],
            'family1': fam1,
            'family2': fam2,
            'quality': quality,
            'score': round(score, 3),
            'mode': mode,
            'round': self.round_number,
            'convergence': conv,
        }

    def run_round(
        self,
        mode: str = "alternating",
        batch_size: int = 20,
        query: str | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una ronda de lotería."""
        if mode not in VALID_LOTTERY_MODES:
            raise ValueError(f"Modo de lotería inválido: {mode}")
        if batch_size < 2:
            raise ValueError("El lote debe contener al menos dos métodos.")
        if len(self.get_available_methods()) < 2:
            raise ValueError("No quedan al menos dos métodos sin usar.")
        self.round_number += 1

        # Seleccionar lote según modo
        if mode == "optimized":
            batch = self.select_optimized_batch(batch_size)
            selected_mode = "optimized"
        elif mode == "associative" or (mode == "alternating" and self.round_number % 2 == 1):
            batch = self.select_associative_batch(batch_size, query=query)
            selected_mode = "associative"
        else:
            batch = self.select_random_batch(batch_size)
            selected_mode = "pure"

        # Marcar métodos como usados
        for m in batch:
            self.used_methods.add(m['id'])

        # Generar ideas
        ideas = self.generate_ideas_from_batch(batch, selected_mode)
        self.last_round_ideas = ideas

        # Estadísticas de la ronda
        stats = {
            'round': self.round_number,
            'mode': selected_mode,
            'methods_used': len(batch),
            'ideas_generated': len(ideas),
            'extraordinary': sum(1 for i in ideas if i['quality'] == 'EXTRAORDINARIA'),
            'good': sum(1 for i in ideas if i['quality'] == 'BUENA'),
            'trash': sum(1 for i in ideas if i['quality'] == 'BASURA'),
            'families': sorted({str(m['family']) for m in batch}),
            'method_ids': [str(m['id']) for m in batch],
        }

        self.round_history.append(stats)
        return stats

    def run_tournament(
        self,
        total_rounds: int = 10,
        batch_size: int = 20,
        mode: str = "alternating",
        query: str | None = None,
    ) -> dict[str, Any]:
        """Ejecuta un torneo completo de lotería."""
        if total_rounds < 1:
            raise ValueError("El torneo debe tener al menos una ronda.")
        print("=" * 60)
        print("DOBLE LOTERIA DE CRIBA")
        print("=" * 60)
        print()
        print("Modo: " + ("Asociativa + Pura (alternando)" if mode == "alternating" else mode))
        print("Métodos por ronda: " + str(batch_size))
        print("Total rondas: " + str(total_rounds))
        if query:
            print(_console_safe("Query: " + query[:50] + "..."))
        print()

        for _ in range(total_rounds):
            stats = self.run_round(mode, batch_size, query=query)
            self._print_round_stats(stats)

        return self._get_summary()

    def _print_round_stats(self, stats: dict[str, Any]) -> None:
        """Imprime estadísticas de una ronda."""
        mode_label = {
            "optimized": "OPT",
            "associative": "ASC",
            "pure": "RND",
        }[stats['mode']]
        print(f"Ronda {stats['round']:3d} {mode_label} {stats['mode']:12s} | "
              f"Ideas: {stats['ideas_generated']:4d} | "
              f"Extra: {stats['extraordinary']:2d} | "
              f"Buenas: {stats['good']:3d} | "
              f"Basura: {stats['trash']:3d}")

    def _get_summary(self) -> dict[str, Any]:
        """Retorna resumen del torneo."""
        total_ideas = len(self.all_ideas)
        extraordinary = sum(1 for i in self.all_ideas if i['quality'] == 'EXTRAORDINARIA')
        good = sum(1 for i in self.all_ideas if i['quality'] == 'BUENA')
        trash = sum(1 for i in self.all_ideas if i['quality'] == 'BASURA')

        summary: dict[str, Any] = {
            'total_rounds': self.round_number,
            'total_methods_used': len(self.used_methods),
            'total_methods_available': len(self.methods),
            'total_combinations_tested': len(self.used_combos),
            'total_ideas': total_ideas,
            'extraordinary_ideas': extraordinary,
            'good_ideas': good,
            'trash_ideas': trash,
            'coverage_percent': round(len(self.used_methods) / len(self.methods) * 100, 1),
            'extraordinary_percent': round(extraordinary / total_ideas * 100, 1) if total_ideas > 0 else 0,
            'top_ideas': sorted(self.all_ideas, key=lambda x: x['score'], reverse=True)[:10]
        }

        print()
        print("=" * 60)
        print("RESUMEN DEL TORNEO")
        print("=" * 60)
        print(f"Rondas ejecutadas: {summary['total_rounds']}")
        print(f"Métodos usados: {summary['total_methods_used']}/{summary['total_methods_available']} ({summary['coverage_percent']}%)")
        print(f"Combinaciones probadas: {summary['total_combinations_tested']:,}")
        print()
        print("IDEAS GENERADAS:")
        print(f"  Extraordinarias: {summary['extraordinary_ideas']} ({summary['extraordinary_percent']}%)")
        print(f"  Buenas: {summary['good_ideas']}")
        print(f"  Basura: {summary['trash_ideas']}")
        print(f"  Total: {summary['total_ideas']}")
        print()
        print("TOP 10 IDEAS:")
        for i, idea in enumerate(summary['top_ideas'][:10], 1):
            print(_console_safe(f"  {i}. [{idea['quality']}] {idea['title'][:50]}"))
            print(f"     Score: {idea['score']} | Modo: {idea['mode']}")

        return summary

    def get_top_ideas(self, n: int = 50) -> list[dict[str, Any]]:
        """Retorna las mejores N ideas."""
        return sorted(self.all_ideas, key=lambda x: x['score'], reverse=True)[:n]

    def get_ideas_by_quality(self, quality: str) -> list[dict[str, Any]]:
        """Retorna ideas por calidad."""
        return [i for i in self.all_ideas if i['quality'] == quality]

    def get_family_coverage(self) -> dict[str, int]:
        """Retorna cobertura de familias."""
        coverage: dict[str, int] = {}
        for idea in self.all_ideas:
            for fam in [idea['family1'], idea['family2']]:
                coverage[fam] = coverage.get(fam, 0) + 1
        return dict(sorted(coverage.items(), key=lambda x: -x[1]))

    def save_results(self, output_dir: str | Path) -> None:
        """Guarda resultados del torneo."""
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)

        # Guardar todas las ideas
        with (destination / 'all_ideas.json').open('w', encoding='utf-8') as f:
            json.dump(self.all_ideas, f, ensure_ascii=False, indent=2)

        # Guardar top ideas
        with (destination / 'top_ideas.json').open('w', encoding='utf-8') as f:
            json.dump(self.get_top_ideas(50), f, ensure_ascii=False, indent=2)

        # Guardar extraordinarias
        with (destination / 'extraordinary_ideas.json').open('w', encoding='utf-8') as f:
            json.dump(self.get_ideas_by_quality('EXTRAORDINARIA'), f, ensure_ascii=False, indent=2)

        # Guardar historial
        with (destination / 'round_history.json').open('w', encoding='utf-8') as f:
            json.dump(self.round_history, f, ensure_ascii=False, indent=2)

        # Guardar cobertura
        with (destination / 'family_coverage.json').open('w', encoding='utf-8') as f:
            json.dump(self.get_family_coverage(), f, ensure_ascii=False, indent=2)

        print(_console_safe(f"Resultados guardados en: {destination}"))


def run_lottery(methods_file: str | None = None, rounds: int = 20, batch_size: int = 20,
                mode: str = "alternating", seed: int = 42,
                query: str | None = None,
                output_dir: str | Path | None = None) -> dict[str, Any]:
    """Función principal para ejecutar la lotería."""
    if methods_file is None:
        from .catalog import methods

        engine = LotteryEngine.from_methods(methods(), seed)
    else:
        engine = LotteryEngine(methods_file, seed)
    summary = engine.run_tournament(rounds, batch_size, mode, query=query)
    destination = Path(output_dir) if output_dir is not None else default_output_dir()
    engine.save_results(destination)
    summary["output_dir"] = str(destination)
    return summary


if __name__ == "__main__":
    run_lottery(rounds=20, batch_size=20, mode="alternating")
