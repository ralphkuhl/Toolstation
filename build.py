import PyInstaller.__main__
import os
import shutil

def build():
    # Clean up previous builds
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    PyInstaller.__main__.run([
        'src/main_ui.py',
        '--name', 'DMXControl',
        '--onefile',
        '--windowed',
        '--add-data', 'fixtures:fixtures',
        '--add-data', 'scenes:scenes',
        '--hidden-import', 'pylibftdi.driver',
        '--hidden-import', 'rtmidi.midiutil',
    ])

if __name__ == '__main__':
    build()
