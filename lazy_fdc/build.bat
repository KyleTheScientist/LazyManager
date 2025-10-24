pyinstaller --noconfirm --onefile --console --add-data "resource/*;resource" --name LazyFDC main.py
copy dist\LazyFDC.exe F:\LazyFDC.exe