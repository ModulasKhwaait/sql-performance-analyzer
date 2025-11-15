import os
from typing import List, Dict, Any
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from parsers.plan_parser import ExecutionPlanParser
from analyzers.plan_analyzer import PlanAnalyzer


class BatchPlanAnalyzer:
    """Analyzes multiple execution plans and provides comparative insights."""
    
    def __init__(self, plans_directory: str):
        self.plans_directory = plans_directory
        self.results: List[Dict[str, Any]] = []
    
    def analyze_directory(self) -> List[Dict[str, Any]]:
        """Analyze all .sqlplan and .xml files in the directory."""
        plan_files = []
        
        # Find all plan files
        for ext in ['*.xml', '*.sqlplan']:
            plan_files.extend(Path(self.plans_directory).glob(ext))
        
        if not plan_files:
            print(f"⚠️  No execution plan files found in {self.plans_directory}")
            return []
        
        print(f"📂 Found {len(plan_files)} execution plan(s) to analyze...\n")
        
        # Analyze each plan
        for plan_file in plan_files:
            result = self._analyze_single_plan(plan_file)
            if result:
                self.results.append(result)
        
        return self.results
    
    def _analyze_single_plan(self, plan_file: Path) -> Dict[str, Any]:
        """Analyze a single execution plan file."""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be']
            plan_xml = None
            
            for encoding in encodings:
                try:
                    with open(plan_file, 'r', encoding=encoding) as f:
                        plan_xml = f.read()
                    break
                except (UnicodeError, UnicodeDecodeError):
                    continue
            
            if plan_xml is None:
                print(f"❌ Could not read {plan_file.name} with any encoding")
                return None
            
            # Parse and analyze
            parser = ExecutionPlanParser(plan_xml)
            summary = parser.get_summary()
            
            analyzer = PlanAnalyzer(summary)
            analyzer.analyze_all()
            analysis = analyzer.get_analysis_summary()
            
            return {
                'filename': plan_file.name,
                'query_text': summary['query_text'][:100] + '...' if len(summary['query_text']) > 100 else summary['query_text'],
                'total_cost': summary['total_cost'],
                'estimated_rows': summary['estimated_rows'],
                'health_score': analysis['health_score'],
                'total_issues': analysis['total_issues'],
                'critical_issues': analysis['critical'],
                'high_issues': analysis['high'],
                'medium_issues': analysis['medium'],
                'issues': analysis['issues']
            }
            
        except Exception as e:
            print(f"❌ Error analyzing {plan_file.name}: {str(e)}")
            return None
    
    def get_ranked_by_severity(self) -> List[Dict[str, Any]]:
        """Get plans ranked by number of critical/high issues."""
        return sorted(
            self.results,
            key=lambda x: (x['critical_issues'] * 100 + x['high_issues'] * 10 + x['total_issues']),
            reverse=True
        )
    
    def get_ranked_by_cost(self) -> List[Dict[str, Any]]:
        """Get plans ranked by total cost."""
        return sorted(self.results, key=lambda x: x['total_cost'], reverse=True)
    
    def get_ranked_by_health(self) -> List[Dict[str, Any]]:
        """Get plans ranked by health score (worst first)."""
        return sorted(self.results, key=lambda x: x['health_score'])
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get overall statistics across all plans."""
        if not self.results:
            return {}
        
        total_issues = sum(r['total_issues'] for r in self.results)
        total_critical = sum(r['critical_issues'] for r in self.results)
        total_high = sum(r['high_issues'] for r in self.results)
        
        avg_health = sum(r['health_score'] for r in self.results) / len(self.results)
        avg_cost = sum(r['total_cost'] for r in self.results) / len(self.results)
        
        plans_with_issues = len([r for r in self.results if r['total_issues'] > 0])
        
        return {
            'total_plans_analyzed': len(self.results),
            'plans_with_issues': plans_with_issues,
            'plans_healthy': len(self.results) - plans_with_issues,
            'total_issues_found': total_issues,
            'total_critical': total_critical,
            'total_high': total_high,
            'average_health_score': avg_health,
            'average_cost': avg_cost
        }
    
    def print_summary_report(self):
        """Print a formatted summary report."""
        stats = self.get_summary_stats()
        
        print("="*70)
        print("BATCH EXECUTION PLAN ANALYSIS REPORT")
        print("="*70)
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Plans Analyzed: {stats['total_plans_analyzed']}")
        print(f"   Plans with Issues: {stats['plans_with_issues']}")
        print(f"   Healthy Plans: {stats['plans_healthy']}")
        print(f"   Average Health Score: {stats['average_health_score']:.1f}/100")
        print(f"   Average Cost: {stats['average_cost']:.6f}")
        
        print(f"\n🚨 Issues Summary:")
        print(f"   Total Issues: {stats['total_issues_found']}")
        print(f"   🔴 Critical: {stats['total_critical']}")
        print(f"   🟠 High: {stats['total_high']}")
        
        print("\n" + "="*70)
        print("TOP 5 MOST PROBLEMATIC QUERIES (by severity)")
        print("="*70)
        
        ranked = self.get_ranked_by_severity()[:5]
        for i, plan in enumerate(ranked, 1):
            print(f"\n#{i}. {plan['filename']}")
            print(f"   Health Score: {plan['health_score']}/100")
            print(f"   Issues: {plan['critical_issues']} critical, {plan['high_issues']} high, {plan['medium_issues']} medium")
            print(f"   Cost: {plan['total_cost']:.6f}")
            print(f"   Query: {plan['query_text']}")
        
        print("\n" + "="*70)
        print("TOP 5 MOST EXPENSIVE QUERIES (by cost)")
        print("="*70)
        
        ranked_cost = self.get_ranked_by_cost()[:5]
        for i, plan in enumerate(ranked_cost, 1):
            print(f"\n#{i}. {plan['filename']}")
            print(f"   Cost: {plan['total_cost']:.6f}")
            print(f"   Health Score: {plan['health_score']}/100")
            print(f"   Query: {plan['query_text']}")


# Test with the sample plan
if __name__ == "__main__":
    analyzer = BatchPlanAnalyzer('sample_plans')
    results = analyzer.analyze_directory()
    
    if results:
        analyzer.print_summary_report()
        
        print("\n" + "="*70)
        print("💡 TIP: Add more .xml or .sqlplan files to sample_plans/ to see")
        print("   comparative analysis across multiple queries!")
        print("="*70)
        # Show detailed issues for each problematic query
        print("\n" + "="*70)
        print("DETAILED ISSUES FOR EACH QUERY")
        print("="*70)
        
        for result in analyzer.get_ranked_by_severity():
            if result['total_issues'] > 0:
                print(f"\n📄 {result['filename']}")
                print(f"   Query: {result['query_text']}")
                print(f"   Health Score: {result['health_score']}/100")
                print(f"   Total Issues: {result['total_issues']}\n")
                
                for i, issue in enumerate(result['issues'], 1):
                    severity_emoji = {
                        'CRITICAL': '🔴',
                        'HIGH': '🟠',
                        'MEDIUM': '🟡',
                        'LOW': '🟢'
                    }
                    print(f"   {severity_emoji.get(issue['severity'], '⚪')} Issue #{i}: [{issue['severity']}] {issue['type']}")
                    print(f"      Description: {issue['description']}")
                    if issue.get('cost_impact', 0) > 0:
                        print(f"      Cost Impact: {issue['cost_impact']:.1f}%")
                    print(f"      Recommendation: {issue['recommendation'][:150]}...")  # Truncate long recommendations
                    print()
    else:
        print("\n❌ No plans could be analyzed.")
        # Show detailed issues for each problematic query
        print("\n" + "="*70)
        print("DETAILED ISSUES FOR EACH QUERY")
        print("="*70)
        
        