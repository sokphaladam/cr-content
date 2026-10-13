; Installer hooks for the NSIS installer (tauri.bundle.json -> bundle.windows.nsis.installerHooks).

; An update copies the new files over the old ones without removing files the new version no longer ships.
; For the engine that breaks startup: leftovers of a library left out of the build (numpy, say) are found
; instead of the real one. So the old engine goes first; the user's library lives elsewhere and is not touched.
!macro NSIS_HOOK_PREINSTALL
  RMDir /r "$INSTDIR\engine"
!macroend

; "Start with Windows" (Settings, or the tray menu) adds a Run entry; don't leave it pointing at a removed app.
!macro NSIS_HOOK_POSTUNINSTALL
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Shorts Studio"
!macroend
