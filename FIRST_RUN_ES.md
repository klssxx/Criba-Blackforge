# Primer uso de CRIBA + BLACKFORGE

## 1. Descargar y abrir

1. Descarga `CRIBA-Blackforge-Portable-Windows-x64.zip` desde la
   [última release](https://github.com/klssxx/Criba-Blackforge/releases/latest).
2. Compara el SHA-256 del ZIP con el archivo `.sha256` de la misma release:

   ```powershell
   Get-FileHash -Algorithm SHA256 .\CRIBA-Blackforge-Portable-Windows-x64.zip
   ```

3. Extrae **todo** el ZIP a una carpeta, por ejemplo `C:\CRIBA-Blackforge`.
4. Abre `CRIBA.exe`. No lo ejecutes directamente desde dentro del ZIP.

Windows puede mostrar SmartScreen porque el ejecutable todavía no está firmado.
Continúa sólo si el hash coincide con el publicado en GitHub.

## 2. Probar CRIBA

1. Escribe un problema o una decisión concreta.
2. Pulsa **Generar** para crear alternativas.
3. Pulsa **Evaluar** para ver el ranking y la recomendación.
4. Pulsa **Guardar** si quieres conservar la sesión.

CRIBA propone y compara ideas; no sustituye una validación real ni el criterio
de la persona que toma la decisión.

## 3. Abrir BLACKFORGE

Pulsa **Blackforge** en el menú izquierdo de CRIBA. Se abrirá la segunda ventana
del mismo producto. Elige un modo de generación y pulsa **Ejecutar generación**.
Al cerrar BLACKFORGE, CRIBA vuelve a mostrarse.

## 4. Consola opcional

```powershell
.\CRIBA-CLI.exe --help
.\CRIBA-CLI.exe blackforge --query "Analizar una hipótesis" --seed 11
```

## Si algo no abre

- Comprueba que extrajiste también la carpeta `_internal`.
- No muevas un `.exe` fuera de la carpeta portable.
- Revisa si el antivirus puso algún archivo en cuarentena.
- Conserva `CRIBA.exe` y `BLACKFORGE.exe` en el mismo directorio.

Los datos locales se guardan en
`%LOCALAPPDATA%\CRIBA-Blackforge\criba.sqlite3`.
