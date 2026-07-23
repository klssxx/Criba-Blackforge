CRIBA + BLACKFORGE v2 — PAQUETE DE IMPLEMENTACIÓN
==================================================

DESTINO RECOMENDADO
-------------------
Copia el contenido de este ZIP dentro de:

E:\PROYECTS\CRIBA

La carpeta quedará así:

E:\PROYECTS\CRIBA\
├── HIPER_MEGAPROMPT_CRIBA_BLACKFORGE_V2.txt
└── imports\blackforge_v2\
    ├── criba_blackforge_catalogo_final_debate20.json
    ├── criba_blackforge_politicas_v2.json
    ├── causal_engine.py
    ├── test_causal_engine.py
    ├── criba_blackforge_debate_20_rondas.md
    ├── criba_blackforge_cambios_debate20.csv
    ├── criba_blackforge_catalogo_final_debate20.csv
    └── criba_blackforge_catalogo_final_debate20.xlsx

ORDEN DE USO
------------
1. Extrae el ZIP en E:\PROYECTS\CRIBA.
2. Abre una sesión nueva de Hermes/HY3 en esa ruta.
3. Pega el contenido de HIPER_MEGAPROMPT_CRIBA_BLACKFORGE_V2.txt.
4. Deja que Hermes lea los archivos desde disco.
5. No pegues los cuatro catálogos originales completos en el chat.
6. El JSON final es la fuente canónica de los 723 registros.
7. El JSON de políticas es la fuente canónica de seguridad y selección.
8. causal_engine.py y test_causal_engine.py son referencia y gate inicial.

NOTA
----
Los cuatro TXT originales de 800/1000/800/600 elementos no se incluyen porque
no son necesarios para integrar la versión consolidada. Solo harían falta para
una nueva auditoría de procedencia.
