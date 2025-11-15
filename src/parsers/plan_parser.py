import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional


class ExecutionPlanParser:
    """Parses SQL Server execution plans (XML format)."""
    
    # XML namespaces used in execution plans
    NAMESPACES = {
        'sp': 'http://schemas.microsoft.com/sqlserver/2004/07/showplan'
    }
    
    def __init__(self, plan_xml: str):
        """Initialize with execution plan XML string."""
        self.plan_xml = plan_xml
        self.root = ET.fromstring(plan_xml)
    
    def get_query_text(self) -> str:
        """Extract the SQL query text from the plan."""
        stmt = self.root.find('.//sp:StmtSimple', self.NAMESPACES)
        if stmt is not None:
            return stmt.get('StatementText', 'Query text not found')
        return 'Query text not found'
    
    def get_total_cost(self) -> float:
        """Get the total estimated cost of the query."""
        stmt = self.root.find('.//sp:StmtSimple', self.NAMESPACES)
        if stmt is not None:
            cost = stmt.get('StatementSubTreeCost')
            return float(cost) if cost else 0.0
        return 0.0
    
    def get_estimated_rows(self) -> int:
        """Get estimated number of rows returned."""
        stmt = self.root.find('.//sp:StmtSimple', self.NAMESPACES)
        if stmt is not None:
            rows = stmt.get('StatementEstRows')
            return int(float(rows)) if rows else 0
        return 0
    
    def get_operators(self) -> List[Dict[str, Any]]:
        """Extract all operators from the execution plan."""
        operators = []
        
        for relop in self.root.findall('.//sp:RelOp', self.NAMESPACES):
            operator = {
                'physical_op': relop.get('PhysicalOp', 'Unknown'),
                'logical_op': relop.get('LogicalOp', 'Unknown'),
                'estimated_rows': float(relop.get('EstimateRows', 0)),
                'estimated_cpu': float(relop.get('EstimateCPU', 0)),
                'estimated_io': float(relop.get('EstimateIO', 0)),
                'estimated_subtree_cost': float(relop.get('EstimatedTotalSubtreeCost', 0)),
                'node_id': relop.get('NodeId', 'Unknown')
            }
            
            # Calculate percentage of total cost
            total_cost = self.get_total_cost()
            if total_cost > 0:
                operator['cost_percentage'] = (operator['estimated_subtree_cost'] / total_cost) * 100
            else:
                operator['cost_percentage'] = 0
            
            operators.append(operator)
        
        return operators
    
    def get_missing_indexes(self) -> List[Dict[str, Any]]:
        """Extract missing index recommendations."""
        missing_indexes = []
        
        for missing_index_group in self.root.findall('.//sp:MissingIndexGroup', self.NAMESPACES):
            impact = float(missing_index_group.get('Impact', 0))
            
            for missing_index in missing_index_group.findall('.//sp:MissingIndex', self.NAMESPACES):
                index_info = {
                    'impact': impact,
                    'database': missing_index.get('Database', '').strip('[]'),
                    'schema': missing_index.get('Schema', '').strip('[]'),
                    'table': missing_index.get('Table', '').strip('[]'),
                    'equality_columns': [],
                    'inequality_columns': [],
                    'included_columns': []
                }
                
                # Extract column groups
                for col_group in missing_index.findall('.//sp:ColumnGroup', self.NAMESPACES):
                    usage = col_group.get('Usage', '')
                    columns = [col.get('Name', '').strip('[]') 
                              for col in col_group.findall('.//sp:Column', self.NAMESPACES)]
                    
                    if usage == 'EQUALITY':
                        index_info['equality_columns'] = columns
                    elif usage == 'INEQUALITY':
                        index_info['inequality_columns'] = columns
                    elif usage == 'INCLUDE':
                        index_info['included_columns'] = columns
                
                missing_indexes.append(index_info)
        
        return missing_indexes
    
    def get_scans_and_seeks(self) -> Dict[str, int]:
        """Count table scans vs index seeks."""
        counts = {
            'table_scans': 0,
            'clustered_index_scans': 0,
            'index_scans': 0,
            'index_seeks': 0,
            'key_lookups': 0
        }
        
        operators = self.get_operators()
        for op in operators:
            physical_op = op['physical_op']
            if 'Table Scan' in physical_op:
                counts['table_scans'] += 1
            elif 'Clustered Index Scan' in physical_op:
                counts['clustered_index_scans'] += 1
            elif 'Index Scan' in physical_op:
                counts['index_scans'] += 1
            elif 'Index Seek' in physical_op:
                counts['index_seeks'] += 1
            elif 'Key Lookup' in physical_op or 'RID Lookup' in physical_op:
                counts['key_lookups'] += 1
        
        return counts
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the execution plan."""
        operators = self.get_operators()
        missing_indexes = self.get_missing_indexes()
        scans_seeks = self.get_scans_and_seeks()
        
        # Find most expensive operator
        most_expensive = max(operators, key=lambda x: x['estimated_subtree_cost']) if operators else None
        
        return {
            'query_text': self.get_query_text(),
            'total_cost': self.get_total_cost(),
            'estimated_rows': self.get_estimated_rows(),
            'operator_count': len(operators),
            'most_expensive_operator': most_expensive,
            'scans_and_seeks': scans_seeks,
            'missing_indexes': missing_indexes,
            'has_performance_issues': (
                scans_seeks['table_scans'] > 0 or
                scans_seeks['clustered_index_scans'] > 0 or
                scans_seeks['key_lookups'] > 0 or
                len(missing_indexes) > 0
            )
        }


# Test the parser
if __name__ == "__main__":
    # Try different encodings
    encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be']
    plan_xml = None
    
    for encoding in encodings:
        try:
            with open('sample_plans/sample_plan.xml', 'r', encoding=encoding) as f:
                plan_xml = f.read()
            print(f"✅ Successfully read file with {encoding} encoding")
            break
        except (UnicodeError, UnicodeDecodeError):
            continue
    
    if plan_xml is None:
        print("❌ Could not read the XML file with any encoding")
        exit(1)
    
    parser = ExecutionPlanParser(plan_xml)
    summary = parser.get_summary()
    
    print("="*70)
    print("EXECUTION PLAN ANALYSIS")
    print("="*70)
    

    
    print(f"\n📝 Query: {summary['query_text']}")
    print(f"\n💰 Total Cost: {summary['total_cost']:.6f}")
    print(f"📊 Estimated Rows: {summary['estimated_rows']}")
    print(f"🔧 Operators: {summary['operator_count']}")
    
    print("\n🔍 Scans vs Seeks:")
    for key, value in summary['scans_and_seeks'].items():
        if value > 0:
            print(f"   {key.replace('_', ' ').title()}: {value}")
    
    if summary['most_expensive_operator']:
        op = summary['most_expensive_operator']
        print(f"\n💸 Most Expensive Operator:")
        print(f"   Type: {op['physical_op']}")
        print(f"   Cost: {op['estimated_subtree_cost']:.6f} ({op['cost_percentage']:.1f}% of total)")
        print(f"   Estimated Rows: {op['estimated_rows']:.0f}")
    
    if summary['missing_indexes']:
        print(f"\n⚠️  Missing Indexes Found: {len(summary['missing_indexes'])}")
        for idx, mi in enumerate(summary['missing_indexes'], 1):
            print(f"\n   Index #{idx} - Impact: {mi['impact']:.1f}%")
            print(f"   Table: {mi['database']}.{mi['schema']}.{mi['table']}")
            if mi['equality_columns']:
                print(f"   Equality Columns: {', '.join(mi['equality_columns'])}")
            if mi['included_columns']:
                print(f"   Included Columns: {', '.join(mi['included_columns'])}")
    
    print(f"\n{'🚨' if summary['has_performance_issues'] else '✅'} Performance Issues: {'YES' if summary['has_performance_issues'] else 'NO'}")