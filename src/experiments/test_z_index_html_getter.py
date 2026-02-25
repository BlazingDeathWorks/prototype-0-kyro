import sys
import time
from playwright.sync_api import sync_playwright

URL = "https://icf.wd5.myworkdayjobs.com/icfexternal_career_site/job/Reston-VA/XMLNAME-2026-Summer-Intern--Full-Stack-Developer--Remote-_R2503169"


def get_open_dropdown_options(page):
    _ = page.content()
    result = page.evaluate(
        """
(() => {
  const body = document.body;
  if (!body) return { options: [] };
  const root = body.lastElementChild;
  if (!root) return { options: [] };

  function getLeafText(node) {
    const prompt = node.querySelector && node.querySelector('[data-automation-id="promptOption"]');
    if (prompt) {
      const t = (prompt.textContent || '').trim();
      if (t) return t;
    }
    const tw = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    while (tw.nextNode()) {
      const val = (tw.currentNode.nodeValue || '').trim();
      if (val && val.length > 0 && val.length < 200) return val;
    }
    return '';
  }

  function collectFromContainer(container) {
    const children = Array.from(container.children);
    const texts = [];
    for (const child of children) {
      const txt = getLeafText(child);
      if (txt) texts.push(txt);
    }
    return texts;
  }

  const list = root.querySelector('[role="listbox"]');
  if (list) {
    const nodes = Array.from(list.querySelectorAll('li, [role="option"], [data-automation-id="promptOption"]'));
    const options = nodes.map(n => (n.textContent || '').trim()).filter(Boolean);
    if (options.length) return { options };
  }

  let foundLeaf = null;
  const explorer = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  while (explorer.nextNode()) {
    const el = explorer.currentNode;
    const txt = getLeafText(el);
    if (txt) { foundLeaf = el; break; }
  }
  if (foundLeaf) {
    let current = foundLeaf.parentElement;
    while (current && current !== root) {
      const children = Array.from(current.children);
      if (!children.length) { current = current.parentElement; continue; }
      const texts = [];
      let allHaveText = true;
      for (const child of children) {
        const t = getLeafText(child);
        if (t) texts.push(t); else allHaveText = false;
      }
      if (texts.length >= Math.min(3, children.length) && allHaveText) {
        const dedup = [];
        const set = new Set();
        for (const t of texts) { if (!set.has(t)) { set.add(t); dedup.push(t); } }
        return { options: dedup };
      }
      current = current.parentElement;
    }
  }

  const leafTexts = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) {
    const el = walker.currentNode;
    const txt = getLeafText(el);
    if (txt) leafTexts.push(txt);
  }
  const uniq = [];
  const seen = new Set();
  for (const t of leafTexts) { if (!seen.has(t)) { seen.add(t); uniq.push(t); } }
  return { options: uniq };
})()
"""
    )
    return result.get("options") or []

def main():
    auto = any(arg == "--auto" for arg in sys.argv[1:])
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(URL)
        if not auto:
            input("Press ENTER to capture last body div...")
        time.sleep(3)
        _ = page.content()
        result = page.evaluate(
            """
(() => {
  const body = document.body;
  if (!body) return { options: [] };
  const root = body.lastElementChild;
  if (!root) return { options: [] };

  function getLeafText(node) {
    const prompt = node.querySelector && node.querySelector('[data-automation-id="promptOption"]');
    if (prompt) {
      const t = (prompt.textContent || '').trim();
      if (t) return t;
    }
    const tw = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    while (tw.nextNode()) {
      const val = (tw.currentNode.nodeValue || '').trim();
      if (val && val.length > 0 && val.length < 200) return val;
    }
    return '';
  }

  function collectFromContainer(container) {
    const children = Array.from(container.children);
    const texts = [];
    for (const child of children) {
      const txt = getLeafText(child);
      if (txt) texts.push(txt);
    }
    return texts;
  }

  const list = root.querySelector('[role="listbox"]');
  if (list) {
    const nodes = Array.from(list.querySelectorAll('li, [role="option"], [data-automation-id="promptOption"]'));
    const options = nodes.map(n => (n.textContent || '').trim()).filter(Boolean);
    if (options.length) return { options };
  }

  // Backtrack approach: find a leaf with text, then ascend to a container where all children yield a leaf text
  let foundLeaf = null;
  const explorer = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  while (explorer.nextNode()) {
    const el = explorer.currentNode;
    const txt = getLeafText(el);
    if (txt) { foundLeaf = el; break; }
  }
  if (foundLeaf) {
    let current = foundLeaf.parentElement;
    while (current && current !== root) {
      const children = Array.from(current.children);
      if (!children.length) { current = current.parentElement; continue; }
      const texts = [];
      let allHaveText = true;
      for (const child of children) {
        const t = getLeafText(child);
        if (t) texts.push(t); else allHaveText = false;
      }
      if (texts.length >= Math.min(3, children.length) && allHaveText) {
        const dedup = [];
        const set = new Set();
        for (const t of texts) { if (!set.has(t)) { set.add(t); dedup.push(t); } }
        return { options: dedup };
      }
      current = current.parentElement;
    }
  }

  // Fallback: collect all leaf texts under root
  const leafTexts = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) {
    const el = walker.currentNode;
    const txt = getLeafText(el);
    if (txt) leafTexts.push(txt);
  }
  const uniq = [];
  const seen = new Set();
  for (const t of leafTexts) { if (!seen.has(t)) { seen.add(t); uniq.push(t); } }
  return { options: uniq };
})()
"""
        )
        opts = result.get("options") or []
        if opts:
            for i, txt in enumerate(opts):
                print(f"{i+1}. {txt}")
        else:
            print("<no options found>")
        browser.close()


if __name__ == "__main__":
    main()
