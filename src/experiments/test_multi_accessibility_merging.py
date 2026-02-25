import os
import json
import copy
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import agentql

# Load environment variables
load_dotenv()

# URL to test
URL = "https://job-boards.greenhouse.io/cloudflare/jobs/6750119?gh_jid=6750119"
URL = "https://jobs.ashbyhq.com/cohere/25cc6633-614a-45e0-8632-ffd4a2475c9b/application"

# AgentQL query for dropdown elements
DROPDOWN_QUERY = """
{
    dropdown_element_trigger_buttons(All dropdown trigger button elements on the page)[]
}
"""

def merge_accessibility_trees(baseline_tree, dropdown_opened_tree):
    """
    Intelligently merge dropdown options from dropdown_opened_tree into baseline_tree.
    Only adds new dropdown options to existing listboxes, doesn't duplicate page structure.
    """
    def find_listboxes(node, listboxes=None):
        """Find all listbox nodes in the tree"""
        if listboxes is None:
            listboxes = []
        
        if isinstance(node, dict):
            if node.get('role') == 'listbox':
                listboxes.append(node)
            
            if 'children' in node:
                for child in node['children']:
                    find_listboxes(child, listboxes)
        
        return listboxes
    
    def find_listbox_by_context(node, target_context, path=""):
        """Find a listbox by looking at its surrounding context (parent elements)"""
        if isinstance(node, dict):
            current_path = f"{path}/{node.get('role', 'unknown')}"
            if node.get('name'):
                current_path += f"[{node.get('name')}]"
            
            if node.get('role') == 'listbox':
                return node, current_path
            
            if 'children' in node:
                for child in node['children']:
                    result, result_path = find_listbox_by_context(child, target_context, current_path)
                    if result:
                        return result, result_path
        
        return None, ""
    
    def extract_dropdown_options(listbox_node):
        """Extract all option nodes from a listbox"""
        options = []
        if isinstance(listbox_node, dict) and 'children' in listbox_node:
            for child in listbox_node['children']:
                if child.get('role') == 'option':
                    options.append(child)
        return options
    
    def update_listbox_with_options(baseline_listbox, new_options):
        """Add new options to a listbox if they don't already exist"""
        if not isinstance(baseline_listbox, dict) or 'children' not in baseline_listbox:
            return
        
        # Get existing option names to avoid duplicates
        existing_option_names = set()
        for child in baseline_listbox['children']:
            if child.get('role') == 'option' and child.get('name'):
                existing_option_names.add(child.get('name'))
        
        # Add new options that don't already exist
        for option in new_options:
            option_name = option.get('name')
            if option_name and option_name not in existing_option_names:
                baseline_listbox['children'].append(copy.deepcopy(option))
                existing_option_names.add(option_name)
    
    # Create a deep copy of baseline tree to avoid modifying original
    merged_tree = copy.deepcopy(baseline_tree)
    
    # Find all listboxes in the opened tree
    opened_listboxes = find_listboxes(dropdown_opened_tree)
    
    def find_dropdown_containers(node, containers=None):
        """Find dropdown containers (combobox, button) that might contain listboxes"""
        if containers is None:
            containers = []
        
        if isinstance(node, dict):
            role = node.get('role', '')
            if role in ['combobox', 'button'] and 'children' in node:
                containers.append(node)
            
            if 'children' in node:
                for child in node['children']:
                    find_dropdown_containers(child, containers)
        
        return containers
    
    # Find dropdown containers in baseline tree
    baseline_containers = find_dropdown_containers(merged_tree)
    
    # For each listbox in the opened tree, add it to appropriate container in baseline
    for opened_listbox in opened_listboxes:
        new_options = extract_dropdown_options(opened_listbox)
        
        if new_options:  # Only process if there are new options
            # Find a suitable container to add this listbox to
            # Look for containers that don't already have a listbox
            for container in baseline_containers:
                container_has_listbox = any(
                    child.get('role') == 'listbox' 
                    for child in container.get('children', [])
                )
                
                if not container_has_listbox:
                    # Add the listbox with options to this container
                    if 'children' not in container:
                        container['children'] = []
                    container['children'].append(copy.deepcopy(opened_listbox))
                    baseline_containers.remove(container)  # Don't reuse this container
                    break
    
    return merged_tree

