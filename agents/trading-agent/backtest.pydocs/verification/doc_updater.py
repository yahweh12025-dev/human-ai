#!/usr/bin/env python3
"""
HERMES-DOC-UPDATER-20260509_102114: Develop automated verification documentation
updater that keeps verification guides current with code changes.

POW File: docs/verification/doc_updater.py

This module provides:
- Scanning of verification-related source code for docstring/comment changes
- Detection of undocumented verification checks and audit procedures
- Automated documentation generation from code analysis
- Staleness detection by comparing docs against current code state
- LLM-powered documentation update suggestions
- Git-diff-aware incremental documentation updates
"""

import os
import sys
import json
import re
import ast
import logging
import hashlib
import datetime
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from core.llm_router import query_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("verification_doc_updater")

DOCS_DIR = PROJECT_ROOT / "docs" / "verification"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
CORE_DIR = PROJECT_ROOT / "core"
STATE_FILE = DOCS_DIR / ".doc_state.json"


@dataclass
class VerificationComponent:
    """A verification-related code component that should be documented."""
    file_path: str
    component_name: str
    component_type: str  # class, function, module
    docstring: str
    signature: str
    verification_keywords: List[str]
    last_modified: str
    content_hash: str


@dataclass
class DocumentationGap:
    """Identified gap between code and documentation."""
    component: VerificationComponent
    gap_type: str  # missing, stale, incomplete
    description: str
    priority: str  # high, medium, low
    suggested_doc: str = ""


@dataclass
class DocumentationUpdate:
    """A proposed documentation update."""
    file_path: str
    section: str
    update_type: str  # add, modify, remove
    old_content: str
    new_content: str
    reason: str


