# Operación de releases seguras

El repositorio usa dos flujos versionados:

- `CI`: valida pull requests y `main` con tests, mypy, `actionlint`,
  `pip-audit` y Trivy. El check que debe exigirse es `ci-result`.
- `Portable Windows release`: al publicar un GitHub Release crea una única vez
  el ZIP portable, su SHA-256 y SBOM CycloneDX; atesta el ZIP y publica los
  mismos ficheros como assets del release.

## Plataforma de automatización

Todos los jobs ejecutan PowerShell sobre el runner Windows x64 fijo
`windows-2025`. GitHub ofrece esa etiqueta Windows estable para x64; para usar
un equipo propio con Windows 10 o Windows 11 habría que registrarlo como
runner autoalojado. No se debe usar un runner personal para pull requests de
origen no confiable.

## Configuración única en GitHub

Un administrador debe configurar estos controles fuera del repositorio antes
de considerar la entrega lista para producción:

1. Crear un ruleset para `main`: pull request obligatorio, una revisión,
   descartar aprobaciones obsoletas, rama actualizada, sin force-push ni
   borrado, y el check obligatorio `ci-result`.
2. Exigir revisión de CODEOWNERS para `.github/workflows/**`,
   `.github/dependabot.yml`, `pyproject.toml`, `uv.lock` y los scripts de
   release protegidos en `.github/CODEOWNERS`.
3. Proteger etiquetas `v*`: solo mantenedores pueden crearlas; no se permiten
   actualizaciones forzadas ni borrados.
4. Crear el entorno GitHub `release`, con aprobación manual de un mantenedor.
   El único job con `contents: write` usa ese entorno para adjuntar assets al
   release ya publicado.

No se usan PATs ni credenciales cloud. Los trabajos de validación tienen solo
`contents: read`; los permisos OIDC se limitan al job que genera la atestación.

## Publicar

1. Actualiza el número de versión y `uv.lock` en un pull request verde.
2. Crea una etiqueta inmutable con formato `vMAJOR.MINOR.PATCH` y publica el
   GitHub Release asociado.
3. Aprueba el entorno `release` cuando el job de atestación haya terminado.
4. Comprueba que el release contiene el ZIP, `.sha256` y `.cdx.json`. Verifica
   el ZIP con:

   ```powershell
   Get-FileHash -Algorithm SHA256 .\CRIBA-Blackforge-Portable-Windows-x64.zip
   ```

   El hash debe coincidir con el fichero `.sha256` adjunto.

## Rollback

No se sobrescribe un asset publicado como corrección. Si un release es
defectuoso, márcalo como pre-release o retíralo de la distribución, abre el
incidente con la URL del workflow y publica una nueva etiqueta inmutable con
la corrección. Conserva la evidencia del workflow, el SHA-256 y el motivo del
rollback.
