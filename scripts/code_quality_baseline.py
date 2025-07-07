#!/usr/bin/env python3
"""Generate code quality baseline metrics for the HCI Paper Extractor project."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: list[str]) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, and return code."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def check_tool_installed(tool: str) -> bool:
    """Check if a tool is installed."""
    try:
        subprocess.run([tool, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_missing_tools() -> None:
    """Install missing analysis tools."""
    tools_to_install = []
    
    if not check_tool_installed("radon"):
        tools_to_install.append("radon")
    
    if not check_tool_installed("vulture"):
        tools_to_install.append("vulture") 
        
    if tools_to_install:
        print(f"Installing missing tools: {', '.join(tools_to_install)}")
        subprocess.run([sys.executable, "-m", "pip", "install"] + tools_to_install)


def analyze_complexity() -> dict:
    """Run complexity analysis using radon."""
    print("Running complexity analysis...")
    
    # Cyclomatic complexity
    stdout, _, _ = run_command(["radon", "cc", "src/", "-s", "-j"])
    cc_data = json.loads(stdout) if stdout else {}
    
    # Maintainability index
    stdout, _, _ = run_command(["radon", "mi", "src/", "-s", "-j"])
    mi_data = json.loads(stdout) if stdout else {}
    
    # Raw metrics (LOC, comments, etc.)
    stdout, _, _ = run_command(["radon", "raw", "src/", "-s", "-j"])
    raw_data = json.loads(stdout) if stdout else {}
    
    return {
        "cyclomatic_complexity": cc_data,
        "maintainability_index": mi_data,
        "raw_metrics": raw_data,
    }


def analyze_code_smells() -> dict:
    """Run code smell analysis using ruff."""
    print("Running code smell analysis...")
    
    # Get statistics
    stdout, _, _ = run_command(["python", "-m", "ruff", "check", "src/", "--statistics"])
    
    smell_stats = {}
    total_issues = 0
    
    for line in stdout.strip().split("\n"):
        if line.strip() and not line.startswith("warning:"):
            parts = line.split("\t")
            if len(parts) >= 2:
                count = int(parts[0])
                rule = parts[1].strip()
                smell_stats[rule] = count
                total_issues += count
    
    # Get top 10 files with most issues
    stdout, _, _ = run_command(["python", "-m", "ruff", "check", "src/", "--format", "json"])
    issues_by_file = {}
    
    if stdout:
        try:
            issues = json.loads(stdout)
            for issue in issues:
                filepath = issue.get("filename", "")
                if filepath not in issues_by_file:
                    issues_by_file[filepath] = 0
                issues_by_file[filepath] += 1
        except json.JSONDecodeError:
            pass
    
    top_files = sorted(issues_by_file.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "total_issues": total_issues,
        "issues_by_rule": smell_stats,
        "top_problematic_files": dict(top_files),
    }


def analyze_dead_code() -> dict:
    """Run dead code analysis using vulture."""
    print("Running dead code analysis...")
    
    try:
        stdout, stderr, returncode = run_command(["vulture", "src/", "--min-confidence", "80"])
        
        dead_code_items = []
        if stdout:
            for line in stdout.strip().split("\n"):
                if line.strip():
                    dead_code_items.append(line)
        
        return {
            "total_dead_code_items": len(dead_code_items),
            "samples": dead_code_items[:10],  # First 10 items
        }
    except Exception as e:
        print(f"  Warning: Dead code analysis failed: {e}")
        return {
            "total_dead_code_items": 0,
            "samples": [],
            "error": str(e)
        }


def analyze_security() -> dict:
    """Run security analysis using bandit."""
    print("Running security analysis...")
    
    # Use a temporary file to get clean JSON output from bandit
    import tempfile
    
    try:
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
            temp_path = tmp_file.name
            
        # Run bandit with output to file to avoid progress bar mixing with JSON
        result = subprocess.run(
            ["bandit", "-r", "src/", "-f", "json", "-o", temp_path],
            capture_output=True,
            text=True
        )
        
        # Read the JSON file
        with open(temp_path, 'r') as f:
            security_data = json.load(f)
            
        # Clean up temp file
        Path(temp_path).unlink()
        
        results = security_data.get("results", [])
        metrics = security_data.get("metrics", {}).get("_totals", {})
        
        # Calculate total issues from metrics if results is empty
        total_issues = len(results)
        if total_issues == 0 and metrics:
            # Count issues from severity metrics
            total_issues = (
                metrics.get("SEVERITY.HIGH", 0) +
                metrics.get("SEVERITY.MEDIUM", 0) + 
                metrics.get("SEVERITY.LOW", 0)
            )
        
        return {
            "total_issues": total_issues,
            "by_severity": metrics,
            "top_issues": [
                {
                    "severity": r.get("issue_severity", "unknown"),
                    "confidence": r.get("issue_confidence", "unknown"),
                    "text": r.get("issue_text", "")[:100] + "..." if len(r.get("issue_text", "")) > 100 else r.get("issue_text", ""),
                    "filename": r.get("filename", ""),
                }
                for r in results[:5]
            ],
        }
    except FileNotFoundError:
        print("  Warning: bandit not found")
        return {
            "total_issues": 0,
            "by_severity": {},
            "top_issues": [],
            "error": "bandit not installed"
        }
    except json.JSONDecodeError as e:
        print(f"  Warning: Failed to parse bandit JSON: {e}")
        return {
            "total_issues": 0,
            "by_severity": {},
            "top_issues": [],
            "error": f"JSON parse error: {str(e)}"
        }
    except Exception as e:
        print(f"  Warning: Security analysis failed: {e}")
        return {
            "total_issues": 0,
            "by_severity": {},
            "top_issues": [],
            "error": str(e)
        }


def get_file_statistics() -> dict:
    """Get basic file statistics."""
    print("Collecting file statistics...")
    
    src_path = Path("src")
    
    py_files = list(src_path.rglob("*.py"))
    file_sizes = [(f, f.stat().st_size) for f in py_files]
    file_lines = []
    
    for f in py_files:
        with open(f, "r", encoding="utf-8") as file:
            lines = len(file.readlines())
            file_lines.append((f, lines))
    
    # Sort by lines of code
    file_lines.sort(key=lambda x: x[1], reverse=True)
    
    return {
        "total_python_files": len(py_files),
        "total_lines_of_code": sum(lines for _, lines in file_lines),
        "average_file_size": sum(size for _, size in file_sizes) // len(file_sizes) if file_sizes else 0,
        "largest_files": [
            {"file": str(f.relative_to("src")), "lines": lines}
            for f, lines in file_lines[:10]
        ],
    }


def generate_baseline_report() -> dict:
    """Generate comprehensive baseline report."""
    print("Generating code quality baseline report...")
    
    install_missing_tools()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "project": "HCI Paper Extractor",
        "file_statistics": get_file_statistics(),
        "code_smells": analyze_code_smells(),
        "complexity": analyze_complexity(),
        "dead_code": analyze_dead_code(),
        "security": analyze_security(),
    }
    
    return report


def main():
    """Main entry point."""
    report = generate_baseline_report()
    
    # Save JSON report
    output_path = Path("code_quality_baseline.json")
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ Baseline report saved to: {output_path}")
    
    # Print summary
    print("\n📊 Code Quality Summary:")
    print(f"  Total Python files: {report['file_statistics']['total_python_files']}")
    print(f"  Total lines of code: {report['file_statistics']['total_lines_of_code']:,}")
    print(f"  Total code smell issues: {report['code_smells']['total_issues']}")
    print(f"  Security issues: {report['security'].get('total_issues', 0)}")
    print(f"  Dead code items: {report['dead_code'].get('total_dead_code_items', 0)}")
    
    # Show errors if any
    if 'error' in report['security']:
        print(f"  Security analysis error: {report['security']['error']}")
    if 'error' in report['dead_code']:
        print(f"  Dead code analysis error: {report['dead_code']['error']}")
    
    print("\n🔝 Top 5 largest files:")
    for item in report['file_statistics']['largest_files'][:5]:
        print(f"  - {item['file']}: {item['lines']:,} lines")
    
    print("\n⚠️  Top 5 code smell types:")
    sorted_smells = sorted(
        report['code_smells']['issues_by_rule'].items(),
        key=lambda x: x[1],
        reverse=True
    )
    for rule, count in sorted_smells[:5]:
        print(f"  - {rule}: {count} occurrences")


if __name__ == "__main__":
    main()