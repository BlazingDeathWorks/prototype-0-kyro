import json

def find_container_by_tf623_id(tree_data, target_id):
    """
    Recursively search through the accessibility tree to find
    the container with the matching tf623_id
    """
    if isinstance(tree_data, dict):
        # Check if this node has the target tf623_id (handle both string and int comparisons)
        node_tf623_id = tree_data.get('attributes', {}).get('tf623_id')
        if node_tf623_id is not None and str(node_tf623_id) == str(target_id):
            return tree_data
        
        # Search in children if they exist
        if 'children' in tree_data:
            for child in tree_data['children']:
                result = find_container_by_tf623_id(child, target_id)
                if result:
                    return result
    
    elif isinstance(tree_data, list):
        # If it's a list, search through each item
        for item in tree_data:
            result = find_container_by_tf623_id(item, target_id)
            if result:
                return result
    
    return None

def contains_hidden(obj):
    """
    Recursively check if an object contains the word "hidden" anywhere
    in its structure (keys, values, or as part of larger strings)
    """
    def search_in_value(value):
        if isinstance(value, str):
            return "hidden" in value.lower()
        elif isinstance(value, dict):
            return any(search_in_value(k) or search_in_value(v) for k, v in value.items())
        elif isinstance(value, list):
            return any(search_in_value(item) for item in value)
        else:
            return False
    
    return search_in_value(obj)

def find_hidden_indexes(tags_data):
    """
    Find indexes of objects that contain "hidden" anywhere in their structure
    """
    hidden_indexes = []
    
    try:
        # Handle AgentQL objects directly - no JSON parsing needed
        if isinstance(tags_data, str):
            # Only try JSON parsing if it's actually a JSON string
            try:
                tags_list = json.loads(tags_data)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat as empty list
                tags_list = []
        else:
            # For AgentQL objects or lists, use directly
            tags_list = tags_data
        
        # Check each object for "hidden"
        for index, obj in enumerate(tags_list):
            if contains_hidden(obj):
                hidden_indexes.append(index)
        
        return hidden_indexes, tags_list
    
    except Exception as e:
        print(f"Error parsing tags data: {e}")
        return [], []


def find_container_in_hierarchy(tf623_id, container_data, path="root"):
    """
    Recursively search for a container with the given tf623_id in the hierarchy
    Returns the matching container and its path if found
    """
    # Check if current container matches (handle both string and int comparisons)
    container_tf623_id = container_data.get('attributes', {}).get('tf623_id')
    if container_tf623_id is not None:
        # Convert both to strings for comparison to handle type mismatches
        if str(container_tf623_id) == str(tf623_id):
            return container_data, path
    
    # Search in children if they exist
    if 'children' in container_data and isinstance(container_data['children'], list):
        for i, child in enumerate(container_data['children']):
            result, child_path = find_container_in_hierarchy(tf623_id, child, f"{path}.children[{i}]")
            if result:
                return result, child_path
    
    return None, None


def find_name_in_children(container, depth=0, max_depth=5):
    """
    Recursively search through children to find a non-empty name
    Returns the first non-empty name found, or None if none found
    """
    if depth > max_depth:
        return None
    
    # Check if current container has a non-empty name
    name = container.get('name', '').strip()
    if name:
        return name
    
    # Search in children if they exist
    children = container.get('children', [])
    if isinstance(children, list):
        for child in children:
            found_name = find_name_in_children(child, depth + 1, max_depth)
            if found_name:
                return found_name
    
    return None


def find_sibling_labels(target_container, parent_container):
    """
    Search for sibling elements that might contain labels for the target element
    This looks for text elements, labels, or other elements with names that could be field labels
    """
    if not parent_container or 'children' not in parent_container:
        return None
    
    target_tf623_id = target_container.get('attributes', {}).get('tf623_id')
    children = parent_container.get('children', [])
    
    # Look for sibling elements with names that could be labels
    for sibling in children:
        sibling_role = sibling.get('role', '')
        sibling_name = sibling.get('name', '').strip()
        sibling_tf623_id = sibling.get('attributes', {}).get('tf623_id')
        
        # Skip the target element itself
        if sibling_tf623_id == target_tf623_id:
            continue
            
        # Look for elements that are likely labels (text, label roles, or elements with meaningful names)
        if sibling_name and (sibling_role in ['text', 'label', 'static text', 'StaticText'] or sibling_name):
            return sibling_name
            
        # Also recursively search within siblings for labels
        if 'children' in sibling:
            found_in_sibling = find_name_in_children(sibling, 0, 2)  # Limited depth for sibling search
            if found_in_sibling:
                return found_in_sibling
    
    return None


def find_parent_container_path(tf623_id, container_data, current_path=None, parent_path=None):
    """
    Find the parent container path for a given tf623_id
    Returns the parent container and the path to reach it
    """
    if current_path is None:
        current_path = []
    
    # Check if current container matches the target tf623_id (handle both string and int comparisons)
    container_tf623_id = container_data.get('attributes', {}).get('tf623_id')
    if container_tf623_id is not None and str(container_tf623_id) == str(tf623_id):
        return parent_path, current_path
    
    # Search in children
    if 'children' in container_data and isinstance(container_data['children'], list):
        for i, child in enumerate(container_data['children']):
            child_path = current_path + [i]
            result_parent, result_path = find_parent_container_path(
                tf623_id, child, child_path, (container_data, current_path)
            )
            if result_parent is not None:
                return result_parent, result_path
    
    return None, None


