# pi-obsidian-md-parser

A skill that helps Pi read and edit Markdown files without breaking your Obsidian frontmatter/metadata.

## Description

This skill provides utilities to safely parse, modify, and save Obsidian Markdown files while preserving YAML frontmatter and metadata.

## Usage

Import and use the provided functions in your Pi workflows.

## Functions

- `parse_markdown(filepath)`: Returns (frontmatter_dict, body_string)
- `update_frontmatter(filepath, updates_dict)`: Updates frontmatter keys
- `append_to_body(filepath, markdown_string)`: Safely appends to the body

## Example

```python
from skills.pi_obsidian_md_parser import parse_md, update_frontmatter

frontmatter, body = parse_md('my_note.md')
frontmatter['tags'] = ['ai', 'research']
update_frontmatter('my_note.md', frontmatter)
```