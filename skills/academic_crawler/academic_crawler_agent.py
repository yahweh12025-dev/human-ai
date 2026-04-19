#!/usr/bin/env python3
"""
Academic-Crawler Agent
Fetches high-authority research data from arXiv (and optionally PubMed) to empower the swarm’s research phase.
"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiohttp
import urllib.parse

# Optional: For more advanced HTML parsing if needed in future
# from bs4 import BeautifulSoup

class AcademicCrawlerAgent:
    def __init__(self):
        self.arxiv_api_url = "http://export.arxiv.org/api/query"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_arxiv_papers(self, search_query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch recent papers from arXiv based on a search query.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        # URL encode the search query
        encoded_query = urllib.parse.quote_plus(search_query)
        url = f"{self.arxiv_api_url}?search_query=all:{encoded_query}&start=0&max_results={max_results}"
        
        print(f"🔍 Fetching from arXiv: {url}")
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    print(f"❌ arXiv API request failed with status: {response.status}")
                    return []
                
                xml_content = await response.text()
                return self._parse_arxiv_xml(xml_content)
        except Exception as e:
            print(f"❌ Error fetching from arXiv: {e}")
            return []

    def _parse_arxiv_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Parse the XML response from arXiv and extract paper details.
        """
        papers = []
        try:
            root = ET.fromstring(xml_content)
            
            # Define namespaces
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            # Find all entry elements
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                paper = self._parse_arxiv_entry(entry, namespaces)
                if paper:
                    papers.append(paper)
                    
        except ET.ParseError as e:
            print(f"❌ Error parsing arXiv XML: {e}")
        except Exception as e:
            print(f"❌ Unexpected error in XML parsing: {e}")
            
        return papers

    def _parse_arxiv_entry(self, entry: ET.Element, namespaces: dict) -> Optional[Dict[str, Any]]:
        """
        Extract details from a single arXiv entry element.
        """
        try:
            # Extract title
            title_elem = entry.find('atom:title', namespaces)
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else "No title"
            
            # Extract summary (abstract)
            summary_elem = entry.find('atom:summary', namespaces)
            summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else "No abstract available"
            
            # Extract authors
            authors = []
            author_elem = entry.find('atom:author', namespaces)
            if author_elem is not None:
                # There can be multiple authors
                for author in entry.findall('atom:author', namespaces):
                    name_elem = author.find('atom:name', namespaces)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text.strip())
            
            # Extract published date
            published_elem = entry.find('atom:published', namespaces)
            published = published_elem.text.strip() if published_elem is not None and published_elem.text else ""
            
            # Extract arXiv ID
            id_elem = entry.find('atom:id', namespaces)
            arxiv_id = ""
            if id_elem is not None and id_elem.text:
                # ID is usually like http://arxiv.org/abs/2301.00001v1
                id_text = id_elem.text.strip()
                if '/abs/' in id_text:
                    arxiv_id = id_text.split('/abs/')[-1].split('v')[0]  # Get base ID without version
                else:
                    arxiv_id = id_text
            
            # Extract PDF link
            pdf_link = ""
            # arXiv links are in the 'link' elements
            for link in entry.findall('atom:link', namespaces):
                if link.get('title') == 'pdf':
                    pdf_link = link.get('href', '')
                    break
            
            # If no explicit PDF link was found, construct it from the ID
            if not pdf_link and arxiv_id:
                pdf_link = f"http://arxiv.org/pdf/{arxiv_id}.pdf"
            
            return {
                'title': title,
                'summary': summary,
                'authors': authors,
                'published': published,
                'arxiv_id': arxiv_id,
                'pdf_link': pdf_link,
                'source': 'arXiv'
            }
        except Exception as e:
            print(f"❌ Error parsing arXiv entry: {e}")
            return None

    def format_papers_as_markdown(self, papers: List[Dict[str, Any]]) -> str:
        """
        Format a list of papers into a clean, readable Markdown summary.
        """
        if not papers:
            return "No papers found for the given query."
        
        markdown = "# arXiv Research Papers\n\n"
        
        for i, paper in enumerate(papers, 1):
            markdown += f"## {i}. {paper['title']}\n\n"
            
            if paper['authors']:
                markdown += f"**Authors:** {', '.join(paper['authors'])}\n\n"
            
            if paper['published']:
                # Try to format the date nicely
                try:
                    # arXiv date format is usually YYYY-MM-DDTHH:MM:SSZ
                    date_obj = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime("%B %d, %Y")
                    markdown += f"**Published:** {formatted_date}\n\n"
                except:
                    markdown += f"**Published:** {paper['published']}\n\n"
            
            if paper['summary']:
                # Truncate summary for readability in markdown list
                summary = paper['summary']
                if len(summary) > 500:
                    summary = summary[:500] + "..."
                markdown += f"**Abstract:** {summary}\n\n"
            
            if paper['arxiv_id']:
                markdown += f"**arXiv ID:** [{paper['arxiv_id']}](https://arxiv.org/abs/{paper['arxiv_id']})\n\n"
            
            if paper['pdf_link']:
                markdown += f"**PDF Link:** [{paper['pdf_link']}]({paper['pdf_link']})\n\n"
            
            markdown += "---\n\n"
        
        return markdown

    async def research(self, topic: str) -> str:
        """
        Main research method: fetch papers on a topic and return formatted markdown.
        This is the method the AntFarm Orchestrator or Researcher agent would call.
        """
        print(f"📚 Researching topic: {topic}")
        
        # Use the topic as the search query, but we can refine it
        # For now, a direct search on the topic is fine
        search_query = topic
        
        async with self:
            papers = await self.fetch_arxiv_papers(search_query, max_results=8)
            
            if not papers:
                return f"# Research on {topic}\n\nNo papers found on arXiv for the query: '{search_query}'"
            
            markdown_output = self.format_papers_as_markdown(papers)
            
            # Prepend a header with the topic
            full_report = f"# Research Report: {topic}\n\n{markdown_output}"
            
            return full_report

# Example usage for testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        async with AcademicCrawlerAgent() as agent:
            result = await agent.research("large language model reasoning")
            print(result)
    
    asyncio.run(test())