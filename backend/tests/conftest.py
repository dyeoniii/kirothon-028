import os
import shutil
import sys
import tempfile
from pathlib import Path

# app import 전에 테스트용 DB/저장소 지정 (실제 app.db, 서버 저장 폴더를 건드리지 않음)
_TMP = Path(tempfile.mkdtemp(prefix="akpleguard_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["STORAGE_DIR"] = str(_TMP / "storage")
os.environ["MAX_UPLOAD_MB"] = "10"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _force_adapter_stubs(monkeypatch):
    """다른 세션의 실제 모듈/.env 키/네트워크에 의존하지 않도록 항상 stub으로 테스트."""
    from app.api import adapters

    monkeypatch.setattr(adapters, "_resolve", lambda name: (adapters._STUBS[name], False))


@pytest.fixture()
def client():
    from app import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    shutil.rmtree(os.environ["STORAGE_DIR"], ignore_errors=True)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    shutil.rmtree(_TMP, ignore_errors=True)
