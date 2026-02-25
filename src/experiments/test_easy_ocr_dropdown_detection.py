import os
import json
import pathlib
import cv2
import numpy as np
import time
import warnings
from playwright.sync_api import sync_playwright
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Suppress MPS pin_memory warning from EasyOCR/PyTorch
warnings.filterwarnings("ignore", message=".*pin_memory.*")
from test_z_index_html_getter import get_open_dropdown_options

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("EasyOCR not installed. Install with: pip install easyocr")

try:
    from thefuzz import fuzz
    THEFUZZ_AVAILABLE = True
except ImportError:
    THEFUZZ_AVAILABLE = False
    print("thefuzz not installed. Install with: pip install thefuzz")

TARGET_LABELS = [
    "If hired, can you provide proof of legal authorization to live and work in the country this job is located?",
    "What is your work authorization status?",
    "Do you have any relatives presently working for Dexcom?",
    "Do you have any agreements with your current or former employer(s) that could potentially prohibit or limit your employment with Dexcom? This could include agreements such as, but not limited to, the following: non-compete agreement, confidentiality agreement, non-solicitation agreement, invention assignment agreement, employment agreement, or separation agreement. If yes, you may be asked to provide to Dexcom upon request.",
    "Are you currently 18 years or older?",
    "I verify that my application submission is truthful and accurate.",
]

URL = "https://dexcom.wd1.myworkdayjobs.com/en-US/Dexcom/job/Remote---United-States/Intern-I---Software-Engineering_JR115298/apply"
WIDTH = 1440
HEIGHT = 900
OVERLAP = 300
SPACING = 4
DROPDOWN_WIDTH = 300
DROPDOWN_HEIGHT = 36
DEBUG = True


def normalize(s: str) -> str:
    """
    Normalize text for comparison:
    - Lowercase
    - Strip extra whitespace
    - Remove trailing punctuation (*, ?, ., !)
    """
    result = " ".join(s.lower().split())
    # Remove trailing punctuation
    while result and result[-1] in '*?.!':
        result = result[:-1]
    return result.strip()


# =============================================================================
# STEP 1: Parse OCR chunks from EasyOCR results
# =============================================================================
def parse_ocr_chunks(ocr_results):
    """
    Parse EasyOCR results into a list of text chunks sorted by y-position.
    Each chunk has: text, x1, y1, x2, y2
    """
    chunks = []
    for detection in ocr_results:
        bbox, text, conf = detection
        if conf < 0.3 or not text.strip():
            continue
        
        # Get min/max coordinates from 4 corners
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        x1, y1 = min(xs), min(ys)
        x2, y2 = max(xs), max(ys)
        
        chunks.append({
            "text": text.strip(),
            "x1": x1, "y1": y1,
            "x2": x2, "y2": y2
        })
    
    # Sort by y-position (top to bottom), then by x-position (left to right)
    chunks = sorted(chunks, key=lambda c: (c["y1"], c["x1"]))
    return chunks


# =============================================================================
# STEP 2: Find starting chunk by comparing chunk to beginning of target label
# =============================================================================
def find_starting_chunk_idx(chunks, target_label, start_from_idx=0, debug=False):
    """
    Find the first chunk that matches the BEGINNING of the target label.
    
    Algorithm:
    1. Normalize the chunk text
    2. Skip if chunk is only a single word (unless target label is also single word)
    3. Substring the normalized target label to the same length as the chunk
    4. Compare using fuzz.ratio() - if >= 95, it's a match
    
    This ensures we only match chunks that appear at the START of the target label,
    and allows for minor OCR errors (like ; instead of , or extra punctuation).
    
    We skip very short chunks (< 3 chars) and single-word chunks to avoid noise
    (unless the target label itself is a single word).
    
    Returns: chunk index, or -1 if not found
    """
    normalized_target = normalize(target_label)
    target_word_count = len(normalized_target.split())
    
    for i in range(start_from_idx, len(chunks)):
        chunk_text = normalize(chunks[i]["text"])
        
        # Skip very short chunks (likely noise)
        if len(chunk_text) < 3:
            continue
        
        # Skip single-word chunks - not reliable enough for matching
        # UNLESS the target label is also a single word
        words = chunk_text.split()
        if len(words) < 2 and target_word_count > 1:
            if debug:
                print(f"      Chunk {i}: '{chunk_text[:40]}' -> SKIP (single word)")
            continue
        
        # Substring target to same length as chunk, then compare
        target_prefix = normalized_target[:len(chunk_text)]
        ratio = fuzz.ratio(chunk_text, target_prefix)
        
        if debug:
            print(f"      Chunk {i}: '{chunk_text[:40]}' vs '{target_prefix[:40]}' -> ratio = {ratio}")
        
        if ratio >= 95:
            if debug:
                print(f"      ✓ Found starting chunk at idx {i}")
            return i
    
    return -1