def main():
    with sync_playwright() as playwright:
        try:
            # Launch browser
            browser = playwright.chromium.launch(headless=False)
            page = agentql.wrap(browser.new_page())
            
            # Listen to console messages
            def handle_console_msg(msg):
                print(f"Browser console: {msg.text}")
            page.on("console", handle_console_msg)
            
            # Navigate to the URL
            print(f"Navigating to: {URL}")
            page.goto(URL)
            
            # Wait for page to load
            page.wait_for_page_ready_state()
            
            # Get base accessibility tree (no dropdowns opened)
            print("Extracting base accessibility tree...")
            base_tree = page.accessibility.snapshot(
                interesting_only=False,
                root=None
            )
            
            # Find dropdown elements using AgentQL
            print("\nQuerying for dropdown elements...")
            dropdown_data = page.query_elements(DROPDOWN_QUERY)
            
            if dropdown_data and hasattr(dropdown_data, 'dropdown_element_trigger_buttons'):
                dropdowns = dropdown_data.dropdown_element_trigger_buttons
                print(f"Found {len(dropdowns)} dropdown elements")
                
                # First, capture the baseline accessibility tree (before any dropdowns are opened)
                print("\nCapturing baseline accessibility tree (no dropdowns opened)...")
                baseline_tree = page.accessibility.snapshot(
                    interesting_only=False,
                    root=None
                )
                print("Baseline accessibility tree captured")
                
                # Start with the baseline tree as our merged result
                merged_tree = baseline_tree
                
                # Process each dropdown and update the baseline tree with its options
                for i, dropdown in enumerate(dropdowns):
                    try:
                        print(f"\nProcessing dropdown {i+1}...")
                        
                        # Get dropdown info
                        tf623_id = dropdown.get_attribute("tf623_id")
                        print(f"Dropdown {i+1} tf623_id: {tf623_id}")
                        
                        # Scroll dropdown into view
                        dropdown.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)
                        
                        # Click to open dropdown
                        dropdown.click()
                        print(f"Clicked dropdown {i+1}")
                        
                        # Wait for dropdown to open
                        page.wait_for_timeout(2000)  # Wait longer to ensure options load
                        
                        # Get accessibility tree with this dropdown opened
                        dropdown_opened_tree = page.accessibility.snapshot(
                            interesting_only=False,
                            root=None
                        )
                        
                        print(f"Captured accessibility tree for dropdown {i+1}")
                        
                        # Merge this dropdown's options into our baseline tree
                        merged_tree = merge_accessibility_trees(merged_tree, dropdown_opened_tree)
                        print(f"Updated baseline tree with dropdown {i+1} options")
                        
                        # Close the dropdown by pressing escape
                        page.keyboard.press('Escape')
                        page.wait_for_timeout(1000)
                        
                    except Exception as e:
                        print(f"Error processing dropdown {i+1}: {e}")
                
                # Save the final merged accessibility tree
                output_file = 'complete_merged_dropdowns_tree.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(merged_tree, f, indent=2, ensure_ascii=False)
                
                print(f"\nSaved complete merged accessibility tree to {output_file}")
            
            else:
                print("No dropdown elements found, saving base tree")
                output_file = "accessibility_tree_cloudflare.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(base_tree, f, indent=2, ensure_ascii=False)
                
                print(f"\nSaved base accessibility tree to {output_file}")
            
            # Keep browser open for inspection
            print("Script completed. Browser will remain open for inspection.")
            input("Press Enter to close browser...")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()