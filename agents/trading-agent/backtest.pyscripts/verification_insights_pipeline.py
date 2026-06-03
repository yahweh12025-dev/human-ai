#!/usr/bin/env python3
"""
HERMES-VERIF-INSIGHTS-20260509_102114: Create verification insights pipeline
that automatically extracts actionable items from completed audits and creates
improvement tasks.

POW File: scripts/verification_insights_pipeline.py

This module provides:
- Automated parsing of verification audit reports (markdown format)
- Pattern extraction from audit findings across multiple dimensions
- LLM-powered insight synthesis from raw findings
- Automatic task generation from identified improvement areas
- Priority scoring for generated tasks based on impact and frequency
- Integration with unified_tasks.json for task injection
"""

import os
import sys
import json
import re
import logging
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.llm_router import query_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("verification_insights_pipeline")

AUDIT_DIR = PROJECT_ROOT / "docs" / "verification"
VALIDATION_DIR = PROJECT_ROOT / "validation"
INSIGHTS_OUTPUT_DIR = PROJECT_ROOT / "data" / "verification_insights"
UNIFIED_TASKS_FILE = PROJECT_ROOT / "unified_tasks.json"


@dataclass
class AuditFinding:
    """A single finding from a verification audit."""
    audit_id: str
    category: str  # security, performance, correctness, compliance
    severity: str  # critical, high, medium, low
    description: str
    affected_component: str
    recommendation: str = ""
    resolved: bool = False


@dataclass
class InsightPattern:
    """A recurring pattern identified across multiple audits."""
    pattern_id: str
    category: str
    description: str
    frequency: int  # how many audits this pattern appears in
    affected_components: List[str]
    severity_distribution: Dict[str, int]
    first_seen: str
    last_seen: str
    trend: str  # increasing, stable, decreasing
    recommended_action: str = ""


@dataclass
class GeneratedTask:
    """A task generated from verification insights."""
    task_id: str
    title: str
    description: str
    priority: int  # 1-3
    suggested_agent: str
    source_patterns: List[str]
    estimated_impact: str  # high, medium, low
    pow_file: str


@dataclass
class InsightReport:
    """Complete insight report from pipeline execution."""
    generated_at: str
    audits_analyzed: int
    findings_extracted: int
    patterns_identified: int
    tasks_generated: int
    top_patterns: List[Dict[str, Any]]
    generated_tasks: List[Dict[str, Any]]
    trend_summary: Dict[str, Any]


