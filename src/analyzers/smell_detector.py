from typing import List, Dict, Any
import re


class QuerySmell:
    """Represents a detected performance issue in a SQL query."""
    
    def __init__(self, smell_type: str, severity: str, description: str, suggestion: str):
        self.smell_type = smell_type
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW
        self.description = description
        self.suggestion = suggestion
    
    def to_dict(self) -> Dict[str, str]:
        return {
            'type': self.smell_type,
            'severity': self.severity,
            'description': self.description,
            'suggestion': self.suggestion
        }


class SmellDetector:
    """Detects performance anti-patterns in SQL queries."""
    
    def __init__(self, query: str):
        self.query = query
        self.upper_query = query.upper()
        self.smells: List[QuerySmell] = []
    
    def detect_all(self) -> List[QuerySmell]:
        """Run all smell detection checks."""
        self.check_select_star()
        self.check_missing_where()
        self.check_cartesian_product()
        self.check_non_sargable()
        self.check_union_vs_union_all()
        self.check_leading_wildcards()
        self.check_or_in_where()
        self.check_not_in_subquery()
        self.check_repeated_table_access()

        return self.smells
    
    def check_select_star(self):
        """Detect SELECT * usage."""
        if re.search(r'\bSELECT\s+\*', self.upper_query):
            self.smells.append(QuerySmell(
                smell_type="SELECT_STAR",
                severity="MEDIUM",
                description="Query uses SELECT * instead of specific columns",
                suggestion="Specify only the columns you need. This reduces network traffic, memory usage, and prevents issues when table schema changes."
            ))
    
    def check_missing_where(self):
        """Detect SELECT queries without WHERE clause."""
        # Only check SELECT queries
        if self.upper_query.strip().startswith('SELECT'):
            # Make sure it's not a simple SELECT without FROM (like SELECT GETDATE())
            if 'FROM' in self.upper_query and 'WHERE' not in self.upper_query:
                self.smells.append(QuerySmell(
                    smell_type="MISSING_WHERE",
                    severity="HIGH",
                    description="SELECT query without WHERE clause - may return entire table",
                    suggestion="Add a WHERE clause to filter rows. Returning entire tables can cause performance issues and excessive memory usage."
                ))
    
    def check_cartesian_product(self):
        """Detect potential Cartesian products (JOINs without ON condition)."""
        # Count JOINs
        join_count = len(re.findall(r'\bJOIN\b', self.upper_query))
        
        # Count ON clauses
        on_count = len(re.findall(r'\bON\b', self.upper_query))
        
        # If we have JOINs but fewer ON clauses, potential Cartesian product
        if join_count > 0 and on_count < join_count:
            self.smells.append(QuerySmell(
                smell_type="CARTESIAN_PRODUCT",
                severity="CRITICAL",
                description=f"Found {join_count} JOIN(s) but only {on_count} ON clause(s) - potential Cartesian product",
                suggestion="Ensure every JOIN has a corresponding ON condition. Cartesian products multiply row counts and can crash your database."
            ))
    
    def check_non_sargable(self):
        """Detect non-SARGable predicates (functions on columns in WHERE)."""
        # Common non-SARGable patterns
        patterns = [
            (r'WHERE\s+\w+\([^)]*\w+\.\w+[^)]*\)', "Function applied to column in WHERE clause"),
            (r'WHERE.*YEAR\s*\(', "YEAR() function on date column"),
            (r'WHERE.*MONTH\s*\(', "MONTH() function on date column"),
            (r'WHERE.*DAY\s*\(', "DAY() function on date column"),
            (r'WHERE.*UPPER\s*\(', "UPPER() function on column"),
            (r'WHERE.*LOWER\s*\(', "LOWER() function on column"),
            (r'WHERE.*LTRIM\s*\(', "LTRIM() function on column"),
            (r'WHERE.*RTRIM\s*\(', "RTRIM() function on column"),
        ]
        
        for pattern, description in patterns:
            if re.search(pattern, self.upper_query):
                self.smells.append(QuerySmell(
                    smell_type="NON_SARGABLE",
                    severity="HIGH",
                    description=f"Non-SARGable predicate detected: {description}",
                    suggestion="Avoid functions on indexed columns in WHERE clause. Rewrite to allow index usage. Example: Instead of 'WHERE YEAR(date_col) = 2024', use 'WHERE date_col >= '2024-01-01' AND date_col < '2025-01-01''"
                ))
                break  # Only report once
    
    def check_union_vs_union_all(self):
        """Detect UNION when UNION ALL might be more appropriate."""
        if re.search(r'\bUNION\b(?!\s+ALL)', self.upper_query):
            self.smells.append(QuerySmell(
                smell_type="UNION_WITHOUT_ALL",
                severity="MEDIUM",
                description="Using UNION instead of UNION ALL",
                suggestion="If you don't need to remove duplicates, use UNION ALL instead of UNION. UNION ALL is faster because it doesn't perform duplicate elimination."
            ))
    
    def check_leading_wildcards(self):
        """Detect leading wildcards in LIKE clauses."""
        if re.search(r"LIKE\s+['\"]%", self.upper_query):
            self.smells.append(QuerySmell(
                smell_type="LEADING_WILDCARD",
                severity="HIGH",
                description="LIKE predicate with leading wildcard (LIKE '%...')",
                suggestion="Leading wildcards prevent index usage. If possible, avoid patterns like 'LIKE '%value'. Consider full-text search for better performance on text searches."
            ))
    
    def check_or_in_where(self):
        """Detect OR conditions in WHERE clause."""
        # Look for OR in WHERE clause (simplified check)
        where_match = re.search(r'WHERE.*', self.upper_query, re.DOTALL)
        if where_match:
            where_clause = where_match.group()
            if ' OR ' in where_clause:
                self.smells.append(QuerySmell(
                    smell_type="OR_IN_WHERE",
                    severity="MEDIUM",
                    description="OR condition in WHERE clause may prevent index usage",
                    suggestion="OR conditions can prevent optimal index usage. Consider rewriting with UNION ALL or using IN clause if appropriate. Example: 'WHERE col = 1 OR col = 2' -> 'WHERE col IN (1, 2)'"
                ))
    
    def check_not_in_subquery(self):
        """Detect NOT IN with subquery which can be slow."""
        if re.search(r'NOT\s+IN\s*\(', self.upper_query):
            # Check if it looks like a subquery (contains SELECT)
            not_in_match = re.search(r'NOT\s+IN\s*\([^)]*SELECT', self.upper_query)
            if not_in_match:
                self.smells.append(QuerySmell(
                    smell_type="NOT_IN_SUBQUERY",
                    severity="MEDIUM",
                    description="NOT IN with subquery can perform poorly",
                    suggestion="Consider using NOT EXISTS or LEFT JOIN with IS NULL instead. NOT EXISTS often performs better, especially with large subqueries."
                ))

    def check_repeated_table_access(self):
        """Detect when the same table is accessed multiple times."""
        # Extract table names using regex
        # Look for table names after FROM and JOIN
        table_pattern = r'\b(?:FROM|JOIN)\s+([#@]?\w+)'  # Added [#@]? to capture temp tables
        tables = re.findall(table_pattern, self.upper_query)
        
        # Filter out temp tables (start with # or @) and table variables
        permanent_tables = [table for table in tables if not table.startswith('#') and not table.startswith('@')]
        
        # Count occurrences of each permanent table
        table_counts = {}
        for table in permanent_tables:
            table_counts[table] = table_counts.get(table, 0) + 1
        
        # Find tables accessed more than once
        repeated_tables = {table: count for table, count in table_counts.items() if count > 1}
        
        if repeated_tables:
            table_list = ', '.join([f"{table} ({count}x)" for table, count in repeated_tables.items()])
            self.smells.append(QuerySmell(
                smell_type="REPEATED_TABLE_ACCESS",
                severity="MEDIUM",
                description=f"Permanent table(s) accessed multiple times: {table_list}",
                suggestion="Consider materializing the table data into a temp table with appropriate indexes. Reading the same permanent table multiple times causes redundant I/O. Create a temp table once, add necessary indexes, and query from it. Note: Repeated temp table access is fine - this only flags permanent tables."
            ))

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of detected smells by severity."""
        summary = {
            'total_smells': len(self.smells),
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'smells': [smell.to_dict() for smell in self.smells]
        }
        
        for smell in self.smells:
            if smell.severity == 'CRITICAL':
                summary['critical'] += 1
            elif smell.severity == 'HIGH':
                summary['high'] += 1
            elif smell.severity == 'MEDIUM':
                summary['medium'] += 1
            elif smell.severity == 'LOW':
                summary['low'] += 1
        
        return summary


# Test the detector
if __name__ == "__main__":
    print("="*70)
    print("SQL QUERY SMELL DETECTOR - TEST CASES")
    print("="*70)
    
    # Test Case 1: Multiple issues
    test_query1 = """
    SELECT * 
    FROM employees e
    JOIN departments d
    WHERE YEAR(e.hire_date) = 2024
    """
    
    print("\n📋 Test Query 1:")
    print(test_query1)
    detector1 = SmellDetector(test_query1)
    smells1 = detector1.detect_all()
    summary1 = detector1.get_summary()
    
    print(f"\n🔍 Found {summary1['total_smells']} issues:")
    print(f"   CRITICAL: {summary1['critical']}")
    print(f"   HIGH: {summary1['high']}")
    print(f"   MEDIUM: {summary1['medium']}")
    
    for i, smell in enumerate(smells1, 1):
        print(f"\n   Issue {i}: [{smell.severity}] {smell.smell_type}")
        print(f"   Description: {smell.description}")
        print(f"   Suggestion: {smell.suggestion}")
    
    # Test Case 2: Good query (should have no issues)
    print("\n" + "="*70)
    test_query2 = """
    SELECT 
        e.employee_id,
        e.first_name,
        e.last_name,
        d.department_name
    FROM employees e
    INNER JOIN departments d ON e.department_id = d.department_id
    WHERE e.salary > 50000
        AND e.hire_date >= '2024-01-01'
        AND e.hire_date < '2025-01-01'
    """
    
    print("\n📋 Test Query 2 (Should be clean):")
    print(test_query2)
    detector2 = SmellDetector(test_query2)
    smells2 = detector2.detect_all()
    summary2 = detector2.get_summary()
    
    print(f"\n🔍 Found {summary2['total_smells']} issues:")
    if summary2['total_smells'] == 0:
        print("   ✅ No performance issues detected! Good query!")
    
    # Test Case 3: Very bad query
    print("\n" + "="*70)
    test_query3 = """
    SELECT *
    FROM orders o
    JOIN customers c
    WHERE customer_name LIKE '%Smith%'
       OR customer_email LIKE '%gmail%'
    UNION
    SELECT * FROM archived_orders
    """
    
    print("\n📋 Test Query 3 (Problematic):")
    print(test_query3)
    detector3 = SmellDetector(test_query3)
    smells3 = detector3.detect_all()
    summary3 = detector3.get_summary()
    
    print(f"\n🔍 Found {summary3['total_smells']} issues:")
    print(f"   CRITICAL: {summary3['critical']}")
    print(f"   HIGH: {summary3['high']}")
    print(f"   MEDIUM: {summary3['medium']}")
    
    for i, smell in enumerate(smells3, 1):
        print(f"\n   Issue {i}: [{smell.severity}] {smell.smell_type}")
        print(f"   Description: {smell.description}")
        print(f"   Suggestion: {smell.suggestion}") 


# Test Case 4: NOT IN subquery
print("\n" + "="*70)
test_query4 = """
SELECT employee_id, first_name
FROM employees
WHERE department_id NOT IN (
    SELECT department_id 
    FROM departments 
    WHERE location = 'New York'
)
"""

print("\n📋 Test Query 4 (NOT IN with subquery):")
print(test_query4)
detector4 = SmellDetector(test_query4)
smells4 = detector4.detect_all()
summary4 = detector4.get_summary()

print(f"\n🔍 Found {summary4['total_smells']} issues:")
for i, smell in enumerate(smells4, 1):
    print(f"\n   Issue {i}: [{smell.severity}] {smell.smell_type}")
    print(f"   Description: {smell.description}")
    print(f"   Suggestion: {smell.suggestion}")

# Test Case 5: Repeated table access (your real-world scenario!)
print("\n" + "="*70)
test_query5 = """
SELECT 
    e1.employee_id,
    e1.first_name,
    e2.manager_name,
    e3.department_head
