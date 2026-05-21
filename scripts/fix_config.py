import re

with open('_config.yml', 'r') as f:
    lines = f.readlines()

# Find the exclude block
in_exclude = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == 'exclude:':
        in_exclude = True
        continue
    if in_exclude:
        # Check if we are still in the exclude block: line starts with two spaces and a dash
        if re.match(r'^  - ', line):
            # This is a list item in the exclude block
            # We want to quote the scalar if it's not already quoted and starts with *
            # Pattern: ^  - (.*?)(\s*(#.*)?)$
            match = re.match(r'^(\s*-\s*)(.*)(\s*(#.*)?)$', line)
            if match:
                indent_dash = match.group(1)  # includes the dash and spaces before it
                scalar = match.group(2)
                rest = match.group(3)  # includes comment and trailing spaces
                # Check if scalar is already quoted (single or double quotes)
                if not (scalar.startswith('"') and scalar.endswith('"') or \
                        scalar.startswith("'") and scalar.endswith("'")):
                    # If scalar starts with *, we need to quote it
                    if scalar.strip().startswith('*'):
                        scalar = '"' + scalar + '"'
                        lines[i] = indent_dash + scalar + rest + '\n'
        else:
            # We've left the exclude block
            break

with open('_config.yml', 'w') as f:
    f.writelines(lines)
