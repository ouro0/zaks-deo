' demarrage_silencieux.vbs
' Lance lancer.bat au demarrage de Windows sans fenetre noire

Dim WShell
Set WShell = CreateObject("WScript.Shell")
WShell.Run "cmd /c ""C:\Users\ZAK\projet_téléchrgement\lancer.bat""", 1, False
Set WShell = Nothing
