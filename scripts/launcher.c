/*
 * Sistema AT - IPD DINADAF :: Lanzador nativo para Windows x64
 * Doble clic en SistemaAT.exe -> ejecuta py\pythonw.exe main.py
 * en silencio (sin consola). Si falta algo, muestra un mensaje
 * de error claro. El lanzador termina inmediatamente tras iniciar
 * la aplicacion.
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

static void alerta(const char *titulo, const char *texto)
{
    MessageBoxA(NULL, texto, titulo, MB_ICONERROR | MB_OK);
}

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR lpCmdLine, int nCmdShow)
{
    char dir[MAX_PATH], py[MAX_PATH * 2], script[MAX_PATH * 2], cmdline[MAX_PATH * 3];
    char *slash;
    DWORD n;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    (void)hInst; (void)hPrev; (void)lpCmdLine; (void)nCmdShow;

    n = GetModuleFileNameA(NULL, dir, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) {
        alerta("Sistema AT", "No se pudo ubicar la carpeta del programa.");
        return 1;
    }
    slash = strrchr(dir, '\\');
    if (slash != NULL) *slash = '\0';

    if (snprintf(py, sizeof(py), "%s\\py\\pythonw.exe", dir) < 0) return 1;
    if (snprintf(script, sizeof(script), "%s\\main.py", dir) < 0) return 1;

    if (GetFileAttributesA(py) == INVALID_FILE_ATTRIBUTES) {
        alerta("Sistema AT",
               "Falta la carpeta \"py\" (incluye Python 3.12).\n"
               "No separe ni renombre las carpetas del sistema:\n"
               "SistemaAT.exe, py, src, templates y main.py deben viajar juntos.");
        return 1;
    }
    if (GetFileAttributesA(script) == INVALID_FILE_ATTRIBUTES) {
        alerta("Sistema AT", "Falta el archivo main.py junto a SistemaAT.exe.");
        return 1;
    }

    if (snprintf(cmdline, sizeof(cmdline), "\"%s\" \"%s\"", py, script) < 0) return 1;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcessA(NULL, cmdline, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        alerta("Sistema AT",
               "No se pudo iniciar el sistema.\n\n"
               "Detalle: fallo al ejecutar py\\pythonw.exe.\n"
               "Use CONSOLA_DEBUG.bat para ver el mensaje de error completo.");
        return 1;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
