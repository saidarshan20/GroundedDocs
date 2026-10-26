from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(not (ROOT / ".streamlit" / "secrets.toml").exists(), reason="Local demo secrets not generated")
def test_guest_can_login_get_pdf_citation_and_logout():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    app.run()
    assert not app.exception
    app.text_input[0].set_value("guest-demo-2026")
    app.button[0].click().run()
    assert not app.exception
    assert app.text_input[0].label == "Ask a question about the documents"
    app.text_input[0].set_value("How many pages may a guest print per visit?")
    app.button[1].click().run()
    assert not app.exception
    assert any("Guests may print up to ten" in item.value for item in app.markdown)
    assert any("page 1" in item.value and "pub12:page-1:001" in item.value for item in app.caption)
    app.button[0].click().run()
    assert not app.exception
    assert app.text_input[0].label == "Password"