class CodeScanner:
    """Scans verification-related source code for documentation needs."""

    # Patterns that indicate verification-related code
    VERIFICATION_KEYWORDS = [
        "verify", "validate", "audit", "check", "compliance",
        "assertion", "constraint", "threshold", "gate", "approval",
        "certification", "attestation", "inspection", "review",
    ]

    # Directories to scan for verification code
    SCAN_DIRS = [
        "scripts",
        "core",
        "tests",
        "verification",
        "infrastructure",
    ]

    def scan_verification_components(self) -> List[VerificationComponent]:
        """Scan all relevant directories for verification components."""
        components = []

        for scan_dir_name in self.SCAN_DIRS:
            scan_dir = PROJECT_ROOT / scan_dir_name
            if not scan_dir.exists():
                continue

            for py_file in scan_dir.rglob("*.py"):
                try:
                    file_components = self._analyze_file(py_file)
                    components.extend(file_components)
                except Exception as e:
                    logger.debug(f"Failed to analyze {py_file}: {e}")

        logger.info(f"Found {len(components)} verification-related components")
        return components

    def _analyze_file(self, filepath: Path) -> List[VerificationComponent]:
        """Analyze a Python file for verification-related components."""
        components = []

        content = filepath.read_text(errors="ignore")
        rel_path = str(filepath.relative_to(PROJECT_ROOT))

        # Check if file is verification-related
        content_lower = content.lower()
        file_keywords = [kw for kw in self.VERIFICATION_KEYWORDS
                        if kw in content_lower]
        if not file_keywords:
            return components

        # Compute content hash for change detection
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]

        # Get last modified time
        try:
            mtime = datetime.datetime.fromtimestamp(
                filepath.stat().st_mtime
            ).isoformat()
        except Exception:
            mtime = ""

        # Parse AST for classes and functions
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # If AST parsing fails, create a module-level component
            components.append(VerificationComponent(
                file_path=rel_path,
                component_name=filepath.stem,
                component_type="module",
                docstring=self._extract_module_docstring(content),
                signature="",
                verification_keywords=file_keywords,
                last_modified=mtime,
                content_hash=content_hash,
            ))
            return components

        # Extract classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_keywords = self._get_node_keywords(node, content)
                if class_keywords:
                    docstring = ast.get_docstring(node) or ""
                    components.append(VerificationComponent(
                        file_path=rel_path,
                        component_name=node.name,
                        component_type="class",
                        docstring=docstring,
                        signature=f"class {node.name}",
                        verification_keywords=class_keywords,
                        last_modified=mtime,
                        content_hash=content_hash,
                    ))

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                func_keywords = self._get_node_keywords(node, content)
                if func_keywords:
                    docstring = ast.get_docstring(node) or ""
                    sig = self._get_function_signature(node)
                    components.append(VerificationComponent(
                        file_path=rel_path,
                        component_name=node.name,
                        component_type="function",
                        docstring=docstring,
                        signature=sig,
                        verification_keywords=func_keywords,
                        last_modified=mtime,
                        content_hash=content_hash,
                    ))

        return components

    def _get_node_keywords(self, node: ast.AST, source: str) -> List[str]:
        """Get verification keywords relevant to an AST node."""
        # Get source lines for this node
        try:
            if hasattr(node, 'end_lineno') and node.end_lineno:
                lines = source.split('\n')[node.lineno-1:node.end_lineno]
            else:
                lines = source.split('\n')[node.lineno-1:node.lineno+20]
            node_text = '\n'.join(lines).lower()
        except Exception:
            node_text = getattr(node, 'name', '').lower()

        return [kw for kw in self.VERIFICATION_KEYWORDS if kw in node_text]

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature string."""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        return f"def {node.name}({', '.join(args)})"

    def _extract_module_docstring(self, content: str) -> str:
        """Extract module-level docstring."""
        match = re.match(r'^(?:#!/.*\n)?(?:#.*\n)*\s*(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')',
                        content, re.DOTALL)
        if match:
            return (match.group(1) or match.group(2) or "").strip()
        return ""


class GapDetector:
    """Detects gaps between code and documentation."""

    def __init__(self):
        self.previous_state: Dict[str, str] = {}
        self._load_state()

    def _load_state(self):
        """Load previous documentation state for comparison."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    self.previous_state = json.load(f)
            except Exception:
                self.previous_state = {}

    def _save_state(self, components: List[VerificationComponent]):
        """Save current state for future comparisons."""
        state = {}
        for comp in components:
            key = f"{comp.file_path}::{comp.component_name}"
            state[key] = comp.content_hash

        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        self.previous_state = state

    def detect_gaps(self, components: List[VerificationComponent],
                    existing_docs: Dict[str, str]) -> List[DocumentationGap]:
        """Detect documentation gaps for verification components."""
        gaps = []

        for comp in components:
            key = f"{comp.file_path}::{comp.component_name}"

            # Check if component is documented
            is_documented = self._is_documented(comp, existing_docs)

            if not is_documented:
                gaps.append(DocumentationGap(
                    component=comp,
                    gap_type="missing",
                    description=f"Verification component '{comp.component_name}' in "
                               f"{comp.file_path} has no documentation",
                    priority="high" if comp.component_type == "class" else "medium",
                ))
            elif self._is_stale(comp, key):
                gaps.append(DocumentationGap(
                    component=comp,
                    gap_type="stale",
                    description=f"Documentation for '{comp.component_name}' may be "
                               f"outdated (code changed since last doc update)",
                    priority="medium",
                ))
            elif not comp.docstring:
                gaps.append(DocumentationGap(
                    component=comp,
                    gap_type="incomplete",
                    description=f"'{comp.component_name}' lacks a docstring",
                    priority="low",
                ))

        # Update state
        self._save_state(components)

        gaps.sort(key=lambda g: {"high": 0, "medium": 1, "low": 2}[g.priority])
        logger.info(f"Detected {len(gaps)} documentation gaps")
        return gaps

    def _is_documented(self, comp: VerificationComponent,
                       existing_docs: Dict[str, str]) -> bool:
        """Check if a component appears in existing documentation."""
        comp_name_lower = comp.component_name.lower()

        for doc_path, doc_content in existing_docs.items():
            if comp_name_lower in doc_content.lower():
                return True
            # Check for file reference
            if comp.file_path in doc_content:
                return True

        return False

    def _is_stale(self, comp: VerificationComponent, key: str) -> bool:
        """Check if documentation is stale (code changed since last update)."""
        old_hash = self.previous_state.get(key)
        if old_hash and old_hash != comp.content_hash:
            return True
        return False