class AuditParser:
    """Parses verification audit reports from markdown and JSON formats."""

    def parse_audit_directory(self, directory: Path) -> List[AuditFinding]:
        """Parse all audit files in a directory."""
        findings = []

        if not directory.exists():
            logger.warning(f"Audit directory not found: {directory}")
            return findings

        # Parse markdown audits
        for md_file in sorted(directory.glob("audit_*.md")):
            try:
                file_findings = self._parse_markdown_audit(md_file)
                findings.extend(file_findings)
            except Exception as e:
                logger.debug(f"Failed to parse {md_file.name}: {e}")

        # Parse JSON validation reports
        if VALIDATION_DIR.exists():
            for json_file in sorted(VALIDATION_DIR.glob("*.json")):
                try:
                    file_findings = self._parse_json_validation(json_file)
                    findings.extend(file_findings)
                except Exception as e:
                    logger.debug(f"Failed to parse {json_file.name}: {e}")

        logger.info(f"Extracted {len(findings)} findings from audit reports")
        return findings

    def _parse_markdown_audit(self, filepath: Path) -> List[AuditFinding]:
        """Parse a markdown audit report."""
        findings = []
        audit_id = filepath.stem  # e.g., "audit_142"

        content = filepath.read_text(errors="ignore")

        # Extract findings using common audit report patterns
        # Pattern 1: ## Finding / ## Issue sections
        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)

        for section in sections:
            if not section.strip():
                continue

            lines = section.strip().split("\n")
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()

            # Determine category from keywords
            category = self._classify_category(title + " " + body)
            severity = self._extract_severity(title + " " + body)
            component = self._extract_component(body)

            if category and len(body) > 10:
                findings.append(AuditFinding(
                    audit_id=audit_id,
                    category=category,
                    severity=severity,
                    description=title,
                    affected_component=component,
                    recommendation=self._extract_recommendation(body),
                    resolved="resolved" in body.lower() or "fixed" in body.lower(),
                ))

        return findings

    def _parse_json_validation(self, filepath: Path) -> List[AuditFinding]:
        """Parse a JSON validation report."""
        findings = []

        with open(filepath) as f:
            data = json.load(f)

        audit_id = filepath.stem

        # Handle different JSON report structures
        if isinstance(data, dict):
            # Look for findings/issues/results arrays
            for key in ["findings", "issues", "results", "checks", "violations"]:
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        if isinstance(item, dict):
                            findings.append(AuditFinding(
                                audit_id=audit_id,
                                category=item.get("category", "general"),
                                severity=item.get("severity", "medium"),
                                description=item.get("description", item.get("message", "")),
                                affected_component=item.get("component", item.get("file", "")),
                                recommendation=item.get("recommendation", ""),
                                resolved=item.get("resolved", False),
                            ))

        return findings

    def _classify_category(self, text: str) -> str:
        """Classify finding into a category."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["security", "vulnerab", "injection", "auth", "crypto"]):
            return "security"
        if any(w in text_lower for w in ["performance", "latency", "memory", "cpu", "slow"]):
            return "performance"
        if any(w in text_lower for w in ["error", "bug", "incorrect", "wrong", "fail"]):
            return "correctness"
        if any(w in text_lower for w in ["compliance", "standard", "policy", "convention"]):
            return "compliance"
        if any(w in text_lower for w in ["test", "coverage", "assertion"]):
            return "testing"
        if any(w in text_lower for w in ["deploy", "config", "infra"]):
            return "infrastructure"
        return "general"

    def _extract_severity(self, text: str) -> str:
        """Extract severity level from text."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["critical", "urgent", "severe"]):
            return "critical"
        if any(w in text_lower for w in ["high", "important", "major"]):
            return "high"
        if any(w in text_lower for w in ["low", "minor", "trivial", "cosmetic"]):
            return "low"
        return "medium"

    def _extract_component(self, text: str) -> str:
        """Extract affected component from text."""
        # Look for file paths
        path_match = re.search(r'[a-zA-Z_/]+\.py|[a-zA-Z_/]+\.js|[a-zA-Z_/]+\.yaml', text)
        if path_match:
            return path_match.group(0)

        # Look for component names
        comp_match = re.search(r'(?:in|for|component:?)\s+([a-zA-Z_]+)', text, re.IGNORECASE)
        if comp_match:
            return comp_match.group(1)

        return "unknown"

    def _extract_recommendation(self, text: str) -> str:
        """Extract recommendation from finding text."""
        # Look for recommendation sections
        rec_match = re.search(
            r'(?:recommend|suggest|fix|resolution|action)[:\s]+(.+?)(?:\n\n|\Z)',
            text, re.IGNORECASE | re.DOTALL
        )
        if rec_match:
            return rec_match.group(1).strip()[:200]
        return ""


