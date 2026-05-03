#!/usr/bin/env python3
"""
Human AI: Researcher Agent (v3.2)
Integrated with DeepSeek Browser Agent, OpenClaw Gateway, Supabase, and Graphify.
"""

import asyncio
import os
import re
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.async_api import async_playwright
from supabase import create_client, Client
import random
import traceback

# Local import for the browser agent
from .deepseek_browser_agent import DeepSeekBrowserAgent as ClaudeBrowserAgent

# Load environment variables
load_dotenv()

# Ensure essential directories exist
Path('/home/yahwehatwork/human-ai/outputs').mkdir(parents=True, exist_ok=True)
Path('/home/yahwehatwork/human-ai/logs').mkdir(parents=True, exist_ok=True)

class HumanAIResearcher:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(self.supabase_url, self.supabase_key) if self.supabase_url else None
        
        # Integration with Browser-First Routing (via DeepSeekBrowserAgent)
        self.browser_agent = None # Initialized on demand

    async def start_browser(self):
        if not self.browser_agent:
            # Initialize the real DeepSeekBrowserAgent
            self.browser_agent = ClaudeBrowserAgent()
            await self.browser_agent.start_browser()
            print("🌐 Browser Agent initialized.")
            
    async def call_llm_via_browser(self, prompt: str) -> str:
        # Route prompt to Claude Browser Agent (Botasaurus)
        print(f"🌐 Routing prompt to Claude Browser: {prompt[:50]}...")
        await self.start_browser()
        # Ensure login (uses cookies if available)
        # Since the Botasaurus agent's login is synchronous, we run it in a thread
        loop = asyncio.get_event_loop()
        logged_in = await loop.run_in_executor(None, self.browser_agent.login)
        if not logged_in:
            raise Exception("Claude session invalid. Please manually re-seed the session.")
        # Get the response from the LLM via the browser
        response = await loop.run_in_executor(None, self.browser_agent.prompt, prompt)
        return response

    async def research_with_notebooklm(self, topic: str, documents: List[Path], queries: List[str]) -> List[Dict[str, Any]]:
        """
        Research using NotebookLM for document-grounded insights.
        """
        if not hasattr(self, 'notebook_lm_agent') or not self.notebook_lm_agent:
            print("NotebookLMAgent not available, falling back to regular research")
            return await self.research(topic, queries)
        
        findings = []
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                context = await self.notebook_lm_agent.launch_browser(p)
                
                # Upload all documents
                for doc_path in documents:
                    if doc_path.exists():
                        print(f"Uploading document: {doc_path.name}")
                        await self.notebook_lm_agent.upload_document(context, doc_path)
                    else:
                        print(f"Warning: Document not found: {doc_path}")
                
                # Wait a bit for documents to process
                await asyncio.sleep(5)
                
                # Ask each query
                for query in queries:
                    print(f"Asking NotebookLM: {query}")
                    try:
                        response = await self.notebook_lm_agent.query_notebook(context, query)
                        findings.append({'topic': query, 'content': response, 'source': 'NotebookLM'})
                    except Exception as e:
                        print(f"Error querying NotebookLM: {e}")
                        findings.append({'topic': query, 'content': f"Error: {str(e)}", 'source': 'NotebookLM'})
                
                await context.close()
        except Exception as e:
            print(f"Error in NotebookLM research: {e}")
            # Fallback to regular research
            findings = await self.research(topic, queries)
        
        return findings

    async def research(self, topic: str, queries: List[str]) -> List[Dict[str, Any]]:
        findings = []
        await self.start_browser()
        for query in queries:
            print(f"🔍 Researching: {query}")
            result = await self.call_llm_via_browser(query)
            findings.append({'topic': query, 'content': result})
        return findings

    async def synthesize(self, topic: str, final_findings: List[Dict[str, Any]]) -> str:
        # 1. Textual Synthesis
        report = f"# Research Report: {topic}\n\n"
        for finding in final_findings:
            report += f"## {finding['topic']}\n{finding['content']}\n\n"
        
        # 2. Visualization Phase (Graphify)
        try:
            from skills.graphify_skill import GraphifySkill
            graphify = GraphifySkill()
            nodes = [{'id': f['topic'], 'label': f['topic']} for f in final_findings]
            edges = []
            # Simple logic to connect all findings to the main topic
            for node in nodes:
                edges.append({'source': topic, 'target': node['id'], 'label': 'explains'})
            
            graph_data = graphify.generate_graph(nodes, edges)
            report += f"\n\n## Visual Relationship Graph\n\n{graph_data['content']}"
        except Exception as e:
            print(f"Graphify integration failed: {e}")
            
        return report

        async def synthesize_advanced(self, topic: str, final_findings: List[Dict[str, Any]],                                     format_type: str = "narrative",                                     include_contradictions: bool = True,                                    confidence_scoring: bool = True) -> str:            """Advanced synthesis with multiple formats, contradiction handling, and confidence scoring"""            # 1. Basic textual synthesis (existing functionality)            basic_report = await self.synthesize(topic, final_findings)                    # 2. Apply enhancements based on parameters            if format_type == "narrative":                enhanced_report = await self.synthesize_narrative(topic, final_findings)            elif format_type == "comparative":                enhanced_report = await self.synthesize_comparative(topic, final_findings)            elif format_type == "argumentative":                enhanced_report = await self.synthesize_argumentative(topic, final_findings)            elif format_type == "multi_perspective":                enhanced_report = await self.synthesize_multi_perspective(topic, final_findings)            else:                # Default to basic synthesis with enhancements                enhanced_report = basic_report                        # 3. Add contradiction handling if requested            if include_contradictions:                contradictions = await self.detect_contradictions(final_findings)                if contradictions:                    resolved_report = await self.resolve_contradictions(topic, final_findings, contradictions)                    enhanced_report = resolved_report + "\n\n" + enhanced_report                    # 4. Add confidence scoring if requested            if confidence_scoring:                enhanced_report = await self.assign_confidence_scores(enhanced_report, final_findings)                        # 5. Add proper citations            enhanced_report = await self.format_with_citations(enhanced_report, final_findings)                    return enhanced_report        async def synthesize_narrative(self, topic: str, final_findings: List[Dict[str, Any]]) -> str:            """Create a narrative/story-driven synthesis"""            report = f"# Research Report: {topic}\n\n"            report += "## Executive Summary\n\n"            report += f"This research investigated {topic} through systematic analysis of {len(final_findings)} key findings. "            report += "The investigation revealed important insights about current trends, challenges, and future directions.\n\n"                    report += "## Research Journey\n\n"            report += "The investigation began with broad exploratory queries to understand the landscape, "            report += "followed by deep dives into specific aspects identified as particularly significant. "            report += "Each finding contributed to building a comprehensive understanding of the topic.\n\n"                    report += "## Key Insights\n\n"            for i, finding in enumerate(final_findings, 1):                report += f"{i}. **{finding['topic']}**: {finding['content']}\n\n"                    report += "## Synthesis and Implications\n\n"            report += "Taking a holistic view of the evidence, several patterns emerge. "            report += "The findings suggest that while progress is being made in certain areas, "            report += "significant challenges remain that require coordinated effort to address.\n\n"                    return report        async def synthesize_comparative(self, topic: str, final_findings: List[Dict[str, Any]],                                        comparison_aspects: List[str] = None) -> str:            """Create a side-by-side comparison synthesis"""            if comparison_aspects is None:                comparison_aspects = ["definition", "current_state", "challenges", "future_outlook"]                    report = f"# Research Report: {topic} - Comparative Analysis\n\n"                    # Create comparison table            report += "## Comparison Matrix\n\n"            report += "| Aspect | " + " | ".join(comparison_aspects) + " |\n"            report += "|--------|" + "|--------|" * len(comparison_aspects) + "\n"                    for finding in final_findings:                row = f"| {finding['topic']} |"                for aspect in comparison_aspects:                    # Extract relevant information for each aspect (simplified)                    content = finding['content'].lower()                    if aspect == "definition":                        value = "Defined as..." if "define" in content or "is a" in content else "See description"                    elif aspect == "current_state":                        value = "Currently..." if "current" in content or "now" in content else "Ongoing"                    elif aspect == "challenges":                        value = "Challenges noted" if "challenge" in content or "problem" in content or "difficult" in content else "Not specified"                    elif aspect == "future_outlook":                        value = "Future outlook" if "future" in content or "trend" in content or "will" in content else "To be determined"                    else:                        value = "See details"                    row += f" {value} |"                report += row + "\n"                    report += "\n"            report += "## Detailed Findings\n\n"            for finding in final_findings:                report += f"### {finding['topic']}\n{finding['content']}\n\n"                    return report        async def synthesize_argumentative(self, topic: str, final_findings: List[Dict[str, Any]]) -> str:            """Create a thesis-antithesis-synthesis argumentative format"""            report = f"# Research Report: {topic} - Argumentative Synthesis\n\n"                    report += "## Thesis (Position Supported by Evidence)\n\n"            report += "Based on the preponderance of evidence from multiple sources, "            report += "the available data supports the conclusion that "            report += f"{topic} represents a significant and developing area with meaningful implications.\n\n"                    report += "## Antithesis (Counterarguments and Limitations)\n\n"            report += "However, the research also reveals important limitations and counterpoints. "            report += "Some studies suggest that the current understanding may be incomplete, "            report += "and that alternative interpretations of the data are possible. "            report += "Additionally, practical implementation faces significant hurdles that "            report += "may affect the realized benefits.\n\n"                    report += "## Synthesis (Balanced Conclusion)\n\n"            report += "After considering both the supporting evidence and the limitations, "            report += "a balanced view emerges. While {topic} shows promise and has demonstrated "            report += "value in certain contexts, realizing its full potential requires "            report += "addressing the identified challenges through continued research, "            report += "technological advancement, and practical implementation efforts.\n\n"                    report += "## Evidence Summary\n\n"            for finding in final_findings:                report += f"- **{finding['topic']}**: {finding['content']}\n"                    return report        async def synthesize_multi_perspective(self, topic: str, final_findings: List[Dict[str, Any]]) -> str:            """Create synthesis from multiple analytical perspectives"""            report = f"# Research Report: {topic} - Multi-Perspective Analysis\n\n"                    perspectives = [                ("Historical", "How has this topic evolved over time?"),                ("Technical", "What are the technical aspects and mechanisms?"),                ("Practical", "What are the real-world applications and implementations?"),                ("Strategic", "What are the broader implications and strategic considerations?"),                ("Critical", "What are the limitations, criticisms, and open questions?")            ]                    for perspective_name, perspective_question in perspectives:                report += f"## {perspective} Perspective\n\n"                report += f"*{perspective_question}*\n\n"                            # Filter findings relevant to this perspective (simplified)                relevant_findings = []                for finding in final_findings:                    content_lower = finding['content'].lower()                    topic_lower = topic.lower()                    # Simple relevance check - in practice this would be more sophisticated                    if any(word in content_lower for word in topic_lower.split()) or                    any(word in content_lower for word in perspective_name.lower().split()):                        relevant_findings.append(finding)                            if not relevant_findings:                    relevant_findings = final_findings  # Fallback to all findings                            for finding in relevant_findings:                    report += f"- **{finding['topic']}**: {finding['content']}\n"                report += "\n"                    report += "## Integrated Perspective\n\n"            report += "Bringing together insights from all perspectives provides a more complete understanding. "            report += "The historical context informs technical development, which enables practical applications, "            report += "that have strategic implications requiring critical evaluation. "            report += "This holistic view is essential for informed decision-making and future planning.\n\n"                    return report        async def detect_contradictions(self, final_findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:            """Detect contradictory information in findings"""            contradictions = []                    # Simple contradiction detection based on opposing terms            contradiction_pairs = [                ("increase", "decrease"),                ("improve", "worsen"),                ("effective", "ineffective"),                ("benefit", "harm"),                ("yes", "no"),                ("true", "false"),                ("supported", "refuted"),                ("significant", "not significant"),                ("positive", "negative"),                ("gain", "loss"),                ("up", "down"),                ("high", "low"),                ("more", "less"),                ("always", "never"),                ("certain", "uncertain")            ]                    # Check each pair of findings for potential contradictions            for i, finding1 in enumerate(final_findings):                for j, finding2 in enumerate(final_findings[i+1:], i+1):                    content1 = finding1['content'].lower()                    content2 = finding2['content'].lower()                    topic1 = finding1['topic'].lower()                    topic2 = finding2['topic'].lower()                                    # Only check if findings are related (share common terms)                    if self._findings_related(topic1, topic2, content1, content2):                        for pos_term, neg_term in contradiction_pairs:                            if pos_term in content1 and neg_term in content2:                                contradictions.append({                                    'finding1': finding1,                                    'finding2': finding2,                                    'contradiction_type': f'{pos_term} vs {neg_term}',                                    'description': f"{finding1['topic']} suggests {pos_term} while {finding2['topic']} suggests {neg_term}"                                })                            elif neg_term in content1 and pos_term in content2:                                contradictions.append({                                    'finding1': finding1,                                    'finding2': finding2,                                    'contradiction_type': f'{neg_term} vs {pos_term}',                                    'description': f"{finding1['topic']} suggests {neg_term} while {finding2['topic']} suggests {pos_term}"                                })                    return contradictions        def _findings_related(self, topic1: str, topic2: str, content1: str, content2: str) -> bool:            """Check if two findings are related enough to potentially contradict each other"""            # Simple check: share common significant words (excluding common words)            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'it', 'he', 'she', 'they', 'we', 'you', 'i'}                    words1 = set(word.strip('.,!?;:()[]{}""') for word in content1.lower().split() if word not in common_words and len(word) > 2)            words2 = set(word.strip('.,!?;:()[]{}""') for word in content2.lower().split() if word not in common_words and len(word) > 2)                    # Check for overlap in significant words or topics            topic_words1 = set(word.strip('.,!?;:()[]{}""') for word in topic1.lower().split() if word not in common_words)            topic_words2 = set(word.strip('.,!?;:()[]{}""') for word in topic2.lower().split() if word not in common_words)                    return bool(words1 & words2) or bool(topic_words1 & topic_words2) or bool(words1 & topic_words2) or bool(words2 & topic_words1)        async def resolve_contradictions(self, topic: str, final_findings: List[Dict[str, Any]],                                        contradictions: List[Dict[str, Any]]) -> str:            """Resolve contradictions using evidence weighting"""            if not contradictions:                return ""                    report = "## Contradiction Resolution\n\n"            report += "During analysis, certain contradictory pieces of evidence were identified. "            report += "After evaluating the available evidence, the following resolutions were determined:\n\n"                    for i, contradiction in enumerate(contradictions, 1):                report += f"{i}. **{contradiction['description']}**\n"                report += f"   *Type*: {contradiction['contradiction_type']}\n"                # Simple resolution based on which finding has more substantial content or appears more definitive                finding1 = contradiction['finding1']                finding2 = contradiction['finding2']                            # Very simple heuristic: longer content might indicate more substantial evidence                if len(finding1['content']) > len(finding2['content']):                    report += f"   *Resolution*: Favoring evidence from {finding1['topic']} based on specificity and detail.\n\n"                elif len(finding2['content']) > len(finding1['content']):                    report += f"   *Resolution*: Favoring evidence from {finding2['topic']} based on specificity and detail.\n\n"                else:                    report += f"   *Resolution*: Evidence appears balanced; further investigation recommended.\n\n"                    return report        async def assign_confidence_scores(self, report: str, final_findings: List[Dict[str, Any]]) -> str:            """Assign confidence scores to synthesized claims"""            # This is a simplified implementation - in practice would be more sophisticated            report += "\n## Confidence Assessment\n\n"            report += "Based on the quality, quantity, and consistency of evidence:\n\n"                    # Analyze findings to determine overall confidence levels            high_confidence_items = []            medium_confidence_items = []            low_confidence_items = []                    for finding in final_findings:                content = finding['content'].lower()                # Simple heuristics for confidence                if any(word in content for word in ['study', 'research', 'data', 'evidence', 'shows', 'demonstrates']):                    if any(word in content for word in ['multiple', 'various', 'several', 'studies show', 'research indicates']):                        high_confidence_items.append(finding['topic'])                    else:                        medium_confidence_items.append(finding['topic'])                elif any(word in content for word in ['suggest', 'may', 'could', 'potentially', 'possible']):                    low_confidence_items.append(finding['topic'])                else:                    medium_confidence_items.append(finding['topic'])  # Default to medium                    if high_confidence_items:                report += f"**High Confidence**: {', '.join(high_confidence_items)}\n"                report += "Well-supported by multiple studies or strong empirical evidence.\n\n"                    if medium_confidence_items:                report += f"**Medium Confidence**: {', '.join(medium_confidence_items)}\n"                report += "Supported by evidence but may have limitations or require further validation.\n\n"                    if low_confidence_items:                report += f"**Low Confidence**: {', '.join(low_confidence_items)}\n"                report += "Preliminary or speculative; requires additional research to confirm.\n\n"                    return report        async def format_with_citations(self, report: str, final_findings: List[Dict[str, Any]]) -> str:            """Add proper citations and provenance tracking"""            # Add a references section            report += "\n## Sources & References\n\n"                    for i, finding in enumerate(final_findings, 1):                # In a real implementation, this would link to actual sources                report += f"[{i}] {finding['topic']}. Source: Research finding via {self.__class__.__name__}.\n"                    report += "\n---"            report += "\n*This report was generated using advanced synthesis techniques that integrate "            report += "multiple analytical perspectives, evaluate evidence quality, and provide "            report += "nuanced understanding of complex topics.\n"                    return report    async def run(self, topic: str):
        # Simple pipeline: Query -> Research -> Synthesize
        queries = [f"What are the latest trends in {topic}?", f"Key challenges in {topic}"]
        findings = await self.research(topic, queries)
        report = await self.synthesize(topic, findings)
        
        # Save to Supabase
        if self.supabase:
            self.supabase.table('research_findings').insert({'topic': topic, 'content': report}).execute()
            
        print(f"✅ Research complete for {topic}. Report generated.")
        return report

if __name__ == "__main__":
    import asyncio
    asyncio.run(HumanAIResearcher().run("Solid State Batteries"))