def get_container_at_path(container_data, path):
    """
    Navigate to a container using the given path
    """
    current = container_data
    for index in path:
        if 'children' in current and isinstance(current['children'], list):
            if 0 <= index < len(current['children']):
                current = current['children'][index]
            else:
                return None
        else:
            return None
    return current


def find_name_with_inside_out_search(tf623_id, container_hierarchy, max_levels=5):
    """
    Implement inside-out search strategy:
    1. First search within the immediate container
    2. Search for sibling labels at the immediate parent level
    3. If nothing found, search within parent containers level by level
    4. Stop when we reach the boundary of the overall child group
    """
    if not tf623_id or not container_hierarchy:
        print(f"      ❌ Invalid input: tf623_id={tf623_id}, container_hierarchy={'present' if container_hierarchy else 'missing'}")
        return None
    
    print(f"      🎯 Starting inside-out search for tf623_id={tf623_id}")
    
    # Find the target container and its parent path
    target_container, target_path = find_container_in_hierarchy(tf623_id, container_hierarchy)
    

    if not target_container:
        print(f"      ❌ Target element {tf623_id} not found in accessibility tree")
        return None
    
    print(f"      ✅ Found target element: role={target_container.get('role', 'unknown')}")

    # Step 1: Search within the immediate container
    print(f"      🔍 Step 1: Searching within immediate container")
    found_name = find_name_in_children(target_container)
    if found_name:
        print(f"        ✅ Found name in immediate container: '{found_name}'")
        return found_name
    else:
        print(f"        ❌ No name found in immediate container")

    # Step 2: Search for sibling labels at the immediate parent level
    print(f"      🔍 Step 2: Searching for sibling labels at immediate parent level")
    parent_info, parent_path = find_parent_container_path(tf623_id, container_hierarchy)
    
    if parent_info:
        # parent_info is a tuple (parent_container, parent_path)
        parent_container, _ = parent_info
        print(f"        📁 Found parent container: role={parent_container.get('role', 'unknown')}")
        sibling_label = find_sibling_labels(target_container, parent_container)
        if sibling_label:
            print(f"        ✅ Found sibling label: '{sibling_label}'")
            return sibling_label
        else:
            print(f"        ❌ No sibling labels found")
    else:
        print(f"        ❌ No parent container found")

    # Step 3: Search outward level by level (fallback)
    if not parent_info:
        print(f"      ❌ Cannot continue search - no parent info available")
        return None
    
    # parent_info is a tuple (parent_container, parent_path)
    parent_container, current_search_path = parent_info
    current_search_path = current_search_path.copy()
    
    print(f"      🔍 Step 3: Searching outward level by level (max {max_levels} levels)")
    # Search outward up to max_levels
    for level in range(max_levels):
        if not current_search_path:
            print(f"        Level {level}: No more parent paths available")
            break
            
        print(f"        Level {level}: Searching at path depth {len(current_search_path)}")
        # Get the container at current search level
        search_container = get_container_at_path(container_hierarchy, current_search_path)
        
        if not search_container:
            print(f"        Level {level}: Could not access container")
            break
        
        # First try to find sibling labels at this level
        if level == 0:  # Only try sibling search at the first outward level
            print(f"        Level {level}: Checking for sibling labels")
            sibling_label = find_sibling_labels(target_container, search_container)
            if sibling_label:
                print(f"        Level {level}: ✅ Found sibling label: '{sibling_label}'")
                return sibling_label
            else:
                print(f"        Level {level}: No sibling labels found")
        
        # Fallback: Search within this level's container
        print(f"        Level {level}: Searching within container for names")
        found_name = find_name_in_children(search_container)
        
        if found_name:
            print(f"        Level {level}: ✅ Found name in container: '{found_name}'")
            return found_name
        else:
            print(f"        Level {level}: No names found in container")
        
        # Move up one level (remove last path element)
        if current_search_path:
            current_search_path.pop()
    
    print(f"      ❌ Inside-out search completed - no suitable name found")
    return None