class PatternExtractor:
    """Identifies recurring patterns across audit findings."""

    def extract_patterns(self, findings: List[AuditFinding]) -> List[InsightPattern]:
        """Extract patterns from a collection of findings."""
        # Group findings by category and similar descriptions
        category_groups = defaultdict(list)
        for finding in findings:
            category_groups[finding.category].append(finding)

        patterns = []

        for category, cat_findings in category_groups.items():
            # Cluster findings by similarity
            clusters = self._cluster_findings(cat_findings)

            for cluster_key, cluster_findings in clusters.items():
                if len(cluster_findings) < 2:
                    continue  # Only report patterns that appear multiple times

                # Build pattern from cluster
                severity_dist = Counter(f.severity for f in cluster_findings)
                components = list(set(f.affected_component for f in cluster_findings))
                audit_dates = sorted(f.audit_id for f in cluster_findings)

                pattern = InsightPattern(
                    pattern_id=f"PAT-{category[:3].upper()}-{len(patterns)+1:03d}",
                    category=category,
                    description=cluster_key,
                    frequency=len(cluster_findings),
                    affected_components=components[:10],
                    severity_distribution=dict(severity_dist),
                    first_seen=audit_dates[0] if audit_dates else "",
                    last_seen=audit_dates[-1] if audit_dates else "",
                    trend=self._determine_trend(cluster_findings),
                )
                patterns.append(pattern)

        # Sort by frequency
        patterns.sort(key=lambda p: p.frequency, reverse=True)
        logger.info(f"Identified {len(patterns)} recurring patterns")
        return patterns

    def _cluster_findings(self, findings: List[AuditFinding]) -> Dict[str, List[AuditFinding]]:
        """Cluster findings by similarity using keyword overlap."""
        clusters: Dict[str, List[AuditFinding]] = defaultdict(list)

        for finding in findings:
            # Normalize description to create cluster key
            key = self._normalize_description(finding.description)
            clusters[key].append(finding)

        return clusters

    def _normalize_description(self, description: str) -> str:
        """Normalize a description for clustering."""
        # Remove specific identifiers and numbers
        normalized = re.sub(r'\d+', 'N', description.lower())
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Extract key terms (words longer than 3 chars)
        words = [w for w in normalized.split() if len(w) > 3]

        # Take first 5 significant words as cluster key
        return " ".join(sorted(set(words[:8])))

    def _determine_trend(self, findings: List[AuditFinding]) -> str:
        """Determine if a pattern is increasing, stable, or decreasing."""
        if len(findings) < 3:
            return "stable"

        # Simple: compare first half vs second half frequency
        mid = len(findings) // 2
        first_half = len(findings[:mid])
        second_half = len(findings[mid:])

        ratio = second_half / max(first_half, 1)
        if ratio > 1.3:
            return "increasing"
        elif ratio < 0.7:
            return "decreasing"
        return "stable"


