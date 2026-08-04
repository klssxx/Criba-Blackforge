"""Sistema de Doble Lotería para CRIBA: Asociativa + Pura, alternando para máxima diversión."""
from __future__ import annotations
import json
import os
import random
from itertools import combinations
from typing import Any


class LotteryEngine:
    """Motor de doble lotería que explota TODOS los métodos sin repetir combinaciones."""

    def __init__(self, methods_file: str, seed: int = 42):
        self.methods = self._load_methods(methods_file)
        self.used_combos: set[tuple[str, str]] = set()
        self.used_methods: set[str] = set()
        self.all_ideas: list[dict[str, Any]] = []
        self.round_history: list[dict[str, Any]] = []
        self.rng = random.Random(seed)
        self.round_number = 0

    def _load_methods(self, filepath: str) -> list[dict[str, Any]]:
        """Carga métodos desde JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            payload: Any = json.load(f)
        if not isinstance(payload, list) or not all(
            isinstance(item, dict) for item in payload
        ):
            raise ValueError("El archivo de métodos debe contener una lista JSON.")
        return [dict(item) for item in payload]

    @classmethod
    def from_methods(
        cls, methods: list[dict[str, Any]], seed: int = 42
    ) -> "LotteryEngine":
        """Construye el motor desde una lista de métodos ya cargada en memoria.

        Evita leer un archivo (el catálogo de BLACKFORGE es una lista de dicts
        inmutable, no un JSON en disco). Es el camino limpio que usa la pantalla
        BLACKFORGE en lugar de parchear atributos con ``__new__``.
        """
        eng = cls.__new__(cls)
        eng.methods = methods
        eng.used_combos = set()
        eng.used_methods = set()
        eng.all_ideas = []
        eng.round_history = []
        eng.rng = random.Random(seed)
        eng.round_number = 0
        return eng

    def get_available_methods(self) -> list[dict[str, Any]]:
        """Retorna métodos no usados aún."""
        return [m for m in self.methods if m['name'] not in self.used_methods]

    def select_random_batch(self, size: int = 20) -> list[dict[str, Any]]:
        """Selecciona un lote ALEATORIO de métodos (lotería pura)."""
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
        available = self.get_available_methods()
        if len(available) < size:
            return available

        # Usar query o theme para buscar asociaciones
        search_term = query or theme
        if search_term:
            # Buscar métodos relacionados con el término
            related = [m for m in available if search_term.lower() in
                      (m.get('title', '') + ' ' + m.get('description', '') + ' ' + m.get('family', '')).lower()]
            if len(related) >= size:
                return self.rng.sample(related, size)
            # Si no hay suficientes, mezclar con otros
            remaining = [m for m in available if m not in related]
            extra = self.rng.sample(remaining, min(size - len(related), len(remaining)))
            return related + extra

        # Si no hay suficientes relacionados, mezclar
        families = list(set(m['family'] for m in available))
        selected: list[dict[str, Any]] = []
        selected_families: set[str] = set()

        # Tomar 1 de cada familia primero (diversidad)
        for fam in families:
            fam_methods = [m for m in available if m['family'] == fam and m['name'] not in
                          [s['name'] for s in selected]]
            if fam_methods:
                selected.append(self.rng.choice(fam_methods))
                selected_families.add(fam)
                if len(selected) >= size:
                    break

        # Completar con aleatorios
        remaining = [m for m in available if m['name'] not in [s['name'] for s in selected]]
        if remaining and len(selected) < size:
            extra = self.rng.sample(remaining, min(size - len(selected), len(remaining)))
            selected.extend(extra)

        return selected[:size]

    def generate_ideas_from_batch(
        self, batch: list[dict[str, Any]], mode: str = "associative"
    ) -> list[dict[str, Any]]:
        """Genera ideas de un lote de métodos."""
        ideas: list[dict[str, Any]] = []
        pairs = list(combinations(batch, 2))

        for m1, m2 in pairs:
            combo_key = tuple(sorted([m1['title'], m2['title']]))

            # No repetir combinaciones
            if combo_key in self.used_combos:
                continue

            self.used_combos.add(combo_key)

            # Generar idea
            idea = self._create_idea(m1, m2, mode)
            ideas.append(idea)
            self.all_ideas.append(idea)

        return ideas

    def _create_idea(
        self, m1: dict[str, Any], m2: dict[str, Any], mode: str
    ) -> dict[str, Any]:
        """Crea una idea a partir de dos métodos usando el motor real de CRIBA."""
        from .engine import _BASE_VALUES, _evaluate_idea

        # Generar título descriptivo
        if mode == "associative":
            title = f"{m1['title'][:30]} → {m2['title'][:30]}"
            description = f"Asociar '{m1['family']}' con '{m2['family']}'"
        else:
            title = f"{m1['title'][:30]} × {m2['title'][:30]}"
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
        self.round_number += 1

        # Seleccionar lote según modo
        if mode == "associative" or (mode == "alternating" and self.round_number % 2 == 1):
            batch = self.select_associative_batch(batch_size, query=query)
            selected_mode = "associative"
        else:
            batch = self.select_random_batch(batch_size)
            selected_mode = "pure"

        # Marcar métodos como usados
        for m in batch:
            self.used_methods.add(m['name'])

        # Generar ideas
        ideas = self.generate_ideas_from_batch(batch, selected_mode)

        # Estadísticas de la ronda
        stats = {
            'round': self.round_number,
            'mode': selected_mode,
            'methods_used': len(batch),
            'ideas_generated': len(ideas),
            'extraordinary': sum(1 for i in ideas if i['quality'] == 'EXTRAORDINARIA'),
            'good': sum(1 for i in ideas if i['quality'] == 'BUENA'),
            'trash': sum(1 for i in ideas if i['quality'] == 'BASURA'),
            'families': list(set(m['family'] for m in batch))
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
        print("=" * 60)
        print("🎰 DOBLE LOTERÍA DE CRIBA 🎰")
        print("=" * 60)
        print("")
        print("Modo: " + ("Asociativa + Pura (alternando)" if mode == "alternating" else mode))
        print("Métodos por ronda: " + str(batch_size))
        print("Total rondas: " + str(total_rounds))
        if query:
            print("Query: " + query[:50] + "...")
        print("")

        for _ in range(total_rounds):
            stats = self.run_round(mode, batch_size, query=query)
            self._print_round_stats(stats)

        return self._get_summary()

    def _print_round_stats(self, stats: dict[str, Any]) -> None:
        """Imprime estadísticas de una ronda."""
        mode_emoji = "🔗" if stats['mode'] == "associative" else "🎲"
        print(f"Ronda {stats['round']:3d} {mode_emoji} {stats['mode']:12s} | "
              f"Ideas: {stats['ideas_generated']:4d} | "
              f"⭐ {stats['extraordinary']:2d} | "
              f"👍 {stats['good']:3d} | "
              f"🗑️  {stats['trash']:3d}")

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

        print("")
        print("=" * 60)
        print("📊 RESUMEN DEL TORNEO")
        print("=" * 60)
        print(f"Rondas ejecutadas: {summary['total_rounds']}")
        print(f"Métodos usados: {summary['total_methods_used']}/{summary['total_methods_available']} ({summary['coverage_percent']}%)")
        print(f"Combinaciones probadas: {summary['total_combinations_tested']:,}")
        print("")
        print("IDEAS GENERADAS:")
        print(f"  ⭐ Extraordinarias: {summary['extraordinary_ideas']} ({summary['extraordinary_percent']}%)")
        print(f"  👍 Buenas: {summary['good_ideas']}")
        print(f"  🗑️  Basura: {summary['trash_ideas']}")
        print(f"  📊 Total: {summary['total_ideas']}")
        print("")
        print("TOP 10 IDEAS:")
        for i, idea in enumerate(summary['top_ideas'][:10], 1):
            print(f"  {i}. [{idea['quality']}] {idea['title'][:50]}")
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

    def save_results(self, output_dir: str) -> None:
        """Guarda resultados del torneo."""
        os.makedirs(output_dir, exist_ok=True)

        # Guardar todas las ideas
        with open(os.path.join(output_dir, 'all_ideas.json'), 'w', encoding='utf-8') as f:
            json.dump(self.all_ideas, f, ensure_ascii=False, indent=2)

        # Guardar top ideas
        with open(os.path.join(output_dir, 'top_ideas.json'), 'w', encoding='utf-8') as f:
            json.dump(self.get_top_ideas(50), f, ensure_ascii=False, indent=2)

        # Guardar extraordinarias
        with open(os.path.join(output_dir, 'extraordinary_ideas.json'), 'w', encoding='utf-8') as f:
            json.dump(self.get_ideas_by_quality('EXTRAORDINARIA'), f, ensure_ascii=False, indent=2)

        # Guardar historial
        with open(os.path.join(output_dir, 'round_history.json'), 'w', encoding='utf-8') as f:
            json.dump(self.round_history, f, ensure_ascii=False, indent=2)

        # Guardar cobertura
        with open(os.path.join(output_dir, 'family_coverage.json'), 'w', encoding='utf-8') as f:
            json.dump(self.get_family_coverage(), f, ensure_ascii=False, indent=2)

        print(f"Resultados guardados en: {output_dir}/")


def run_lottery(methods_file: str, rounds: int = 20, batch_size: int = 20,
                mode: str = "alternating", seed: int = 42,
                query: str | None = None) -> dict[str, Any]:
    """Función principal para ejecutar la lotería."""
    engine = LotteryEngine(methods_file, seed)
    summary = engine.run_tournament(rounds, batch_size, mode, query=query)
    engine.save_results("E:/PROYECTS/CRIBA/verification/lottery_results")
    return summary


if __name__ == "__main__":
    # Ejecutar lotería
    methods_file = "E:/PROYECTS/CRIBA/verification/compose_run/all_methods.json"
    run_lottery(methods_file, rounds=20, batch_size=20, mode="alternating")
