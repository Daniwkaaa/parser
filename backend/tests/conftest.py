import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests import fake_servers  # noqa: E402

PORT = fake_servers.start()
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp, 'test.db').as_posix()}"
os.environ["OVERPASS_URLS"] = f"http://127.0.0.1:{PORT}/api/interpreter"
os.environ["NOMINATIM_URL"] = f"http://127.0.0.1:{PORT}"
os.environ["HTTP_TIMEOUT"] = "5"

from app.services.http import rate_limiter  # noqa: E402

rate_limiter.set_interval("127.0.0.1", 0)
