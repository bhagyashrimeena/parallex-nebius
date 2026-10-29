import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app import main

@pytest.fixture
def client(tmp_path,monkeypatch):
    path = tmp_path / "sessions"
    path.mkdir()
    monkeypatch.setattr(main, "SESSIONS", path)
    return TestClient(main.app)

@pytest.fixture
def photo():
    im=Image.new('RGB',(650,500),(110,139,124))
    output=io.BytesIO()
    im.save(output,format='JPEG')
    return output.getvalue()

@pytest.fixture
def make_case(client,photo):
    res=client.post('/api/sessions',data={'category':'Equipment & assets','objective':'Document a casing'},files=[('files',('photo.jpg',photo,'image/jpeg'))])
    assert res.status_code==201,res.text
    return res.json()