# =============================================================================
# STEP 3: Expand match greedily using fuzz.ratio()
# =============================================================================
def expand_match_with_fuzzy_ratio(chunks, target_label, start_chunk_idx, debug=False):
    """
    Starting from start_chunk_idx, greedily expand the match by adding
    subsequent chunks as long as fuzz.ratio() improves AND the chunk
    actually appears in the remaining portion of the target label.
    
    Algorithm:
    1. Set matching_string = first chunk's text
    2. Calculate best_ratio = fuzz.ratio(matching_string, target_label)
    3. Try adding next chunk to matching_string
    4. First check: does the next chunk appear in the remaining target? (partial_ratio >= 80)
    5. If not, stop expanding (chunk doesn't belong to this target)
    6. If yes and new_ratio > best_ratio: keep it, continue
    7. If new_ratio <= best_ratio: discard it, stop expanding
    
    Returns:
        - matching_string: the final matched string
        - bounding_box: (x1, y1, x2, y2) covering all matched chunks
        - end_chunk_idx: the index of the last chunk included
    """
    normalized_target = normalize(target_label)
    
    # Start with the first chunk
    matching_string = normalize(chunks[start_chunk_idx]["text"])
    best_ratio = fuzz.ratio(matching_string, normalized_target)
    
    # Track bounding box
    x1 = chunks[start_chunk_idx]["x1"]
    y1 = chunks[start_chunk_idx]["y1"]
    x2 = chunks[start_chunk_idx]["x2"]
    y2 = chunks[start_chunk_idx]["y2"]
    
    end_chunk_idx = start_chunk_idx
    
    if debug:
        print(f"      Initial: '{matching_string[:50]}...' ratio={best_ratio}")
    
    # Try to expand by adding subsequent chunks
    for i in range(start_chunk_idx + 1, len(chunks)):
        next_chunk = chunks[i]
        next_chunk_text = normalize(next_chunk["text"])
        
        # Option 2: Check that this chunk actually appears in the REMAINING portion of target
        # This prevents adding garbage chunks that don't belong to this target label
        remaining_target = normalized_target[len(matching_string):].strip()
        chunk_in_remaining = fuzz.partial_ratio(next_chunk_text, remaining_target)
        
        if debug:
            print(f"      + Chunk {i}: '{next_chunk_text[:30]}' in remaining? partial_ratio={chunk_in_remaining}")
        
        if chunk_in_remaining < 80:
            # This chunk doesn't appear in what we expect next - stop expanding
            if debug:
                print(f"      ✓ Stopped at chunk {i} (chunk not in remaining target)")
            break
        
        # Try adding this chunk
        candidate_string = matching_string + " " + next_chunk_text
        new_ratio = fuzz.ratio(candidate_string, normalized_target)
        
        if debug:
            print(f"        -> ratio={new_ratio} (prev={best_ratio})")
        
        if new_ratio > best_ratio:
            # Improvement - include this chunk
            matching_string = candidate_string
            best_ratio = new_ratio
            end_chunk_idx = i
            
            # Expand bounding box
            x1 = min(x1, next_chunk["x1"])
            y1 = min(y1, next_chunk["y1"])
            x2 = max(x2, next_chunk["x2"])
            y2 = max(y2, next_chunk["y2"])
        else:
            # No improvement - stop expanding
            if debug:
                print(f"      ✓ Stopped at chunk {i} (ratio decreased)")
            break
    
    return matching_string, (x1, y1, x2, y2), end_chunk_idx