class InsightSynthesizer:
    """Uses LLM to synthesize insights from patterns."""

    SYSTEM_PROMPT = """You are a verification intelligence analyst for an autonomous
multi-agent trading system. Your job is to analyze patterns from verification audits
and generate actionable improvement tasks. Focus on:
1. Root cause identification
2. Cross-cutting concerns that affect multiple agents
3. Preventive measures rather than reactive fixes
4. Impact on trading performance and system reliability"""

    def synthesize_insights(self, patterns: List[InsightPattern],
                           use_llm: bool = True) -> List[GeneratedTask]:
        """Generate improvement tasks from identified patterns."""
        tasks = []

        # Group patterns by potential impact
        high_impact = [p for p in patterns if p.frequency >= 3 or
                      p.severity_distribution.get("critical", 0) > 0 or
                      p.severity_distribution.get("high", 0) >= 2]

        medium_impact = [p for p in patterns if p not in high_impact and
                        p.frequency >= 2]

        # Generate tasks for high-impact patterns
        for pattern in high_impact[:10]:
            task = self._generate_task_from_pattern(pattern, priority=1)
            if task:
                tasks.append(task)

        # Generate tasks for medium-impact patterns
        for pattern in medium_impact[:10]:
            task = self._generate_task_from_pattern(pattern, priority=2)
            if task:
                tasks.append(task)

        # Use LLM to generate cross-cutting tasks
        if use_llm and patterns:
            cross_cutting = self._generate_cross_cutting_tasks(patterns)
            tasks.extend(cross_cutting)

        logger.info(f"Generated {len(tasks)} improvement tasks from insights")
        return tasks

    def _generate_task_from_pattern(self, pattern: InsightPattern,
                                    priority: int) -> Optional[GeneratedTask]:
        """Generate a single task from a pattern."""
        # Determine best agent based on category
        agent_map = {
            "security": "OpenCode",
            "performance": "OpenCode",
            "correctness": "OpenCode",
            "compliance": "OpenCode",
            "testing": "OpenCode",
            "infrastructure": "OpenCode",
            "general": "Hermes",
        }
        suggested_agent = agent_map.get(pattern.category, "Hermes")

        # Generate task description
        title = f"Fix recurring {pattern.category} pattern: {pattern.description[:50]}"
        description = (
            f"Address recurring {pattern.category} issue found in {pattern.frequency} audits. "
            f"Affected components: {', '.join(pattern.affected_components[:5])}. "
            f"Trend: {pattern.trend}. "
            f"Severity distribution: {json.dumps(pattern.severity_distribution)}."
        )
        if pattern.recommended_action:
            description += f" Recommended: {pattern.recommended_action}"

        # Generate POW file path
        pow_file = f"scripts/fix_{pattern.pattern_id.lower().replace('-', '_')}.py"

        return GeneratedTask(
            task_id=f"INSIGHT-{pattern.pattern_id}",
            title=title,
            description=description,
            priority=priority,
            suggested_agent=suggested_agent,
            source_patterns=[pattern.pattern_id],
            estimated_impact="high" if priority == 1 else "medium",
            pow_file=pow_file,
        )

    def _generate_cross_cutting_tasks(self,
                                      patterns: List[InsightPattern]) -> List[GeneratedTask]:
        """Use LLM to identify cross-cutting improvement opportunities."""
        # Prepare pattern summary for LLM
        pattern_summary = "\n".join([
            f"- [{p.category}] {p.description} (freq: {p.frequency}, trend: {p.trend})"
            for p in patterns[:15]
        ])

        prompt = f"""Based on these recurring verification patterns, suggest 2-3 cross-cutting
improvement tasks that would address multiple patterns simultaneously:

Patterns:
{pattern_summary}

For each task, provide JSON:
[{{
  "title": "...",
  "description": "...",
  "suggested_agent": "Hermes|OpenCode|OpenClaw|Researcher",
  "priority": 1,
  "estimated_impact": "high|medium"
}}]"""

        try:
            response = query_llm(
                agent_name="hermes",
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=1024,
                temperature=0.3,
            )

            tasks = self._parse_llm_tasks(response, patterns)
            return tasks
        except Exception as e:
            logger.warning(f"LLM cross-cutting task generation failed: {e}")
            return []

    def _parse_llm_tasks(self, response: str,
                         patterns: List[InsightPattern]) -> List[GeneratedTask]:
        """Parse LLM-generated tasks from response."""
        tasks = []

        # Try to extract JSON array
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                items = json.loads(response[start:end])
                for i, item in enumerate(items):
                    if isinstance(item, dict) and "title" in item:
                        task_id = f"INSIGHT-CROSS-{i+1:03d}"
                        tasks.append(GeneratedTask(
                            task_id=task_id,
                            title=item["title"],
                            description=item.get("description", ""),
                            priority=item.get("priority", 2),
                            suggested_agent=item.get("suggested_agent", "Hermes"),
                            source_patterns=[p.pattern_id for p in patterns[:3]],
                            estimated_impact=item.get("estimated_impact", "medium"),
                            pow_file=f"scripts/{task_id.lower().replace('-', '_')}.py",
                        ))
        except (json.JSONDecodeError, ValueError):
            pass

        return tasks


