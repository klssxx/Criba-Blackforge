# First run: CRIBA + BLACKFORGE

## 1. Download and open

1. Download `CRIBA-Blackforge-Portable-Windows-x64.zip` from the
   [latest release](https://github.com/klssxx/Criba-Blackforge/releases/latest).
2. Compare the ZIP SHA-256 with the `.sha256` file from the same release:

   ```powershell
   Get-FileHash -Algorithm SHA256 .\CRIBA-Blackforge-Portable-Windows-x64.zip
   ```

3. Extract the **entire** ZIP to a folder such as `C:\CRIBA-Blackforge`.
4. Open `CRIBA.exe`. Do not run it from inside the ZIP preview.

Windows may display SmartScreen because the executable is not signed yet. Only
continue when the hash matches the value published on GitHub.

## 2. Try CRIBA

1. Enter a specific problem or decision.
2. Select **Generar** to create alternatives.
3. Select **Evaluar** to see the ranking and recommendation.
4. Select **Guardar** if you want to keep the session.

CRIBA proposes and compares ideas. It does not replace real-world validation or
human judgment.

## 3. Open BLACKFORGE

Select **Blackforge** in CRIBA's left menu. The second window of the same product
will open. Choose a generation mode and select **Ejecutar generación**. CRIBA
will reappear when BLACKFORGE closes.

## 4. Optional command line

```powershell
.\CRIBA-CLI.exe --help
.\CRIBA-CLI.exe blackforge --query "Analyze a hypothesis" --seed 11
```

## If the app does not open

- Make sure you extracted the `_internal` folder too.
- Do not move an `.exe` outside the portable folder.
- Check whether antivirus quarantined a file.
- Keep `CRIBA.exe` and `BLACKFORGE.exe` in the same directory.

Local data is stored in `%LOCALAPPDATA%\CRIBA-Blackforge\criba.sqlite3`.
