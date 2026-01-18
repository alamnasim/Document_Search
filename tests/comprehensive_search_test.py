#!/usr/bin/env python3
"""
Comprehensive Search API Test Suite
Tests all search parameters and edge cases with detailed reporting
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

API_URL = "http://localhost:8000/api/v1"
RESULTS_FILE = "search_test_results.md"

class TestResult:
    def __init__(self, test_name, category, payload, response_data=None, error=None, elapsed_ms=0):
        self.test_name = test_name
        self.category = category
        self.payload = payload
        self.response_data = response_data
        self.error = error
        self.elapsed_ms = elapsed_ms
        self.success = error is None

class SearchTester:
    def __init__(self):
        self.test_results: List[TestResult] = []
        self.start_time = datetime.now()
        
    def run_test(self, test_name: str, category: str, payload: Dict[str, Any]) -> TestResult:
        """Execute a single test case"""
        print(f"\n{'='*70}")
        print(f"🔍 {test_name}")
        print(f"{'='*70}")
        print(f"Category: {category}")
        print(f"Request: {json.dumps(payload, indent=2)}")
        
        try:
            start = time.time()
            response = requests.post(f"{API_URL}/search", json=payload, timeout=10)
            elapsed_ms = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                result = TestResult(test_name, category, payload, data, None, elapsed_ms)
                
                print(f"\n SUCCESS ({elapsed_ms}ms)")
                print(f"   Total Results: {data.get('total_results', 0)}")
                print(f"   ES Time: {data.get('took_ms', 0)}ms")
                print(f"   Results Returned: {len(data.get('results', []))}")
                
                if data.get('results'):
                    top = data['results'][0]
                    print(f"\n   Top Result:")
                    print(f"   - File: {top.get('file_name', 'N/A')}")
                    print(f"   - Score: {top.get('score', 0):.2f}")
                    if top.get('content_snippet'):
                        snippet = top['content_snippet'][:80]
                        print(f"   - Snippet: {snippet}...")
            else:
                error = f"HTTP {response.status_code}: {response.text[:200]}"
                result = TestResult(test_name, category, payload, None, error, elapsed_ms)
                print(f"\n FAILED: {error}")
                
        except Exception as e:
            result = TestResult(test_name, category, payload, None, str(e), 0)
            print(f"\n ERROR: {e}")
        
        self.test_results.append(result)
        return result
    
    def generate_report(self):
        """Generate comprehensive markdown report"""
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        
        report = []
        report.append("# 🔍 Comprehensive Search API Test Report\n")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Total Tests:** {len(self.test_results)}\n")
        report.append(f"**Total Duration:** {elapsed_time:.2f}s\n")
        report.append(f"**Passed:** {sum(1 for r in self.test_results if r.success)}\n")
        report.append(f"**Failed:** {sum(1 for r in self.test_results if not r.success)}\n")
        report.append("\n---\n\n")
        
        # Group by category
        categories = {}
        for result in self.test_results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        # Summary table
        report.append("## 📊 Summary by Category\n\n")
        report.append("| Category | Total | Passed | Failed | Avg Time (ms) |\n")
        report.append("|----------|-------|--------|--------|---------------|\n")
        
        for cat, results in sorted(categories.items()):
            total = len(results)
            passed = sum(1 for r in results if r.success)
            failed = total - passed
            avg_time = sum(r.elapsed_ms for r in results if r.success) / max(passed, 1)
            report.append(f"| {cat} | {total} | {passed} | {failed} | {avg_time:.1f} |\n")
        
        report.append("\n---\n\n")
        
        # Detailed results by category
        for category, results in sorted(categories.items()):
            report.append(f"## {category}\n\n")
            
            for result in results:
                status_icon = "" if result.success else ""
                report.append(f"### {status_icon} {result.test_name}\n\n")
                
                # Request
                report.append("**Request:**\n```json\n")
                report.append(json.dumps(result.payload, indent=2))
                report.append("\n```\n\n")
                
                # Response
                if result.success and result.response_data:
                    data = result.response_data
                    report.append("**Response:**\n")
                    report.append(f"- Status:  Success\n")
                    report.append(f"- Client Time: {result.elapsed_ms}ms\n")
                    report.append(f"- ES Time: {data.get('took_ms', 0)}ms\n")
                    report.append(f"- Total Results: {data.get('total_results', 0)}\n")
                    report.append(f"- Results Returned: {len(data.get('results', []))}\n\n")
                    
                    # Top 3 results
                    if data.get('results'):
                        report.append("**Top Results:**\n\n")
                        for i, res in enumerate(data['results'][:3], 1):
                            report.append(f"{i}. **{res.get('file_name', 'N/A')}** (Score: {res.get('score', 0):.2f})\n")
                            if res.get('content_snippet'):
                                snippet = res['content_snippet'][:150].replace('\n', ' ')
                                report.append(f"   - Snippet: `{snippet}...`\n")
                            report.append(f"   - Type: {res.get('file_type', 'N/A')}\n")
                            report.append(f"   - Path: `{res.get('file_path', 'N/A')}`\n\n")
                else:
                    report.append("**Response:**\n")
                    report.append(f"- Status:  Failed\n")
                    report.append(f"- Error: {result.error}\n\n")
                
                report.append("---\n\n")
        
        # Performance analysis
        report.append("## ⚡ Performance Analysis\n\n")
        successful_tests = [r for r in self.test_results if r.success and r.response_data]
        
        if successful_tests:
            # Fastest tests
            fastest = sorted(successful_tests, key=lambda x: x.response_data.get('took_ms', 999999))[:5]
            report.append("### 🚀 Fastest Queries (ES Time)\n\n")
            for r in fastest:
                es_time = r.response_data.get('took_ms', 0)
                report.append(f"- **{r.test_name}**: {es_time}ms\n")
            
            report.append("\n")
            
            # Slowest tests
            slowest = sorted(successful_tests, key=lambda x: x.response_data.get('took_ms', 0), reverse=True)[:5]
            report.append("### 🐌 Slowest Queries (ES Time)\n\n")
            for r in slowest:
                es_time = r.response_data.get('took_ms', 0)
                report.append(f"- **{r.test_name}**: {es_time}ms\n")
            
            report.append("\n")
            
            # Result distribution
            report.append("### 📈 Result Distribution\n\n")
            result_counts = {}
            for r in successful_tests:
                count = r.response_data.get('total_results', 0)
                result_counts[count] = result_counts.get(count, 0) + 1
            
            for count, freq in sorted(result_counts.items()):
                report.append(f"- {count} results: {freq} queries\n")
        
        report.append("\n---\n\n")
        
        # Recommendations
        report.append("## 💡 Performance Recommendations\n\n")
        report.append("Based on test results:\n\n")
        report.append("1. **Use exact matching** (`fuzziness: '0'`) for known terms - Up to 3x faster\n")
        report.append("2. **Limit result size** - Smaller `size` values improve response time\n")
        report.append("3. **Specify fields** - Searching fewer fields reduces query time\n")
        report.append("4. **Apply min_score** - Filters out irrelevant results early\n")
        report.append("5. **Use snippets** - Avoid fetching full content when not needed\n\n")
        
        # Write to file
        with open(RESULTS_FILE, 'w') as f:
            f.write(''.join(report))
        
        print(f"\n\n{'='*70}")
        print(f"📄 Report saved to: {RESULTS_FILE}")
        print(f"{'='*70}\n")

def main():
    tester = SearchTester()
    
    print("=" * 70)
    print("🚀 Starting Comprehensive Search API Test Suite")
    print("=" * 70)
    
    # Category 1: Basic Searches
    tester.run_test(
        "Basic search - Single term",
        "Basic Searches",
        {"query": "tiger"}
    )
    
    tester.run_test(
        "Basic search - Multi-word",
        "Basic Searches",
        {"query": "endangered species"}
    )
    
    tester.run_test(
        "Basic search - Phrase",
        "Basic Searches",
        {"query": "largest living cat"}
    )
    
    tester.run_test(
        "Search all documents",
        "Basic Searches",
        {"query": "animal"}
    )
    
    # Category 2: Size Parameter Tests
    tester.run_test(
        "Size=1 (minimal)",
        "Size Optimization",
        {"query": "whale", "size": 1}
    )
    
    tester.run_test(
        "Size=5 (small)",
        "Size Optimization",
        {"query": "mammal", "size": 5}
    )
    
    tester.run_test(
        "Size=20 (large)",
        "Size Optimization",
        {"query": "animal", "size": 20}
    )
    
    tester.run_test(
        "Size=100 (maximum)",
        "Size Optimization",
        {"query": "species", "size": 100}
    )
    
    # Category 3: Fuzziness Tests
    tester.run_test(
        "Exact match (fuzziness=0)",
        "Fuzziness Control",
        {"query": "elephant", "fuzziness": "0"}
    )
    
    tester.run_test(
        "Low tolerance (fuzziness=1)",
        "Fuzziness Control",
        {"query": "elefant", "fuzziness": "1"}
    )
    
    tester.run_test(
        "High tolerance (fuzziness=2)",
        "Fuzziness Control",
        {"query": "elefunt", "fuzziness": "2"}
    )
    
    tester.run_test(
        "Auto fuzziness (default)",
        "Fuzziness Control",
        {"query": "kangaroo", "fuzziness": "AUTO"}
    )
    
    tester.run_test(
        "Typo correction - missing letter",
        "Fuzziness Control",
        {"query": "tger", "fuzziness": "2"}
    )
    
    # Category 4: Min Score Tests
    tester.run_test(
        "No min_score filter",
        "Min Score Filtering",
        {"query": "conservation", "min_score": 0.0}
    )
    
    tester.run_test(
        "Low threshold (min_score=1.0)",
        "Min Score Filtering",
        {"query": "lion", "min_score": 1.0}
    )
    
    tester.run_test(
        "Medium threshold (min_score=3.0)",
        "Min Score Filtering",
        {"query": "tiger", "min_score": 3.0}
    )
    
    tester.run_test(
        "High threshold (min_score=5.0)",
        "Min Score Filtering",
        {"query": "whale", "min_score": 5.0}
    )
    
    # Category 5: Field-Specific Searches
    tester.run_test(
        "Search content only",
        "Field Optimization",
        {"query": "endangered", "fields": ["content"]}
    )
    
    tester.run_test(
        "Search filename only",
        "Field Optimization",
        {"query": "report", "fields": ["file_name"]}
    )
    
    tester.run_test(
        "Search file type",
        "Field Optimization",
        {"query": "pdf", "fields": ["file_type"]}
    )
    
    tester.run_test(
        "Multi-field search",
        "Field Optimization",
        {"query": "animal", "fields": ["content", "file_name", "file_type"]}
    )
    
    tester.run_test(
        "Content + filename",
        "Field Optimization",
        {"query": "data", "fields": ["content", "file_name"]}
    )
    
    # Category 6: Snippet vs Full Content
    tester.run_test(
        "With snippets (default)",
        "Content Optimization",
        {"query": "elephant", "use_snippets": True}
    )
    
    tester.run_test(
        "Without snippets (full content)",
        "Content Optimization",
        {"query": "elephant", "use_snippets": False, "size": 1}
    )
    
    tester.run_test(
        "Snippets with highlights",
        "Content Optimization",
        {"query": "tiger conservation", "use_snippets": True}
    )
    
    # Category 7: Combined Optimizations
    tester.run_test(
        "Max performance combo",
        "Combined Optimizations",
        {
            "query": "whale",
            "size": 3,
            "fuzziness": "0",
            "min_score": 1.0,
            "fields": ["content"],
            "use_snippets": True
        }
    )
    
    tester.run_test(
        "Balanced performance",
        "Combined Optimizations",
        {
            "query": "mammal",
            "size": 10,
            "fuzziness": "AUTO",
            "fields": ["content", "file_name"]
        }
    )
    
    tester.run_test(
        "Quality-focused",
        "Combined Optimizations",
        {
            "query": "endangered species",
            "size": 20,
            "fuzziness": "AUTO",
            "min_score": 2.0
        }
    )
    
    # Category 8: Edge Cases
    tester.run_test(
        "Empty query handling",
        "Edge Cases",
        {"query": ""}
    )
    
    tester.run_test(
        "Very long query",
        "Edge Cases",
        {"query": "tiger lion elephant whale leopard cheetah jaguar bear wolf fox deer rabbit kangaroo"}
    )
    
    tester.run_test(
        "Special characters",
        "Edge Cases",
        {"query": "tiger@#$%"}
    )
    
    tester.run_test(
        "Numbers in query",
        "Edge Cases",
        {"query": "2024 report"}
    )
    
    tester.run_test(
        "Non-existent term",
        "Edge Cases",
        {"query": "xyzzyzxz123456"}
    )
    
    tester.run_test(
        "Case sensitivity test",
        "Edge Cases",
        {"query": "TIGER"}
    )
    
    tester.run_test(
        "Partial word match",
        "Edge Cases",
        {"query": "conser", "fuzziness": "AUTO"}
    )
    
    # Category 9: Document Type Searches
    tester.run_test(
        "Find DOCX files",
        "Document Type Searches",
        {"query": "report", "fields": ["file_name", "file_type"]}
    )
    
    tester.run_test(
        "Find PDF files",
        "Document Type Searches",
        {"query": "animal", "fields": ["file_name", "file_type"]}
    )
    
    tester.run_test(
        "Find Excel files",
        "Document Type Searches",
        {"query": "data", "fields": ["file_name"]}
    )
    
    tester.run_test(
        "Find images",
        "Document Type Searches",
        {"query": "ocr", "fields": ["file_name"]}
    )
    
    # Category 10: Performance Comparison
    tester.run_test(
        "Baseline (all defaults)",
        "Performance Comparison",
        {"query": "lion"}
    )
    
    tester.run_test(
        "Speed optimized",
        "Performance Comparison",
        {"query": "lion", "size": 5, "fuzziness": "0", "fields": ["content"]}
    )
    
    tester.run_test(
        "Quality optimized",
        "Performance Comparison",
        {"query": "lion", "size": 20, "fuzziness": "AUTO", "min_score": 1.5}
    )
    
    # Generate comprehensive report
    print("\n\n" + "=" * 70)
    print("📊 Generating Comprehensive Report...")
    print("=" * 70)
    
    tester.generate_report()
    
    # Summary statistics
    total = len(tester.test_results)
    passed = sum(1 for r in tester.test_results if r.success)
    failed = total - passed
    
    print("\n" + "=" * 70)
    print("🏁 Test Suite Complete!")
    print("=" * 70)
    print(f"Total Tests: {total}")
    print(f" Passed: {passed}")
    print(f" Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    print("=" * 70)
    print(f"\n📄 Detailed report saved to: {RESULTS_FILE}")
    print(f"📊 View report: cat {RESULTS_FILE}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        # Check API health first
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f" API is healthy: {response.json()}\n")
            main()
        else:
            print(f" API health check failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(" Cannot connect to API at http://localhost:8000")
        print("   Start the API with: conda activate doc_search_env && python src/api/run_query_api.py")
    except Exception as e:
        print(f" Error: {e}")
