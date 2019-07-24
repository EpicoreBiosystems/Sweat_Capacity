@echo off
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%HOMEDRIVE%%HOMEPATH%\Desktop\NICU GUI.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "C:\Python27\pythonw" >> CreateShortcut.vbs
echo oLink.Arguments = "nicu.py" >> CreateShortcut.vbs
echo oLink.WorkingDirectory  = "%cd%\" >> CreateShortcut.vbs
echo oLink.IconLocation = "%cd%\img\GUIIcon.ico" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript CreateShortcut.vbs
del CreateShortcut.vbs