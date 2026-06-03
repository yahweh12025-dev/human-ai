import os
import re
import yaml

def parse_md(filepath):
    """
    Parses an Obsidian Markdown file into frontmatter and body.
    Returns: (frontmatter_dict, body_string)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Frontmatter is between two --- markers at the start of the file
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if match:
        frontmatter_raw = match.group(1)
        body = match.group(2)
        try:
            frontmatter = yaml.safe_load(frontmatter_raw) or {}
        except yaml.YAMLError:
            frontmatter = {}
        return frontmatter, body
    else:
        return {}, content

def update_frontmatter(filepath, updates_dict):
    """
    Updates keys in the frontmatter of an Obsidian Markdown file.
    """
    frontmatter, body = parse_md(filepath)
    frontmatter.update(updates_dict)
    
    # Convert dict back to YAML
    frontmatter_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"---\n{frontmatter_yaml}\n---\n{body}")

def append_to_body(filepath, markdown_string):
    """
    Safely appends text to the body of an Obsidian Markdown file.
    """
    frontmatter, body = parse_md(filepath)
    
    # Ensure a newline between existing body and new content
    new_body = body.rstrip() + "\n\n" + markdown_string + "\n"
    
    # Re-write with frontmatter
    frontmatter_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True).strip() if frontmatter else ""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        if frontmatter_yaml:
            f.write(f"---\n{frontmatter_yaml}\n---\n{new_body}")
        else:
            f.write(new_body)

if __name__ == "__main__":
    # Simple test
    test_file = "test_note.md"
    with open(test_file, "w") as f:
        f.write("---\ntags: [test]\nstatus: draft\n---\nHello World")
    
    print("Parsing...")
    fm, body = parse_md(test_file)
    print(f"FM: {fm}, Body: {body}")
    
    print("Updating...")
    update_frontmatter(test_file, {"status": "published", "author": "pi"})
    
    print("Appending...")
    append_to_body(test_file, "This is an appended line.")
    
    with open(test_file, "r") as f:
        print("\nFinal content:\n" + f.read())
    
    os.remove(test_file)
