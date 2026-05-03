#!/usr/bin/env python3
import os
import json

def update_memory_files():
    """Update .hermes/memory.md and docs/memory.md with user's request for concise responses and Obsidian integration."""
    # Update .hermes/memory.md
    hermes_memory_path = '/home/yahwehatwork/human-ai/.hermes/memory.md'
    if os.path.exists(hermes_memory_path):
        with open(hermes_memory_path, 'r') as f:
            lines = f.readlines()
        # Insert a note after the first line (the header) or at the beginning?
        # We'll insert after the first line if it starts with '# Hermes Agent Memory'
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if line.startswith('# Hermes Agent Memory') and not inserted:
                new_lines.append('\n## User Request (2026-04-30)\n')
                new_lines.append('- More concise responses without repetition from previous messages.\n')
                new_lines.append('- Add Obsidian integration to roadmap, todo list, and documentation for local memory management.\n')
                new_lines.append('\n')
                inserted = True
        with open(hermes_memory_path, 'w') as f:
            f.writelines(new_lines)
        print(f"Updated {hermes_memory_path}")

    # Update docs/memory.md
    docs_memory_path = '/home/yahwehatwork/human-ai/docs/memory.md'
    if os.path.exists(docs_memory_path):
        with open(docs_memory_path, 'r') as f:
            content = f.read()
        # We'll append a new entry at the end with a timestamp and the user's request.
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        entry = f'''\n---\n\n## User Request (Updated: {timestamp})\n- Requested more concise responses without repetition from previous messages.\n- Requested adding Obsidian integration to roadmap, todo list, and documentation for local memory management in the human-ai repo.\n'''
        with open(docs_memory_path, 'w') as f:
            f.write(content + entry)
        print(f"Updated {docs_memory_path}")

def update_roadmap_and_unified_plan():
    """Update ROADMAP.md and unified_plan.md to add Obsidian integration in Phase 3."""
    files_to_update = [
        '/home/yahwehatwork/human-ai/docs/ROADMAP.md',
        '/home/yahwehatwork/human-ai/docs/unified_plan.md'
    ]
    for file_path in files_to_update:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        with open(file_path, 'r') as f:
            lines = f.readlines()
        # Find the line index of the Phase 3 header (IN PROGRESS)
        header = '## Phase 3: Orchestration & Ecosystem 🚀 (IN PROGRESS)'
        try:
            header_idx = next(i for i, line in enumerate(lines) if line.strip() == header)
        except StopIteration:
            print(f"Header not found in {file_path}")
            continue
        # Find the start of the next section (next line that starts with '##' after header)
        next_section_idx = len(lines)
        for i in range(header_idx + 1, len(lines)):
            if lines[i].startswith('##'):
                next_section_idx = i
                break
        # Insert the new bullet at the position before the next section (so it becomes the last bullet in Phase 3)
        # But we want to insert after the header and before the existing bullets? Actually, we want to add to the list.
        # The list of bullets starts right after the header? Let's check: after the header, the next line is a bullet or blank?
        # We'll insert at header_idx + 1, but if there are existing bullets, we want to add after them? 
        # Simpler: insert at the line before the next section.
        new_bullet = '- [ ] **Obsidian Integration**: Integrate Obsidian for local knowledge management and memory enhancement\n'
        # Check if the bullet is already present to avoid duplicates
        if any('Obsidian Integration' in line for line in lines):
            print(f"Obsidian Integration already present in {file_path}")
        else:
            lines.insert(next_section_idx, new_bullet)
            with open(file_path, 'w') as f:
                f.writelines(lines)
            print(f"Updated {file_path}")

def update_todo_json():
    """Update infrastructure/configs/todo.json to add Obsidian integration task."""
    todo_path = '/home/yahwehatwork/human-ai/infrastructure/configs/todo.json'
    if not os.path.exists(todo_path):
        print(f"File not found: {todo_path}")
        return
    with open(todo_path, 'r') as f:
        data = json.load(f)
    # Add a new pending task for Obsidian integration
    new_task = {
        'id': 'obsidian-integration-1',
        'content': 'Obsidian Integration: Integrate Obsidian for local knowledge management and memory enhancement',
        'status': 'pending'
    }
    # Check if already present
    if any(task.get('id') == 'obsidian-integration-1' for task in data.get('pending', [])):
        print("Obsidian integration task already in todo.json")
    else:
        data['pending'].append(new_task)
        with open(todo_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Updated {todo_path}")

if __name__ == '__main__':
    update_memory_files()
    update_roadmap_and_unified_plan()
    update_todo_json()
    print('All updates completed.')