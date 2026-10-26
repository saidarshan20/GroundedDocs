from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(not (ROOT / ".streamlit" / "secrets.toml").exists(), reason="Local demo secrets not generated")
def test_guest_can_login_get_pdf_citation_and_logout():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    app.run()
    assert not app.exception
    app.text_input[0].set_value("guest-demo-2026")
    app.button[0].click().run()
    assert not app.exception
    assert app.text_input[0].label == "Ask a question about the documents"
    app.text_input[0].set_value("How many pages may a guest print per visit?")
    next(button for button in app.button if button.label == "Find evidence").click().run()
    assert not app.exception
    assert any("Guests may print up to ten" in item.value for item in app.markdown)
    assert any("page 1" in item.value and "pub12:page-1:001" in item.value for item in app.caption)
    next(button for button in app.button if button.label == "Log out").click().run()
    assert not app.exception
    assert app.text_input[0].label == "Password"


@pytest.mark.skipif(not (ROOT / ".streamlit" / "secrets.toml").exists(), reason="Local demo secrets not generated")
def test_uploaded_text_is_searchable_then_cleared_on_logout():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.text_input[0].set_value("guest-demo-2026")
    app.button[0].click().run()
    app.get("file_uploader")[0].upload(
        "ferry.txt", b"The violet ferry leaves Harbor Nine at 6:40 a.m. every Tuesday.", "text/plain"
    )
    next(button for button in app.button if button.label == "Use this document").click().run()
    assert not app.exception
    assert any("Current upload: ferry.txt" in item.value for item in app.info)
    app.text_input[0].set_value("When does the violet ferry leave Harbor Nine?")
    next(button for button in app.button if button.label == "Find evidence").click().run()
    assert not app.exception
    assert any("6:40 a.m. every Tuesday" in item.value for item in app.markdown)
    next(button for button in app.button if button.label == "Log out").click().run()
    assert app.text_input[0].label == "Password"
    app.selectbox[0].set_value("bob")
    app.text_input[0].set_value("bob-demo-2026")
    app.button[0].click().run()
    assert not any("Current upload" in item.value for item in app.info)
    assert not app.radio
