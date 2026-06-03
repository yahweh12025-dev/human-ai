# pi-cypher-tool

Essential if you use Graphify with Neo4j. It allows Pi to write the complex "Cypher" queries needed to pull data from your knowledge graph

## Description

This skill provides utilities to generate and manage Cypher queries for Neo4j databases, particularly useful when working with Graphify or other Neo4j-based knowledge graphs.

## Usage

Import and use the provided functions in your Pi workflows.

## Functions

- `build_match_query(nodes, relationships, filters)`: Builds a MATCH query with optional filters.
- `build_create_query(nodes, relationships)`: Builds a CREATE query for nodes and relationships.
- `build_return_clause(variables, aggregations)`: Builds a RETURN clause with variables and optional aggregations.
- `execute_query(driver, query, parameters=None)`: Executes a Cypher query using a Neo4j driver.

## Example

```python
from skills.pi_cypher_tool import build_match_query, build_return_clause

match_query = build_match_query(
    nodes=[("n", "Person")],
    relationships=[],
    filters={"n.age": {"$gt": 18}}
)
return_clause = build_return_clause(["n.name", "n.age"])
query = f"{match_query} RETURN {return_clause}"
```
