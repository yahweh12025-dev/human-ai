import json
import re
from collections import Counter
from pathlib import Path

def analyze_logs(log_path="/home/ubuntu/human-ai/infrastructure/logs/master_log.json"):
    print(f"Analyzing logs from: {log_path}")
    errors = []
    
    try:
        with open(log_path, 'r') as f:
            content = f.read()
            # Use a very loose regex to find anything that looks like a JSON object
            # and handle the possibility of nested brackets
            matches = re.finditer(r'\{.*?\}(?=\s*,\s*\{|\s*\]|\s*$)', content, re.DOTALL)
            # If that fails, we'll just use a line-by-line approach for the hybrid file
            if not matches:
                f.seek(0)
                for line in f:
                    if '{' in line and '}' in line:
                        # Try to extract a JSON object from the line
                        start = line.find('{')
                        end = line.rfind('}') + 1
                        try:
                            entry = json.loads(line[start:end])
                            msg = entry.get("message", "")
                            if any(keyword in msg.lower() for keyword in ["error", "exception", "failed", "failure", "indentationerror", "syntaxerror"]):
                                errors.append(entry)
                        except:
                            continue
            else:
                for match in matches:
                    try:
                        entry = json.loads(match.group())
                        msg = entry.get("message", "")
                        if any(keyword in msg.lower() for keyword in ["error", "exception", "failed", "failure", "indentationerror", "syntaxerror"]):
                            errors.append(entry)
                    except:
                        continue
    except Exception as e:
        return f"Error reading logs: {e}"

    if not errors:
        # Fallback: just grep the file for error keywords and count them
        return "No structured JSON errors found. Try using grep for a quick audit."

    patterns = Counter()
    for err in errors:
        msg = err.get("message", "")
        source = err.get("source", "unknown")
        # Create a signature based on the first line of the error and source
        sig = f"[{source}] {msg.splitlines()[0][:60]}"
        patterns[sig] += 1

    sorted_patterns = patterns.most_common(10)
    
    report = ["### Swarm Failure Pattern Report", "━━━━━━━━━━━━━━━━━━━━━━━━"]
    for pattern, count in sorted_patterns:
        report.append(f"Count: {count} | Pattern: {pattern}")
    
    report.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    report.append(f"Total errors analyzed: {len(errors)}")
    
    return "\n".join(report)

if __name__ == "__main__":
    print(analyze_logs())
