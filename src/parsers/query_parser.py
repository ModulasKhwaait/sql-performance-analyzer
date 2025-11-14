import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Function
from sqlparse.tokens import Keyword, DML
from typing import Dict, List, Any
import re


class QueryParser:
    """Parses SQL queries and extracts key components."""
    
    def __init__(self, query: str):
        self.query = query
        self.parsed = sqlparse.parse(query)[0]
    
    def get_query_type(self) -> str:
        """Returns the type of SQL query (SELECT, INSERT, UPDATE, etc.)."""
        return self.parsed.get_type()
    
    def get_tables(self) -> List[str]:
        """Extracts table names from the query."""
        tables = []
        
        # Remove comments and clean the query
        cleaned_query = sqlparse.format(self.query, strip_comments=True)
        
        # Look for FROM and JOIN keywords
        from_pattern = r'\bFROM\s+(\w+)'
        join_pattern = r'\bJOIN\s+(\w+)'
        
        from_matches = re.findall(from_pattern, cleaned_query, re.IGNORECASE)
        join_matches = re.findall(join_pattern, cleaned_query, re.IGNORECASE)
        
        tables.extend(from_matches)
        tables.extend(join_matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tables = []
        for table in tables:
            if table.lower() not in seen:
                seen.add(table.lower())
                unique_tables.append(table)
        
        return unique_tables
    
    def has_where_clause(self) -> bool:
        """Check if query has a WHERE clause."""
        return 'WHERE' in self.query.upper()
    
    def uses_select_star(self) -> bool:
        """Check if query uses SELECT *."""
        return 'SELECT *' in self.query.upper() or 'SELECT*' in self.query.upper().replace(' ', '')
    
    def count_joins(self) -> int:
        """Count the number of JOINs in the query."""
        # Use regex to match JOIN keywords with word boundaries
        # This prevents double-counting (e.g., INNER JOIN won't count as both INNER JOIN and JOIN)
        join_pattern = r'\b(?:INNER\s+JOIN|LEFT\s+(?:OUTER\s+)?JOIN|RIGHT\s+(?:OUTER\s+)?JOIN|FULL\s+(?:OUTER\s+)?JOIN|CROSS\s+JOIN|JOIN)\b'
        matches = re.findall(join_pattern, self.query, re.IGNORECASE)
        return len(matches)
    
    def get_summary(self) -> Dict[str, Any]:
        """Returns a summary of the query."""
        return {
            'query_type': self.get_query_type(),
            'tables': self.get_tables(),
            'table_count': len(self.get_tables()),
            'join_count': self.count_joins(),
            'has_where': self.has_where_clause(),
            'uses_select_star': self.uses_select_star(),
            'query_length': len(self.query)
        }


# Test the parser
if __name__ == "__main__":
    # Sample query for testing
    test_query = """
    SELECT * 
    FROM employees e
    JOIN departments d ON e.department_id = d.id
    """
    
    parser = QueryParser(test_query)
    print("Query Summary:")
    summary = parser.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*50)
    print("Testing with another query:")
    
    test_query2 = """
    SELECT e.name, e.salary, d.department_name
    FROM employees e
    INNER JOIN departments d ON e.dept_id = d.id
    LEFT JOIN locations l ON d.location_id = l.id
    WHERE e.salary > 50000
    """
    
    parser2 = QueryParser(test_query2)
    print("\nQuery Summary:")
    summary2 = parser2.get_summary()
    for key, value in summary2.items():
        print(f"  {key}: {value}")