class TaskInjector:
    """Injects generated tasks into unified_tasks.json."""

    def inject_tasks(self, tasks: List[GeneratedTask],
                     dry_run: bool = False) -> int:
        """Inject tasks into the pending queue."""
        if not UNIFIED_TASKS_FILE.exists():
            logger.error("unified_tasks.json not found")
            return 0

        with open(UNIFIED_TASKS_FILE) as f:
            data = json.load(f)

        pending = data.get("task_queue", {}).get("pending", [])
        existing_ids = {t.get("id") for t in pending}

        injected = 0
        for task in tasks:
            if task.task_id in existing_ids:
                continue

            new_entry = {
                "id": task.task_id,
                "task": task.description,
                "agent": task.suggested_agent,
                "priority": task.priority,
                "status": "pending",
                "pow_file": task.pow_file,
                "source": "verification_insights_pipeline",
                "generated_at": datetime.datetime.utcnow().isoformat(),
            }
            pending.append(new_entry)
            injected += 1

        if not dry_run and injected > 0:
            data["task_queue"]["pending"] = pending
            data["metadata"]["last_updated"] = datetime.datetime.utcnow().isoformat()
            with open(UNIFIED_TASKS_FILE, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Injected {injected} tasks into unified_tasks.json")
        else:
            logger.info(f"Would inject {injected} tasks (dry_run={dry_run})")

        return injected


class VerificationInsightsPipeline:
    """
    Main pipeline orchestrator that extracts insights from verification audits
    and generates actionable improvement tasks.

    Usage:
        pipeline = VerificationInsightsPipeline()
        report = pipeline.run()
    """

    def __init__(self, use_llm: bool = True, dry_run: bool = False):
        self.parser = AuditParser()
        self.pattern_extractor = PatternExtractor()
        self.synthesizer = InsightSynthesizer()
        self.injector = TaskInjector()
        self.use_llm = use_llm
        self.dry_run = dry_run

    def run(self) -> InsightReport:
        """Execute the full verification insights pipeline."""
        logger.info("Starting verification insights pipeline...")

        # Step 1: Parse audit reports
        findings = self.parser.parse_audit_directory(AUDIT_DIR)

        # Step 2: Extract patterns
        patterns = self.pattern_extractor.extract_patterns(findings)

        # Step 3: Synthesize insights and generate tasks
        tasks = self.synthesizer.synthesize_insights(patterns, self.use_llm)

        # Step 4: Inject tasks
        injected_count = self.injector.inject_tasks(tasks, self.dry_run)

        # Step 5: Generate report
        report = InsightReport(
            generated_at=datetime.datetime.utcnow().isoformat(),
            audits_analyzed=len(set(f.audit_id for f in findings)),
            findings_extracted=len(findings),
            patterns_identified=len(patterns),
            tasks_generated=len(tasks),
            top_patterns=[asdict(p) for p in patterns[:10]],
            generated_tasks=[asdict(t) for t in tasks],
            trend_summary=self._compute_trend_summary(patterns),
        )

        # Save report
        self._save_report(report)

        logger.info(
            f"Pipeline complete: {report.audits_analyzed} audits, "
            f"{report.findings_extracted} findings, "
            f"{report.patterns_identified} patterns, "
            f"{report.tasks_generated} tasks generated"
        )

        return report

    def _compute_trend_summary(self, patterns: List[InsightPattern]) -> Dict[str, Any]:
        """Compute overall trend summary across patterns."""
        category_counts = Counter(p.category for p in patterns)
        trend_counts = Counter(p.trend for p in patterns)
        total_frequency = sum(p.frequency for p in patterns)

        return {
            "total_patterns": len(patterns),
            "total_occurrences": total_frequency,
            "by_category": dict(category_counts),
            "by_trend": dict(trend_counts),
            "most_common_category": category_counts.most_common(1)[0][0] if category_counts else "none",
            "increasing_patterns": trend_counts.get("increasing", 0),
        }

    def _save_report(self, report: InsightReport) -> Path:
        """Save insight report to disk."""
        INSIGHTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = INSIGHTS_OUTPUT_DIR / f"insights_{report.generated_at[:10]}.json"

        with open(filepath, "w") as f:
            json.dump(asdict(report), f, indent=2, default=str)

        logger.info(f"Report saved to {filepath}")
        return filepath


def main():
    """Run the verification insights pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verification Insights Pipeline - Extract insights from audits"
    )
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM-powered synthesis")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't inject tasks into unified_tasks.json")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    pipeline = VerificationInsightsPipeline(
        use_llm=not args.no_llm,
        dry_run=args.dry_run,
    )
    report = pipeline.run()

    # Print summary
    print(f"\n{'='*60}")
    print(f"VERIFICATION INSIGHTS REPORT")
    print(f"{'='*60}")
    print(f"Generated: {report.generated_at}")
    print(f"Audits analyzed: {report.audits_analyzed}")
    print(f"Findings extracted: {report.findings_extracted}")
    print(f"Patterns identified: {report.patterns_identified}")
    print(f"Tasks generated: {report.tasks_generated}")

    if report.top_patterns:
        print(f"\nTop Patterns:")
        for p in report.top_patterns[:5]:
            print(f"  [{p['category']}] {p['description'][:50]} "
                  f"(freq: {p['frequency']}, trend: {p['trend']})")

    if report.trend_summary:
        print(f"\nTrend Summary:")
        print(f"  Categories: {report.trend_summary.get('by_category', {})}")
        print(f"  Increasing patterns: {report.trend_summary.get('increasing_patterns', 0)}")

    if report.generated_tasks:
        print(f"\nGenerated Tasks:")
        for t in report.generated_tasks[:5]:
            print(f"  [{t['priority']}] {t['title'][:60]} -> {t['suggested_agent']}")


if __name__ == "__main__":
    main()
