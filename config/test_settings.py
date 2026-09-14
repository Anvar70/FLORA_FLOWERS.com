from .settings import *
# A file-backed disposable test database supports SQLite's busy timeout across live-server threads.
(BASE_DIR/'test-artifacts').mkdir(exist_ok=True)
if DATABASES['default']['ENGINE']=='django.db.backends.sqlite3':
    DATABASES['default']['TEST']={'NAME':BASE_DIR/'test-artifacts'/'browser-test.sqlite3'}