# =============================================================================
# STEP 4: Process all target labels for a single snapshot
# =============================================================================
def process_snapshot_for_labels(chunks, target_labels, last_ended_target_idx, start_verification_idx, debug=False):
    """
    Process target labels for a single snapshot.
    
    Logic:
    - For target_idx < start_verification_idx: Skip (already verified not in previous snapshots)
    - For start_verification_idx <= target_idx < last_ended_target_idx: VERIFICATION PHASE
      - If not found: continue to next label (don't stop)
    - For target_idx >= last_ended_target_idx: NEW SEARCH PHASE
      - If not found: STOP processing this snapshot
    
    Returns:
        - matches: dict of {target_label: {"box": bbox, "text": matched_text}}
        - new_last_ended_target_idx: updated index
        - new_start_verification_idx: updated verification start index
    """
    matches = {}
    ocr_chunk_idx = 0  # Current position in OCR chunks
    new_last_ended_target_idx = last_ended_target_idx
    new_start_verification_idx = start_verification_idx
    
    for target_idx, target_label in enumerate(target_labels):
        # Skip labels that were already verified not to be in previous snapshots
        if target_idx < start_verification_idx:
            if debug:
                print(f"\n    [SKIP] Target {target_idx}: '{target_label[:40]}...' (below start_verification_idx)")
            continue
        
        is_verification_phase = target_idx < last_ended_target_idx
        phase_name = "VERIFICATION" if is_verification_phase else "NEW SEARCH"
        
        if debug:
            print(f"\n    [{phase_name}] Target {target_idx}: '{target_label[:50]}...'")
        
        # STEP 2: Find starting chunk using indexOf check
        starting_chunk_idx = find_starting_chunk_idx(
            chunks, target_label, start_from_idx=ocr_chunk_idx, debug=debug
        )
        
        if starting_chunk_idx == -1:
            # No starting chunk found
            if debug:
                print(f"      ✗ No starting chunk found")
            
            if is_verification_phase:
                # Verification phase - update start_verification_idx and continue
                new_start_verification_idx = max(new_start_verification_idx, target_idx + 1)
                if debug:
                    print(f"      (Verification phase - updating start_verification_idx to {new_start_verification_idx})")
                continue
            else:
                # New search phase - STOP processing this snapshot
                if debug:
                    print(f"      (New search phase - STOPPING snapshot processing)")
                break
        
        # STEP 3: Found starting chunk - expand match using fuzz.ratio()
        matching_string, bbox, end_chunk_idx = expand_match_with_fuzzy_ratio(
            chunks, target_label, starting_chunk_idx, debug=debug
        )
        
        if debug:
            print(f"      ✓ Match found: chunks {starting_chunk_idx}-{end_chunk_idx}")
            print(f"      Text: '{matching_string[:60]}...'")
        
        # Record the match
        matches[target_label] = {
            "box": bbox,
            "text": matching_string
        }
        
        # Update tracking
        new_last_ended_target_idx = target_idx + 1  # Next label to search for
        ocr_chunk_idx = end_chunk_idx + 1  # Start next search after this match
    
    return matches, new_last_ended_target_idx, new_start_verification_idx


# =============================================================================
# DRAWING FUNCTION
# =============================================================================
def draw(img, items, color=(0, 255, 0)):
    """Draw bounding boxes on image."""
    for it in items:
        x1, y1, x2, y2 = it["label_box"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 2)
        dx1, dy1, dx2, dy2 = it["dropdown_box"]
        cv2.rectangle(img, (dx1, dy1), (dx2, dy2), color, 3)
        cx = (dx1 + dx2) // 2
        cy = (dy1 + dy2) // 2
        cv2.line(img, (cx - 6, cy), (cx + 6, cy), color, 2)
        cv2.line(img, (cx, cy - 6), (cx, cy + 6), color, 2)
    return img


# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    if not EASYOCR_AVAILABLE:
        raise RuntimeError("EasyOCR not available. Install with: pip install easyocr")
    if not THEFUZZ_AVAILABLE:
        raise RuntimeError("thefuzz not available. Install with: pip install thefuzz")
    
    print("Initializing EasyOCR reader (this may take a moment)...")
    reader = easyocr.Reader(['en'], gpu=False)
    print("EasyOCR reader initialized!\n")
    
    auto = any(arg == "--auto" for arg in sys.argv[1:])
    snapshots_dir = None
    if DEBUG:
        snapshots_dir = pathlib.Path('/Users/jasonchan/Documents/Programming/Python/Python 3.13/project-kyro/snapshots')
        os.makedirs(snapshots_dir, exist_ok=True)
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
        page = context.new_page()
        page.goto(URL)
        page.wait_for_load_state()
        page.set_viewport_size({"width": WIDTH, "height": HEIGHT})
        page.wait_for_timeout(100)
        
        if not auto:
            input("Press ENTER to start viewport screenshots...")
        
        scroll_height = page.evaluate("document.documentElement.scrollHeight")
        step = max(1, HEIGHT - OVERLAP)
        print(f"Scroll amount per iteration: {step} px")
        print(f"Page scroll height: {scroll_height} px, Viewport height: {HEIGHT} px")
        positions = list(range(0, max(0, scroll_height - HEIGHT) + 1, step))
        if not positions:
            positions = [0]
        
        # Option 1: Always take a final snapshot at the bottom if there's remaining content
        # This handles edge cases where the page is slightly taller than the viewport
        last_position = positions[-1] if positions else 0
        if last_position + HEIGHT < scroll_height:
            final_pos = scroll_height - HEIGHT
            positions.append(final_pos)
            print(f"Added final snapshot at Y={final_pos} to capture bottom content")
        
        print(f"Snapshot positions: {positions}")
        
        # Track state across snapshots
        label_to_snapshot = {}  # label -> {"snapshot_idx": idx, "box": bbox, "text": text}
        last_ended_target_idx = 0  # Index of next label to search for in NEW SEARCH phase
        start_verification_idx = 0  # Index to start verification from (skip labels before this)
        
        idx = 0
        last_pos = 0
        
        for pos in positions:
            try:
                print(f"\n{'='*80}")
                print(f"SNAPSHOT {idx}: Scrolling to Y={pos}")
                print(f"  last_ended_target_idx={last_ended_target_idx}, start_verification_idx={start_verification_idx}")
                print('='*80)
                
                page.evaluate(f"window.scrollTo(0, {pos})")
                page.wait_for_timeout(300)
                ts = time.strftime("%Y%m%d_%H%M%S")
                buf = page.screenshot(full_page=False)
                img = cv2.imdecode(np.frombuffer(buf, np.uint8), cv2.IMREAD_COLOR)
                
                # Run EasyOCR
                print(f"Running EasyOCR...")
                ocr_results = reader.readtext(img)
                
                # STEP 1: Parse OCR chunks
                chunks = parse_ocr_chunks(ocr_results)
                print(f"Parsed {len(chunks)} OCR chunks")
                
                # Save debug JSON
                if DEBUG and snapshots_dir is not None:
                    ocr_debug_path = snapshots_dir / f"easyocr_debug_viewport_{idx}.json"
                    ocr_debug = {
                        "viewport": idx,
                        "scroll_position": pos,
                        "num_chunks": len(chunks),
                        "chunks": [
                            {
                                "idx": i,
                                "text": c["text"],
                                "bbox": {
                                    "x1": float(c["x1"]), "y1": float(c["y1"]),
                                    "x2": float(c["x2"]), "y2": float(c["y2"])
                                }
                            }
                            for i, c in enumerate(chunks)
                        ]
                    }
                    with open(ocr_debug_path, 'w') as f:
                        json.dump(ocr_debug, f, indent=2)
                    print(f"Saved debug: {ocr_debug_path}")
                
                # STEP 4: Process snapshot for labels
                debug_mode = True  # Debug all snapshots for now
                matches, new_last_ended, new_start_verif = process_snapshot_for_labels(
                    chunks, TARGET_LABELS, last_ended_target_idx, start_verification_idx, debug=debug_mode
                )
                
                print(f"\nFound {len(matches)} matches in snapshot {idx}")
                
                # Update label_to_snapshot (LAST snapshot wins)
                for label, match_info in matches.items():
                    label_to_snapshot[label] = {
                        "snapshot_idx": idx,
                        "box": match_info["box"],
                        "text": match_info["text"]
                    }
                    print(f"  ✓ {label}")
                
                # Update tracking indices
                last_ended_target_idx = new_last_ended
                start_verification_idx = new_start_verif
                
                # Build items for drawing (only labels assigned to THIS snapshot)
                items = []
                for label, info in label_to_snapshot.items():
                    if info["snapshot_idx"] == idx:
                        x1, y1, x2, y2 = info["box"]
                        dy = y2 + int(SPACING)
                        h = int(DROPDOWN_HEIGHT)
                        w = int(DROPDOWN_WIDTH)
                        dd = (
                            int(max(0, x1)),
                            int(max(0, dy)),
                            int(min(img.shape[1] - 1, x1 + w)),
                            int(min(img.shape[0] - 1, dy + h)),
                        )
                        cx = int((dd[0] + dd[2]) // 2)
                        cy = int((dd[1] + dd[3]) // 2)
                        items.append({
                            "label": label,
                            "label_text": info["text"],
                            "label_box": [int(x1), int(y1), int(x2), int(y2)],
                            "dropdown_box": [int(dd[0]), int(dd[1]), int(dd[2]), int(dd[3])],
                            "click_point": [cx, cy],
                        })
                
                # Order by TARGET_LABELS order
                ordered_items = []
                for label in TARGET_LABELS:
                    for item in items:
                        if item["label"] == label:
                            ordered_items.append(item)
                            break
                
                # Draw and save
                annotated = draw(img.copy(), ordered_items)
                if DEBUG and snapshots_dir is not None:
                    out_img_path = snapshots_dir / f"viewport_easyocr_{ts}_{idx}_annotated.png"
                    cv2.imwrite(str(out_img_path), annotated)
                    print(f"Saved: {out_img_path} ({len(ordered_items)} items)")
                
                idx += 1
                last_pos = pos
                
            except Exception as e:
                print("Error:", e)
                import traceback
                traceback.print_exc()
        
        # Final summary
        print("\n" + "="*80)
        print("FINAL RESULTS")
        print("="*80)
        
        for i, target_label in enumerate(TARGET_LABELS, 1):
            if target_label in label_to_snapshot:
                info = label_to_snapshot[target_label]
                print(f"{i}. ✓ FOUND (snapshot {info['snapshot_idx']}): {target_label}")
            else:
                print(f"{i}. ✗ MISSING: {target_label}")
        
        browser.close()


if __name__ == "__main__":
    main()