def find_better_names_for_empty_containers(tags_data, container_data):
    """
    Find better names for containers with empty names using inside-out search.
    
    Args:
        tags_data: List of tag dictionaries
        container_data: The accessibility tree data
    
    Returns:
        Tuple of (filtered_tags_data, element_names)
    """
    tags_list = json.loads(tags_data) if isinstance(tags_data, str) else tags_data
    
    filtered_tags = []
    element_names = []
    elements_to_remove = []
    
    print(f"\n🔍 Processing {len(tags_list)} elements for name finding...")
    
    for i, tag in enumerate(tags_list):
        current_name = tag.get('name', '')
        tf623_id = tag.get('tf623_id')
        role = tag.get('role', 'unknown')
        
        print(f"\n  Element {i}: tf623_id={tf623_id}, role={role}, current_name='{current_name}'")
        
        if not current_name and tf623_id:
            # Try inside-out search for a better name
            print(f"    🔎 Searching for name for empty element {tf623_id}...")
            better_name = find_name_with_inside_out_search(tf623_id, container_data)
            
            if better_name:
                print(f"    ✅ Found name: '{better_name}'")
                # Update the tag with the better name
                tag['name'] = better_name
                filtered_tags.append(tag)
                element_names.append(better_name)
            else:
                print(f"    ❌ No suitable name found, marking for removal")
                # Mark for removal if no suitable name found
                elements_to_remove.append(i)
        else:
            print(f"    ✅ Keeping element with existing name: '{current_name}'")
            # Keep elements that already have names
            filtered_tags.append(tag)
            element_names.append(current_name)
    
    print(f"\n📊 Summary: {len(filtered_tags)} elements kept, {len(elements_to_remove)} elements removed")
    return filtered_tags, element_names

def process_form_elements(form_elements_data, accessibility_tree, container_tf623_id):
    """
    Main API function to process form elements and return fully filtered elements with names.
    
    Args:
        form_elements_data: Raw form elements data from AgentQL (list of elements)
        accessibility_tree: Accessibility tree from the page
        container_tf623_id: The tf623_id of the main container
    
    Returns:
        tuple: (filtered_elements_list, element_names_list)
    """
    try:
        # Step 1: Convert AgentQL elements to dict format and filter hidden elements
        parsed_tags = []
        hidden_indexes = []
        
        for i, element in enumerate(form_elements_data):
            # Convert AgentQL Locator element to dict format
            try:
                if hasattr(element, 'get_attribute'):
                    # AgentQL Locator object
                    element_dict = {
                        'tf623_id': element.get_attribute('tf623_id') or '',
                        'name': element.get_attribute('name') or '',
                        'attributes': {},  # We'll populate this with specific attributes
                        'role': element.get_attribute('role') or ''
                    }
                    
                    # Get common attributes that might indicate hidden elements
                    for attr in ['type', 'style', 'class', 'hidden', 'aria-hidden', 'display']:
                        value = element.get_attribute(attr)
                        if value:
                            element_dict['attributes'][attr] = value
                            
                elif hasattr(element, 'tf623_id'):
                    # Object with direct attributes
                    element_dict = {
                        'tf623_id': getattr(element, 'tf623_id', ''),
                        'name': getattr(element, 'name', ''),
                        'attributes': getattr(element, 'attributes', {}),
                        'role': getattr(element, 'role', '')
                    }
                else:
                    # Already in dict format
                    element_dict = element
                
                parsed_tags.append(element_dict)
                
                # Check if element is hidden
                if contains_hidden(element_dict):
                    hidden_indexes.append(i)
                    
            except Exception as e:
                print(f"❌ Error processing element {i}: {e}")
                continue
        
        # Create filtered list without hidden elements
        filtered_elements = []
        for i, element in enumerate(parsed_tags):
            if i not in hidden_indexes:
                filtered_elements.append(element)
        
        print(f"✅ Filtered out {len(hidden_indexes)} hidden elements")
        print(f"✅ Remaining elements: {len(filtered_elements)}")
        
        # Step 2: Extract names from filtered elements
        element_names = []
        for element in filtered_elements:
            name = element.get('name', '').strip()
            element_names.append(name)
        
        # Step 3: Use the full accessibility tree for name improvements
        # The inside-out search needs access to the full tree, not just a sub-container
        if accessibility_tree:
            # Step 4: Find better names for empty containers
            filtered_tags_json = json.dumps(filtered_elements, default=str)
            improved_elements, improved_names = find_better_names_for_empty_containers(filtered_tags_json, accessibility_tree)
            
            # Step 5: Use the improved elements and names
            filtered_elements = improved_elements
            element_names = improved_names
        
        print(f"\n📋 Final filtered elements: {len(filtered_elements)}")
        print(f"📋 Final element names: {len(element_names)}")
        
        # Step 7: Sort elements by tf623_id to ensure proper ordering
        if filtered_elements and element_names:
            # Create pairs of (element, name) with their tf623_id for sorting
            element_pairs = []
            for i, element in enumerate(filtered_elements):
                # tf623_id is stored directly in the element dict, not in attributes
                tf623_id_str = element.get('tf623_id', '')
                # Convert to int for proper numerical sorting, use infinity for missing/invalid IDs
                try:
                    tf623_id = int(tf623_id_str) if tf623_id_str else float('inf')
                except (ValueError, TypeError):
                    tf623_id = float('inf')
                element_pairs.append((tf623_id, element, element_names[i]))
            
            # Sort by tf623_id
            element_pairs.sort(key=lambda x: x[0])
            
            # Rebuild the lists in sorted order
            filtered_elements = [pair[1] for pair in element_pairs]
            element_names = [pair[2] for pair in element_pairs]
            
            print(f"✅ Sorted {len(filtered_elements)} elements by tf623_id")
        
        # Return filtered elements and their corresponding names
        return filtered_elements, element_names
        
    except Exception as e:
        print(f"❌ Error in process_form_elements: {e}")
        return [], []