FROM employees e1
LEFT JOIN employees e2 ON e1.manager_id = e2.employee_id
LEFT JOIN employees e3 ON e1.department_id = e3.department_id
WHERE e1.status = 'Active'
"""

print("\n📋 Test Query 5 (Repeated table access - your scenario!):")
print(test_query5)
detector5 = SmellDetector(test_query5)
smells5 = detector5.detect_all()
summary5 = detector5.get_summary()

print(f"\n🔍 Found {summary5['total_smells']} issues:")
for i, smell in enumerate(smells5, 1):
    print(f"\n   Issue {i}: [{smell.severity}] {smell.smell_type}")
    print(f"   Description: {smell.description}")
    print(f"   Suggestion: {smell.suggestion}")

print("\n💡 This is the exact scenario you dealt with in your career!")
print("   The 'employees' table is accessed 3 times (e1, e2, e3).")
print("   Your solution: Create temp table once, add indexes, query from it!")


# Test Case 6: Temp table reuse (should NOT be flagged)
print("\n" + "="*70)
test_query6 = """
SELECT 
    a.employee_id,
    a.salary,
    b.avg_salary
FROM #TempEmployees a
JOIN #TempEmployees b ON a.department_id = b.department_id
WHERE a.salary > b.avg_salary
"""

print("\n📋 Test Query 6 (Temp table reuse - should be CLEAN):")
print(test_query6)
detector6 = SmellDetector(test_query6)
smells6 = detector6.detect_all()
summary6 = detector6.get_summary()

print(f"\n🔍 Found {summary6['total_smells']} issues:")
if summary6['total_smells'] == 0:
    print("   ✅ Correctly ignored temp table reuse!")
else:
    for i, smell in enumerate(smells6, 1):
        print(f"\n   Issue {i}: [{smell.severity}] {smell.smell_type}")
        print(f"   Description: {smell.description}")

# Test Case 7: Mixed - permanent table repeated, temp table reused (should flag only permanent)
print("\n" + "="*70)
test_query7 = """
SELECT 
    e.employee_id,
    t.processed_data
FROM employees e
JOIN #TempResults t ON e.id = t.employee_id
WHERE e.department_id IN (SELECT department_id FROM employees WHERE status = 'Active')
"""

print("\n📋 Test Query 7 (Mixed scenario):")
print(test_query7)
detector7 = SmellDetector(test_query7)
smells7 = detector7.detect_all()
summary7 = detector7.get_summary()

print(f"\n🔍 Found {summary7['total_smells']} issues:")
for i, smell in enumerate(smells7, 1):
    print(f"\n   Issue {i}: [{smell.severity}] {smell.smell_type}")
    print(f"   Description: {smell.description}")

print("\n💡 Should flag 'employees' (2x) but NOT '#TempResults' (1x)")