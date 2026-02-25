import argparse
from playwright.sync_api import sync_playwright


def parse_coords(s):
    s = s.strip()
    if "," in s:
        parts = s.split(",")
    else:
        parts = s.split()
    if len(parts) != 2:
        return None
    try:
        x = int(float(parts[0]))
        y = int(float(parts[1]))
        return x, y
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Manual coordinate clicker using Playwright")
    ap.add_argument("--url", type=str, default="https://spgi.wd5.myworkdayjobs.com/en-US/Kensho_Careers/job/New-York%2C-NY/Software-Engineer-Intern---Summer-2026_319680-1/apply")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    args = ap.parse_args()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport={"width": args.width, "height": args.height})
        page = context.new_page()
        page.goto(args.url)
        page.wait_for_load_state()

        while True:
            user_input = input("Enter 'x,y' (viewport), 'abs x,y' (page), 'down <pixels>', 'goto <url>', or 'q': ").strip()

            if user_input.lower() in {"q", "quit", "exit"}:
                break

            if user_input.lower().startswith("goto "):
                url = user_input[5:].strip()
                try:
                    page.goto(url)
                    page.wait_for_load_state()
                    print(f"Navigated to: {page.url}")
                except Exception as e:
                    print(f"Navigation error: {e}")
                continue

            if user_input.lower().startswith("down"):
                parts = user_input.split()
                if len(parts) != 2:
                    print("Usage: down <pixels>")
                    continue
                try:
                    amount = int(float(parts[1]))
                except Exception:
                    print("Usage: down <pixels>")
                    continue
                try:
                    page.evaluate(f"window.scrollBy(0, {amount})")
                    page.wait_for_timeout(200)
                    offsets = page.evaluate("({x: window.scrollX, y: window.scrollY})")
                    print(f"Scrolled to Y={offsets['y']}")
                except Exception as e:
                    print(f"Scroll failed: {e}")
                continue

            if user_input.lower().startswith("abs "):
                coords = parse_coords(user_input[4:])
                if not coords:
                    print("Enter absolute coordinates as 'abs x,y'.")
                    continue
                x_abs, y_abs = coords
                try:
                    target_y = max(0, y_abs - args.height // 2)
                    target_x = max(0, x_abs - args.width // 2)
                    page.evaluate(f"window.scrollTo({target_x}, {target_y})")
                    page.wait_for_timeout(300)
                    offsets = page.evaluate("({x: window.scrollX, y: window.scrollY})")
                    vx = int(x_abs - offsets["x"])
                    vy = int(y_abs - offsets["y"])
                    vx = max(0, min(args.width - 1, vx))
                    vy = max(0, min(args.height - 1, vy))
                    page.mouse.click(vx, vy)
                    print(f"Clicked absolute ({x_abs}, {y_abs}) at viewport ({vx}, {vy})")
                except Exception as e:
                    print(f"Absolute click failed: {e}")
                continue

            coords = parse_coords(user_input)
            if not coords:
                print("Enter coordinates as 'x,y' or 'x y'.")
                continue

            x, y = coords
            try:
                page.mouse.click(x, y)
                print(f"Clicked at ({x}, {y})")
            except Exception as e:
                print(f"Click failed: {e}")

        browser.close()


if __name__ == "__main__":
    main()