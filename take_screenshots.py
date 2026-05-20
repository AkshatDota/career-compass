"""
End-to-end UI screenshot capture for Career Compass.

Launches FastAPI on port 8765 (serves both HTML and API).
Playwright opens http://localhost:8765/ — no separate static server needed
since FastAPI handles GET / → Career Compass.html and GET /static/career-compass.js.
API_BASE='' in the JS means all API calls resolve to the same server.
"""
import subprocess
import time
import os
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
APP_DIR    = Path(__file__).parent
SCREENSHOT_DIR = APP_DIR / "screenshots"
BACKEND_PORT   = 8765
FRONTEND_URL   = f"http://localhost:{BACKEND_PORT}/"

SCREENSHOT_DIR.mkdir(exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def snap(page, name: str, description: str):
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  📸  {name}.png  —  {description}")
    return path


def wait_for_screen(page, screen_id: str, timeout: int = 15000):
    page.wait_for_selector(f"#{screen_id}.active", timeout=timeout)


# ── Main flow ─────────────────────────────────────────────────────────────────
def run(page, errors: list):
    # API_BASE='' in career-compass.js → all API calls go to the same origin (port 8765).
    # No patching needed.

    # 1 ── Welcome screen
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    wait_for_screen(page, "screen-welcome")
    time.sleep(0.6)
    snap(page, "01_welcome", "Welcome screen — before name entry")

    # Verify welcome content is hardcoded
    title = page.text_content(".welcome-title")
    assert "Nandini" in title, f"Expected 'Nandini' in title, got: {title}"
    begin_btn = page.query_selector("#beginBtn")
    assert begin_btn and begin_btn.is_visible(), "Begin button not visible"
    assert not begin_btn.is_disabled(), "Begin button should be enabled"
    print("    ✓  Welcome: title shows Nandini, Begin button enabled")

    # 2 ── Click Begin → Q1 (Begin now creates a new session async before advancing)
    begin_btn.click()
    wait_for_screen(page, "screen-question", timeout=20000)
    time.sleep(0.5)
    snap(page, "02_question_01", "Question 1 — energy (single-select)")

    q_text = page.text_content(".question-text")
    assert q_text and len(q_text) > 5, "Question text is empty"
    options = page.query_selector_all(".option")
    assert len(options) >= 2, f"Expected at least 2 options, got {len(options)}"
    print(f"    ✓  Q1 loaded: '{q_text[:50]}...' | {len(options)} options")

    # 3 ── Answer Q1 (single) → observe auto-advance
    options[0].click()
    time.sleep(0.8)
    snap(page, "03_question_02", "Question 2 after auto-advance")

    # 4 ── Answer Q2 (single)
    options2 = page.query_selector_all(".option")
    options2[1].click()
    time.sleep(0.6)
    snap(page, "04_question_03", "Question 3 — multi-select with Continue button")

    # 5 ── Q3 is multi-select — pick two options then click Continue
    options3 = page.query_selector_all(".option")
    options3[0].click()
    time.sleep(0.2)
    options3[2].click()
    time.sleep(0.4)
    snap(page, "05_question_03_selected", "Question 3 — two options selected")

    continue_btn = page.query_selector("#continueBtn")
    if continue_btn and continue_btn.is_visible():
        continue_btn.click()
    else:
        # If it's single, just click first option
        options3[0].click()
    time.sleep(0.6)

    # 6 ── Answer remaining questions quickly (loop until quiz finishes)
    snap_count = {6: "single", 8: "single", 10: "single", 7: "multi", 9: "multi"}
    for i in range(4, 20):
        # Stop if we've left the question screen
        if not page.query_selector("#screen-question.active"):
            break
        # Only click options that are actually visible (stale hidden options cause timeout)
        opts = [o for o in page.query_selector_all(".option") if o.is_visible()]
        if not opts:
            break
        q_type_hint = page.query_selector(".question-kicker")
        kicker_text = q_type_hint.text_content() if q_type_hint else ""
        is_multi = "any" in kicker_text.lower()

        if is_multi:
            opts[0].click()
            time.sleep(0.25)
            if len(opts) > 2:
                opts[2].click()
                time.sleep(0.2)
            cont = page.query_selector("#continueBtn")
            if cont and cont.is_visible():
                if i in snap_count and snap_count[i] == "multi":
                    snap(page, f"0{i}_question_multi", f"Question {i} — multi-select")
                cont.click()
        else:
            opts[0].click()

        time.sleep(0.6)
        # Exit early if quiz has moved past the question screen
        if not page.query_selector("#screen-question.active"):
            break
        if i in snap_count and snap_count[i] == "single":
            snap(page, f"0{i}_question_single", f"Question {i} — single-select")

    # 7 ── Loading screen
    try:
        wait_for_screen(page, "screen-loading", timeout=8000)
        time.sleep(0.7)
        snap(page, "10_loading", "Loading / AI analysis screen")
        loading_title = page.text_content("#loadingTitle")
        assert loading_title and len(loading_title) > 3, "Loading title empty"
        print(f"    ✓  Loading screen: '{loading_title}'")
    except Exception:
        print("    ℹ  Loading screen transitioned too fast to capture (that's fine)")

    # 8 ── Results screen (wait up to 60s for AI to respond)
    print("    ⏳  Waiting for AI results (Groq)…")
    wait_for_screen(page, "screen-results", timeout=60000)
    time.sleep(1.2)
    snap(page, "11_results_top", "Results page — top of page")

    # Validate results content
    career_cards = page.query_selector_all(".career-card")
    assert len(career_cards) >= 1, "No career cards rendered"
    first_title = page.text_content(".career-title")
    assert first_title and len(first_title) > 2, "Career title empty"
    salary_table = page.query_selector(".salary-table")
    assert salary_table, "Salary table missing from results"
    skills = page.query_selector_all(".skill-tag")
    assert len(skills) >= 2, f"Expected at least 2 skill tags, got {len(skills)}"
    roadmap_items = page.query_selector_all(".roadmap li")
    assert len(roadmap_items) >= 2, "Roadmap items missing"
    print(f"    ✓  Results: {len(career_cards)} careers | first: '{first_title}'")
    print(f"    ✓  Skills: {len(skills)} | Roadmap steps: {len(roadmap_items)}")

    # 9 ── Scroll down to show full results
    page.evaluate("window.scrollTo(0, 600)")
    time.sleep(0.5)
    snap(page, "12_results_career_detail", "Results — career detail with salary & skills")

    page.evaluate("window.scrollTo(0, 1400)")
    time.sleep(0.5)
    snap(page, "13_results_roadmap", "Results — roadmap & companies section")

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.5)
    snap(page, "14_results_summary", "Results — closing summary & action bar")

    # 10 ── Hover Download button
    download_btn = page.query_selector("#downloadBtn")
    assert download_btn and download_btn.is_visible(), "Download button not visible"
    download_btn.hover()
    time.sleep(0.3)
    snap(page, "15_results_actions", "Results action bar with Download button hovered")
    print("    ✓  Download button present and visible")

    # 11 ── Back button during quiz (restart and go back on Q3)
    restart_btn = page.query_selector("#restartBtn")
    restart_btn.click()
    wait_for_screen(page, "screen-welcome", timeout=5000)
    time.sleep(0.9)  # let the fadeIn animation finish before snapping
    snap(page, "16_welcome_after_restart", "Welcome screen after restart")
    print("    ✓  Restart → Welcome works")

    # Start quiz again, reach Q3, then go back
    page.click("#beginBtn")
    wait_for_screen(page, "screen-question")
    page.query_selector_all(".option")[0].click()
    time.sleep(0.6)
    page.query_selector_all(".option")[0].click()
    time.sleep(0.6)
    snap(page, "17_question_back_button", "Q3 visible with Back button enabled")
    back_btn = page.query_selector("#backBtn")
    assert not back_btn.is_disabled(), "Back button should be enabled on Q3"
    back_btn.click()
    time.sleep(0.5)
    snap(page, "18_question_after_back", "Returned to Q2 via Back button")
    print("    ✓  Back navigation works")


def main():
    # FastAPI serves both the HTML (GET /) and the JS (GET /static/career-compass.js).
    # API_BASE='' means API calls go to the same origin — no patching needed.
    env = os.environ.copy()
    env["DB_PATH"] = str(APP_DIR / "career_compass.db")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", str(BACKEND_PORT), "--log-level", "warning"],
        cwd=APP_DIR,
        env=env,
    )
    time.sleep(2)

    errors = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            # Log console errors
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: errors.append(str(err)))

            print("\n🚀  Starting UI screenshot run…\n")
            run(page, errors)
            browser.close()

        print(f"\n✅  All screenshots saved to: {SCREENSHOT_DIR}")
        print(f"    Files: {sorted(p.name for p in SCREENSHOT_DIR.glob('*.png'))}")

        if errors:
            print(f"\n⚠️   Console errors captured ({len(errors)}):")
            for e in errors[:10]:
                print(f"    • {e}")
        else:
            print("\n🟢  No console errors detected.")

    except Exception as exc:
        print(f"\n❌  Screenshot run failed: {exc}")
        import traceback; traceback.print_exc()
    finally:
        backend.terminate()
        backend.wait()


if __name__ == "__main__":
    main()
