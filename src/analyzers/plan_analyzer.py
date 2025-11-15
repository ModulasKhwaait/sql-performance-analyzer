from typing import List, Dict, Any


class PlanIssue:
    """Represents a performance issue found in an execution plan."""
    
    def __init__(self, issue_type: str, severity: str, description: str, recommendation: str, cost_impact: float = 0.0):
        self.issue_type = issue_type
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW
        self.description = description
        self.recommendation = recommendation
        self.cost_impact = cost_impact
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.issue_type,
            'severity': self.severity,
            'description': self.description,
            'recommendation': self.recommendation,
            'cost_impact': self.cost_impact
        }


class PlanAnalyzer:
    """Analyzes execution plans and identifies performance issues."""
    
    def __init__(self, plan_summary: Dict[str, Any]):
        self.summary = plan_summary
        self.issues: List[PlanIssue] = []
    
    def analyze_all(self) -> List[PlanIssue]:
        """Run all performance checks."""
        self.check_table_scans()
        self.check_clustered_index_scans()
        self.check_key_lookups()
        self.check_missing_indexes()
        self.check_expensive_operators()
        self.check_high_row_estimates()
        
        return self.issues
    
    def check_table_scans(self):
        """Detect table scans (heap scans)."""
        scans = self.summary['scans_and_seeks']['table_scans']
        if scans > 0:
            self.issues.append(PlanIssue(
                issue_type="TABLE_SCAN",
                severity="CRITICAL",
                description=f"Query performs {scans} table scan(s) on heap table(s)",
                recommendation="Table scans read every row in the table. Consider: 1) Adding a clustered index to the table, 2) Adding a covering non-clustered index, 3) Adding a WHERE clause to filter rows."
            ))
    
    def check_clustered_index_scans(self):
        """Detect clustered index scans."""
        scans = self.summary['scans_and_seeks']['clustered_index_scans']
        if scans > 0:
            self.issues.append(PlanIssue(
                issue_type="CLUSTERED_INDEX_SCAN",
                severity="HIGH",
                description=f"Query performs {scans} clustered index scan(s)",
                recommendation="Clustered index scans read the entire table. This may be acceptable for small tables, but for large tables consider: 1) Adding a non-clustered index on filter columns, 2) Reviewing WHERE clause predicates, 3) Ensuring statistics are up to date."
            ))
    
    def check_key_lookups(self):
        """Detect key lookups (bookmark lookups)."""
        lookups = self.summary['scans_and_seeks']['key_lookups']
        if lookups > 0:
            self.issues.append(PlanIssue(
                issue_type="KEY_LOOKUP",
                severity="HIGH",
                description=f"Query performs {lookups} key lookup(s)",
                recommendation="Key lookups occur when a non-clustered index doesn't contain all required columns. Each lookup is an additional read operation. Consider: 1) Creating a covering index with INCLUDE columns, 2) Adding frequently queried columns to the existing index."
            ))
    
    def check_missing_indexes(self):
        """Analyze missing index recommendations."""
        missing_indexes = self.summary['missing_indexes']
        
        for mi in missing_indexes:
            impact = mi['impact']
            
            # Build index creation script
            index_name = f"IX_{mi['table']}"
            if mi['equality_columns']:
                index_name += f"_{'_'.join(mi['equality_columns'][:2])}"  # Use first 2 columns
            
            key_columns = mi['equality_columns'] + mi['inequality_columns']
            
            create_statement = f"CREATE NONCLUSTERED INDEX {index_name}\n"
            create_statement += f"ON {mi['schema']}.{mi['table']} ({', '.join(key_columns)})"
            
            if mi['included_columns']:
                create_statement += f"\nINCLUDE ({', '.join(mi['included_columns'])})"
            
            severity = "CRITICAL" if impact > 90 else "HIGH" if impact > 70 else "MEDIUM"
            
            self.issues.append(PlanIssue(
                issue_type="MISSING_INDEX",
                severity=severity,
                description=f"Missing index on {mi['schema']}.{mi['table']} with {impact:.1f}% impact",
                recommendation=f"SQL Server suggests creating an index. Estimated improvement: {impact:.1f}%\n\nSuggested index:\n{create_statement}\n\nNote: Review existing indexes first to avoid duplicates. Consider impact on INSERT/UPDATE/DELETE operations.",
                cost_impact=impact
            ))
    
    def check_expensive_operators(self):
        """Identify operators that consume significant resources."""
        most_expensive = self.summary.get('most_expensive_operator')
        total_cost = self.summary['total_cost']
        
        # Only flag if BOTH conditions are true:
        # 1. Operator consumes > 50% of query cost
        # 2. Total cost is significant (> 0.1)
        if most_expensive and most_expensive['cost_percentage'] > 50 and total_cost > 0.1:
            op_type = most_expensive['physical_op']
            cost_pct = most_expensive['cost_percentage']
            
            recommendations = {
                'Sort': 'Sorts are expensive. Consider: 1) Adding an index that matches the ORDER BY clause, 2) Removing unnecessary sorting, 3) Using TOP with an index.',
                'Hash Match': 'Hash joins can be expensive. Consider: 1) Reviewing JOIN conditions, 2) Updating statistics, 3) Adding indexes on JOIN columns.',
                'Nested Loops': 'Nested loops can be slow with large datasets. Consider: 1) Ensuring proper indexes exist, 2) Reviewing cardinality estimates, 3) Updating statistics.',
                'Clustered Index Scan': 'See clustered index scan recommendations above.',
                'Table Scan': 'See table scan recommendations above.'
            }
            
            recommendation = recommendations.get(op_type, f'This {op_type} operator consumes {cost_pct:.1f}% of query cost. Review the execution plan to understand why.')
            
            self.issues.append(PlanIssue(
                issue_type="EXPENSIVE_OPERATOR",
                severity="HIGH",
                description=f"{op_type} operator consumes {cost_pct:.1f}% of total query cost (total: {total_cost:.6f})",
                recommendation=recommendation,
                cost_impact=cost_pct
            ))
    
    def check_high_row_estimates(self):
        """Check for very high estimated row counts."""
        estimated_rows = self.summary['estimated_rows']
        
        if estimated_rows > 100000:
            severity = "HIGH" if estimated_rows > 1000000 else "MEDIUM"
            self.issues.append(PlanIssue(
                issue_type="HIGH_ROW_COUNT",
                severity=severity,
                description=f"Query estimates returning {estimated_rows:,} rows",
                recommendation="Returning large result sets can cause memory and network issues. Consider: 1) Adding more restrictive WHERE clauses, 2) Using pagination (OFFSET/FETCH or TOP), 3) Selecting only necessary columns instead of SELECT *, 4) Reviewing if all rows are actually needed."
            ))
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of all issues found."""
        summary = {
            'total_issues': len(self.issues),
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'issues': [issue.to_dict() for issue in self.issues]
        }
        
        for issue in self.issues:
            if issue.severity == 'CRITICAL':
                summary['critical'] += 1
            elif issue.severity == 'HIGH':
                summary['high'] += 1
            elif issue.severity == 'MEDIUM':
                summary['medium'] += 1
            elif issue.severity == 'LOW':
                summary['low'] += 1
        
        # Calculate overall health score
        total_possible = 100
        deductions = (summary['critical'] * 30 + 
                     summary['high'] * 20 + 
                     summary['medium'] * 10 + 
                     summary['low'] * 5)
        
        summary['health_score'] = max(0, total_possible - deductions)
        
        return summary


# Test the analyzer
if __name__ == "__main__":
    import sys
    sys.path.append('src')
    from parsers.plan_parser import ExecutionPlanParser
    
    # Try different encodings
    encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be']
    plan_xml = None
    
    for encoding in encodings:
        try:
            with open('sample_plans/good_query.xml', 'r', encoding=encoding) as f:
                plan_xml = f.read()
            break
        except (UnicodeError, UnicodeDecodeError):
            continue
    
    if plan_xml is None:
        print("❌ Could not read the XML file")
        exit(1)
    
    # Parse the plan
    parser = ExecutionPlanParser(plan_xml)
    summary = parser.get_summary()
    
    # Analyze for issues
    analyzer = PlanAnalyzer(summary)
    issues = analyzer.analyze_all()
    analysis = analyzer.get_analysis_summary()
    
    print("="*70)
    print("EXECUTION PLAN PERFORMANCE ANALYSIS")
    print("="*70)
    
    print(f"\n📝 Query: {summary['query_text']}")
    print(f"💰 Total Cost: {summary['total_cost']:.6f}")
    print(f"📊 Estimated Rows: {summary['estimated_rows']:,}")
    
    print(f"\n🏥 Health Score: {analysis['health_score']}/100")
    
    print(f"\n🔍 Issues Found: {analysis['total_issues']}")
    print(f"   🔴 CRITICAL: {analysis['critical']}")
    print(f"   🟠 HIGH: {analysis['high']}")
    print(f"   🟡 MEDIUM: {analysis['medium']}")
    print(f"   🟢 LOW: {analysis['low']}")
    
    if analysis['total_issues'] > 0:
        print("\n" + "="*70)
        print("DETAILED ISSUES & RECOMMENDATIONS")
        print("="*70)
        
        for i, issue in enumerate(issues, 1):
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }
            
            print(f"\n{severity_emoji.get(issue.severity, '⚪')} Issue #{i}: [{issue.severity}] {issue.issue_type}")
            print(f"   Description: {issue.description}")
            if issue.cost_impact > 0:
                print(f"   Cost Impact: {issue.cost_impact:.1f}%")
            print(f"   Recommendation:\n   {issue.recommendation.replace(chr(10), chr(10) + '   ')}")
    else:
        print("\n✅ No performance issues detected! This query looks good!")