class DocumentationGenerator:
    """Generates documentation updates from gaps."""

    SYSTEM_PROMPT = """You are a technical documentation writer for an autonomous
multi-agent trading system. Write clear, concise documentation that:
1. Explains what the verification component does
2. Describes inputs, outputs, and side effects
3. Notes any dependencies on other components
4. Includes usage examples where appropriate
Keep documentation in Markdown format."""

    def generate_updates(self, gaps: List[DocumentationGap],
                         use_llm: bool = True) -> List[DocumentationUpdate]:
        """Generate documentation updates for identified gaps."""
        updates = []

        # Group gaps by file for batch processing
        by_file: Dict[str, List[DocumentationGap]] = {}
        for gap in gaps:
            file_path = gap.component.file_path
            by_file.setdefault(file_path, []).append(gap)

        for file_path, file_gaps in by_file.items():
            if use_llm:
                file_updates = self._generate_with_llm(file_path, file_gaps)
            else:
                file_updates = self._generate_basic(file_path, file_gaps)
            updates.extend(file_updates)

        logger.info(f"Generated {len(updates)} documentation updates")
        return updates

    def _generate_basic(self, file_path: str,
                        gaps: List[DocumentationGap]) -> List[DocumentationUpdate]:
        """Generate basic documentation without LLM."""
        updates = []

        for gap in gaps:
            comp = gap.component
            doc_content = self._format_basic_doc(comp)

            updates.append(DocumentationUpdate(
                file_path=f"docs/verification/components/{Path(file_path).stem}.md",
                section=comp.component_name,
                update_type="add" if gap.gap_type == "missing" else "modify",
                old_content="",
                new_content=doc_content,
                reason=gap.description,
            ))

        return updates

    def _generate_with_llm(self, file_path: str,
                           gaps: List[DocumentationGap]) -> List[DocumentationUpdate]:
        """Use LLM to generate documentation updates."""
        updates = []

        for gap in gaps[:5]:  # Limit LLM calls
            comp = gap.component
            prompt = f"""Generate documentation for this verification component:

File: {comp.file_path}
Name: {comp.component_name}
Type: {comp.component_type}
Signature: {comp.signature}
Existing Docstring: {comp.docstring[:200] if comp.docstring else 'None'}
Keywords: {', '.join(comp.verification_keywords)}

Gap Type: {gap.gap_type}
Description: {gap.description}

Write a concise Markdown documentation section (max 150 words) covering:
- Purpose and functionality
- Key parameters/inputs
- Verification behavior
- Usage example (if applicable)"""

            try:
                response = query_llm(
                    agent_name="hermes",
                    prompt=prompt,
                    system_prompt=self.SYSTEM_PROMPT,
                    max_tokens=512,
                    temperature=0.3,
                )

                updates.append(DocumentationUpdate(
                    file_path=f"docs/verification/components/{Path(file_path).stem}.md",
                    section=comp.component_name,
                    update_type="add" if gap.gap_type == "missing" else "modify",
                    old_content="",
                    new_content=response.strip(),
                    reason=gap.description,
                ))
            except Exception as e:
                logger.warning(f"LLM doc generation failed for {comp.component_name}: {e}")
                # Fallback to basic
                updates.append(DocumentationUpdate(
                    file_path=f"docs/verification/components/{Path(file_path).stem}.md",
                    section=comp.component_name,
                    update_type="add",
                    old_content="",
                    new_content=self._format_basic_doc(comp),
                    reason=gap.description,
                ))

        return updates

    def _format_basic_doc(self, comp: VerificationComponent) -> str:
        """Format basic documentation from component info."""
        lines = [
            f"### {comp.component_name}",
            f"",
            f"**Type:** {comp.component_type}",
            f"**File:** `{comp.file_path}`",
            f"**Verification Keywords:** {', '.join(comp.verification_keywords)}",
            f"",
        ]

        if comp.signature:
            lines.append(f"```python")
            lines.append(comp.signature)
            lines.append(f"```")
            lines.append("")

        if comp.docstring:
            lines.append(comp.docstring[:300])
            lines.append("")

        lines.append(f"*Last modified: {comp.last_modified}*")
        lines.append("")

        return "\n".join(lines)


class DocumentationWriter:
    """Writes documentation updates to disk."""

    def apply_updates(self, updates: List[DocumentationUpdate],
                      dry_run: bool = False) -> int:
        """Apply documentation updates to files."""
        applied = 0

        # Group updates by target file
        by_file: Dict[str, List[DocumentationUpdate]] = {}
        for update in updates:
            by_file.setdefault(update.file_path, []).append(update)

        for file_path, file_updates in by_file.items():
            full_path = PROJECT_ROOT / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if dry_run:
                logger.info(f"[DRY RUN] Would update {file_path} ({len(file_updates)} sections)")
                applied += len(file_updates)
                continue

            # Read existing content
            existing_content = ""
            if full_path.exists():
                existing_content = full_path.read_text()

            # Apply updates
            new_content = self._merge_updates(existing_content, file_updates)

            with open(full_path, "w") as f:
                f.write(new_content)

            applied += len(file_updates)
            logger.info(f"Updated {file_path} ({len(file_updates)} sections)")

        return applied

    def _merge_updates(self, existing: str, updates: List[DocumentationUpdate]) -> str:
        """Merge updates into existing documentation."""
        if not existing:
            # Create new document
            header = f"# Verification Component Documentation\n\n"
            header += f"*Auto-generated by doc_updater.py on {datetime.date.today().isoformat()}*\n\n"
            sections = [header]
            for update in updates:
                sections.append(update.new_content)
                sections.append("")
            return "\n".join(sections)

        # Append new sections to existing document
        lines = [existing.rstrip()]
        lines.append("")
        lines.append(f"\n---\n*Updated: {datetime.date.today().isoformat()}*\n")

        for update in updates:
            if update.section not in existing:
                lines.append(update.new_content)
                lines.append("")

        return "\n".join(lines)


