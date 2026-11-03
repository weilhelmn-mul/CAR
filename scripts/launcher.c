/*
 * Sistema AT - IPD DINADAF :: Lanzador nativo para Windows x64 (v1.1)
 * Doble clic en SistemaAT.exe -> ejecuta py\pythonw.exe main.py en
 * silencio (sin consola). v1.1: espera 3 s y comprueba que el sistema
 * siga vivo; si murio de inmediato, muestra un dialogo con el codigo
 * de salida y la guia de diagnostico. Nunca falla en silencio.
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
    char detalle[1024];
    char *slash;
    DWORD n, codigo = 0;
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
               "Falta la carpeta \"py\" (incluye Python 3.12).\n\n"
               "Causa mas frecuente: se ejecuto SistemaAT.exe DENTRO del ZIP\n"
               "sin extraer. Extraiga TODO el contenido del ZIP a una carpeta\n"
               "(o a la memoria USB) y vuelva a intentarlo.\n\n"
               "Si ya extrajo todo, no separe ni renombre las carpetas:\n"
               "SistemaAT.exe, py, src, templates, assets y main.py deben\n"
               "viajar juntos.");
        return 1;
    }
    if (GetFileAttributesA(script) == INVALID_FILE_ATTRIBUTES) {
        alerta("Sistema AT", "Falta el archivo main.py junto a SistemaAT.exe.\n"
                             "Extraiga el ZIP completo antes de ejecutar.");
        return 1;
    }

    if (snprintf(cmdline, sizeof(cmdline), "\"%s\" \"%s\"", py, script) < 0) return 1;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcessA(NULL, cmdline, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
        n = GetLastError();
        snprintf(detalle, sizeof(detalle),
                 "No se pudo iniciar el motor del sistema (codigo de Windows: %lu).\n\n"
                 "Causas frecuentes:\n"
                 "  1) El antivirus bloquea py\\pythonw.exe: agregue una exclusion\n"
                 "     para esta carpeta o use INICIAR_SISTEMA.bat.\n"
                 "  2) Windows de 32 bits o anterior a Windows 10 (se requiere\n"
                 "     Windows 10/11 de 64 bits).\n"
                 "  3) Carpeta sin permisos de lectura (no use C:\\Program Files).",
                 n);
        alerta("Sistema AT", detalle);
        return 1;
    }
    CloseHandle(pi.hThread);

    if (WaitForSingleObject(pi.hProcess, 3000) == WAIT_OBJECT_0) {
        GetExitCodeProcess(pi.hProcess, &codigo);
        CloseHandle(pi.hProcess);
        if (codigo != 0) {
            snprintf(detalle, sizeof(detalle),
                     "El sistema se cerro inmediatamente al iniciar (codigo %lu).\n\n"
                     "Para ver el motivo exacto ejecute CONSOLA_DEBUG.bat (doble clic)\n"
                     "y lea el mensaje final; copielo si solicita soporte.\n\n"
                     "Causas frecuentes:\n"
                     "  - Antivirus bloqueando py\\ (agregue exclusion o use\n"
                     "    INICIAR_SISTEMA.bat).\n"
                     "  - Carpeta extraida a medias: vuelva a extraer el ZIP completo.\n"
                     "  - Windows de 32 bits (se requiere 64 bits).",
                     codigo);
            alerta("Sistema AT", detalle);
            return 2;
        }
    }
    CloseHandle(pi.hProcess);
    return 0;
}
