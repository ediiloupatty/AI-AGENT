@echo off
REM ===========================================================================
REM  Pemasang Voca - AI Coding Assistant (perintah: voca) untuk Windows
REM
REM  Cara pakai (CMD), satu baris:
REM    curl -fsSL -o "%TEMP%\voca-install.bat" https://raw.githubusercontent.com/ediiloupatty/voice-coding-assistant/main/install.bat ^&^& "%TEMP%\voca-install.bat"
REM ===========================================================================
setlocal enabledelayedexpansion

set "REPO=https://github.com/ediiloupatty/voice-coding-assistant.git"
set "INSTALL_DIR=%USERPROFILE%\.voca"
set "BIN_DIR=%INSTALL_DIR%\bin"
set "MODEL_BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main/id/id_ID/news_tts/medium"
set "MODEL=id_ID-news_tts-medium"
set "MODEL_EN_BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium"
set "MODEL_EN=en_US-amy-medium"

echo ===========================================
echo   Memasang Voca (perintah: voca)
echo ===========================================

REM --- 1) Prasyarat wajib ---
where python >nul 2>nul || (echo [ERROR] Python belum terpasang. Pasang dari python.org ^(centang "Add to PATH"^). & goto :fail)
where git    >nul 2>nul || (echo [ERROR] Git belum terpasang. Pasang dari git-scm.com. & goto :fail)
where curl   >nul 2>nul || (echo [ERROR] curl tidak ditemukan ^(butuh Windows 10+^). & goto :fail)
where ffmpeg >nul 2>nul || echo [WARN] ffmpeg belum ada - pitch-shift suara dimatikan ^(suara tetap jalan^).

REM --- 2) Unduh / perbarui kode ---
if exist "%INSTALL_DIR%\.git" (
  echo Memperbarui kode...
  git -C "%INSTALL_DIR%" pull --ff-only
) else (
  echo Mengunduh kode ke %INSTALL_DIR% ...
  if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
  git clone --depth 1 "%REPO%" "%INSTALL_DIR%" || (echo [ERROR] Gagal clone repo. & goto :fail)
)

REM --- 3) Virtualenv + dependensi ---
echo Menyiapkan virtualenv dan dependensi ^(bisa beberapa menit^)...
python -m venv "%INSTALL_DIR%\.venv" || (echo [ERROR] Gagal membuat virtualenv. & goto :fail)
"%INSTALL_DIR%\.venv\Scripts\python.exe" -m pip install -q --upgrade pip
"%INSTALL_DIR%\.venv\Scripts\python.exe" -m pip install -q -r "%INSTALL_DIR%\requirements.txt" || (echo [ERROR] Gagal pasang dependensi. & goto :fail)

REM --- 4) Model suara Piper (Indonesia + English) ---
if not exist "%INSTALL_DIR%\models" mkdir "%INSTALL_DIR%\models"
echo Mengunduh model suara Piper Indonesia ^(~60MB^)...
curl -fsSL "%MODEL_BASE%/%MODEL%.onnx"      -o "%INSTALL_DIR%\models\%MODEL%.onnx"
curl -fsSL "%MODEL_BASE%/%MODEL%.onnx.json" -o "%INSTALL_DIR%\models\%MODEL%.onnx.json"
echo Mengunduh model suara Piper English ^(~60MB^)...
curl -fsSL "%MODEL_EN_BASE%/%MODEL_EN%.onnx"      -o "%INSTALL_DIR%\models\%MODEL_EN%.onnx"
curl -fsSL "%MODEL_EN_BASE%/%MODEL_EN%.onnx.json" -o "%INSTALL_DIR%\models\%MODEL_EN%.onnx.json"

REM --- 5) Siapkan .env ---
if not exist "%INSTALL_DIR%\.env" copy "%INSTALL_DIR%\.env.example" "%INSTALL_DIR%\.env" >nul

REM --- 6) Minta API key Qwen / DashScope kalau belum terisi ---
set "KEY_SET="
for /f "usebackq tokens=1,* delims==" %%A in ("%INSTALL_DIR%\.env") do (
  if /i "%%A"=="DASHSCOPE_API_KEY" (
    set "CUR=%%B"
    if not "!CUR!"=="" if "!CUR:~0,6!"=="sk-xxx" (set "KEY_SET=") else (set "KEY_SET=1")
  )
)
if not defined KEY_SET (
  echo.
  echo Masukkan API key Qwen / DashScope kamu.
  echo   ^(Daftar gratis di: https://dashscope.aliyun.com^)
  echo.
  REM Input tersembunyi lewat PowerShell, lalu simpan ke .env
  for /f "usebackq delims=" %%K in (`powershell -NoProfile -Command "$s=Read-Host 'API Key (sk-...)' -AsSecureString; [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))"`) do set "APIKEY=%%K"
  if defined APIKEY (
    powershell -NoProfile -Command "$f='%INSTALL_DIR%\.env'; $k='%APIKEY%'; $c=Get-Content $f; if ($c -match '^DASHSCOPE_API_KEY=') { $c = $c -replace '^DASHSCOPE_API_KEY=.*', ('DASHSCOPE_API_KEY=' + $k) } else { $c += 'DASHSCOPE_API_KEY=' + $k }; Set-Content -Path $f -Value $c -Encoding UTF8"
    echo   API key tersimpan di %INSTALL_DIR%\.env
  ) else (
    echo [WARN] API key dilewati. Isi manual nanti di %INSTALL_DIR%\.env
  )
) else (
  echo API key sudah terisi, melewati langkah ini.
)

REM --- 7) Buat perintah 'voca' ---
echo Membuat perintah 'voca'...
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
> "%BIN_DIR%\voca.cmd" echo @echo off
>> "%BIN_DIR%\voca.cmd" echo set "PYTHONPATH=%INSTALL_DIR%"
>> "%BIN_DIR%\voca.cmd" echo "%INSTALL_DIR%\.venv\Scripts\python.exe" -m voca %%*

REM --- 8) Tambahkan ke PATH (user, aman lewat PowerShell) ---
powershell -NoProfile -Command "$b='%BIN_DIR%'; $p=[Environment]::GetEnvironmentVariable('PATH','User'); if ($p -notlike '*'+$b+'*') { [Environment]::SetEnvironmentVariable('PATH', $p+';'+$b, 'User') }"

echo.
echo ===========================================
echo  Selesai terpasang di %INSTALL_DIR%
echo ===========================================
echo  Setting suara ^& API key ada di:  %INSTALL_DIR%\.env
echo.
echo  Jalankan:  voca           ^(mode hands-free^)
echo        atau  voca --text    ^(mode teks murni^)
echo.

REM --- 9) Tawarkan buka terminal baru (PATH ter-refresh) biar 'voca' langsung jalan ---
choice /c RK /n /m "Tekan [R] buka terminal baru ^& pakai voca sekarang, atau [K] keluar: "
if errorlevel 2 goto :selesai
start "Voca" cmd /k "set PATH=%BIN_DIR%;%PATH% & cls & echo Voca siap dipakai. Ketik:  voca   (atau  voca --text) & echo."

:selesai
endlocal
exit /b 0

:fail
echo.
echo Instalasi GAGAL. Perbaiki error di atas lalu jalankan ulang.
endlocal
exit /b 1