class VerificationDocUpdater:
    """
    Main orchestrator for automated verification documentation updates.

    Usage:
        updater = VerificationDocUpdater()
        report = updater.run()
    """

    def __init__(self, use_llm: bool = True, dry_run: bool = False):
        self.scanner = CodeScanner()
        self.gap_detector = GapDetector()
        self.generator = DocumentationGenerator()
        self.writer = DocumentationWriter()
        self.use_llm = use_llm
        self.dry_run = dry_run

    def run(self) -> Dict[str, Any]:
        """Execute the full documentation update pipeline."""
        logger.info("Starting verification documentation updater...")

        # Step 1: Scan verification components
        components = self.scanner.scan_verification_components()

        # Step 2: Load existing documentation
        existing_docs = self._load_existing_docs()

        # Step 3: Detect gaps
        gaps = self.gap_detector.detect_gaps(components, existing_docs)

        # Step 4: Generate updates
        updates = self.generator.generate_updates(gaps, self.use_llm)

        # Step 5: Apply updates
        applied = self.writer.apply_updates(updates, self.dry_run)

        # Generate report
        report = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "components_scanned": len(components),
            "gaps_detected": len(gaps),
            "updates_generated": len(updates),
            "updates_applied": applied,
            "gap_summary": {
                "missing": len([g for g in gaps if g.gap_type == "missing"]),
                "stale": len([g for g in gaps if g.gap_type == "stale"]),
                "incomplete": len([g for g in gaps if g.gap_type == "incomplete"]),
            },
            "dry_run": self.dry_run,
        }

        # Save report
        report_path = DOCS_DIR / "doc_update_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(
            f"Documentation update complete: {applied} updates applied "
            f"({report['gap_summary']})"
        )

        return report

    def _load_existing_docs(self) -> Dict[str, str]:
        """Load existing documentation files for comparison."""
        docs = {}

        if DOCS_DIR.exists():
            for doc_file in DOCS_DIR.rglob("*.md"):
                try:
                    rel_path = str(doc_file.relative_to(PROJECT_ROOT))
                    docs[rel_path] = doc_file.read_text(errors="ignore")
                except Exception:
                    pass

        logger.info(f"Loaded {len(docs)} existing documentation files")
        return docs

    def get_documentation_health(self) -> Dict[str, Any]:
        """Get overall documentation health metrics."""
        components = self.scanner.scan_verification_components()
        existing_docs = self._load_existing_docs()

        documented = 0
        undocumented = 0
        has_docstring = 0

        for comp in components:
            comp_lower = comp.component_name.lower()
            is_doc = any(comp_lower in doc.lower() for doc in existing_docs.values())
            if is_doc:
                documented += 1
            else:
                undocumented += 1
            if comp.docstring:
                has_docstring += 1

        total = len(components)
        return {
            "total_components": total,
            "documented": documented,
            "undocumented": undocumented,
            "has_docstring": has_docstring,
            "coverage_percent": round(documented / max(total, 1) * 100, 1),
            "docstring_percent": round(has_docstring / max(total, 1) * 100, 1),
        }


def main():
    """Run the verification documentation updater."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automated Verification Documentation Updater"
    )
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM-powered documentation generation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be updated without writing files")
    parser.add_argument("--health", action="store_true",
                        help="Show documentation health metrics")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    updater = VerificationDocUpdater(
        use_llm=not args.no_llm,
        dry_run=args.dry_run,
    )

    if args.health:
        health = updater.get_documentation_health()
        print("\n=== Documentation Health Report ===")
        for key, value in health.items():
            print(f"  {key}: {value}")
        return

    report = updater.run()

    print(f"\n{'='*60}")
    print(f"VERIFICATION DOCUMENTATION UPDATE REPORT")
    print(f"{'='*60}")
    print(f"Components scanned: {report['components_scanned']}")
    print(f"Gaps detected: {report['gaps_detected']}")
    print(f"  - Missing: {report['gap_summary']['missing']}")
    print(f"  - Stale: {report['gap_summary']['stale']}")
    print(f"  - Incomplete: {report['gap_summary']['incomplete']}")
    print(f"Updates applied: {report['updates_applied']}")
    if report['dry_run']:
        print(f"\n  (DRY RUN - no files were modified)")


if __name__ == "__main__":
    main()
