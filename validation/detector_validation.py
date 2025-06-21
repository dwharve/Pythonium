#!/usr/bin/env python3
"""
Detector Performance Validation Script

This script runs all detectors against their validation files to:
1. Measure performance and identify bottlenecks
2. Validate true positive and false positive rates
3. Test edge cases and boundary conditions
4. Generate reports for algorithm tuning

By default, this script disables caching, parallel execution, incremental analysis,
suppression, deduplication, and filtering to ensure clean, reproducible validation
results that reflect the true performance and accuracy of each detector.

Usage:
    python detector_validation.py [--detector DETECTOR_NAME] [--verbose] [--enable-cache]
"""

import argparse
import time
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pythonium.analyzer import Analyzer
from pythonium.detectors.stub_implementation import StubImplementationDetector


def validate_detector(detector_name: str, validation_dir: Path, verbose: bool = False, 
                     enable_cache: bool = False, enable_optimizations: bool = False) -> Dict[str, Any]:
    """
    Validate a single detector against its validation files.
    
    Args:
        detector_name: Name of the detector to validate
        validation_dir: Directory containing validation files
        verbose: Whether to print detailed output
        enable_cache: Whether to enable caching (disabled by default for clean validation)
        enable_optimizations: Whether to enable all performance optimizations
        
    Returns:
        Dictionary containing validation results
    """
    results = {
        'detector': detector_name,
        'files_tested': 0,
        'directories_tested': 0,
        'total_issues': 0,
        'performance': {},
        'file_results': {},
        'directory_results': {},
        'summary': {}
    }
    
    if not validation_dir.exists():
        if verbose:
            print(f"WARNING: No validation directory found for {detector_name}")
        return results
    
    # Find all Python files in the validation directory
    python_files = list(validation_dir.glob("*.py"))
    
    # Find all subdirectories (for multi-file scenarios)
    subdirectories = [d for d in validation_dir.iterdir() if d.is_dir()]
    
    if not python_files and not subdirectories:
        if verbose:
            print(f"WARNING: No Python files or subdirectories found in {validation_dir}")
        return results
    
    # Create analyzer with only this detector
    use_cache = enable_cache
    use_parallel = enable_optimizations
    use_incremental = enable_optimizations
    enable_suppression = enable_optimizations
    enable_deduplication = enable_optimizations
    enable_filtering = enable_optimizations
    
    analyzer = Analyzer(
        str(validation_dir.parent.parent),
        use_cache=use_cache,
        use_parallel=use_parallel,
        use_incremental=use_incremental,
        enable_suppression=enable_suppression,
        enable_deduplication=enable_deduplication,
        enable_filtering=enable_filtering
    )
    
    # Get the detector instance
    if detector_name in analyzer.detectors:
        detector = analyzer.detectors[detector_name]
        # Clear other detectors to test only this one
        analyzer.detectors = {detector_name: detector}
    else:
        if verbose:
            print(f"ERROR: Detector {detector_name} not found")
        return results
    
    total_start_time = time.time()
    
    # Analyze individual files (legacy support)
    for py_file in python_files:
        file_start_time = time.time()
        
        try:
            # Analyze single file
            issues = analyzer.analyze([str(py_file)])
            
            file_end_time = time.time()
            file_duration = file_end_time - file_start_time
            
            # Filter issues for this detector only
            detector_issues = [i for i in issues if i.detector_id == detector_name]
            
            results['file_results'][py_file.name] = {
                'issues_found': len(detector_issues),
                'analysis_time': file_duration,
                'file_size': py_file.stat().st_size,
                'issues': [
                    {
                        'id': issue.id,
                        'severity': issue.severity,
                        'message': issue.message,
                        'line': issue.location.line if issue.location else None
                    }
                    for issue in detector_issues
                ]
            }
            
            results['total_issues'] += len(detector_issues)
            results['files_tested'] += 1
            
            if verbose:
                print(f"  FILE: {py_file.name}: {len(detector_issues)} issues ({file_duration:.3f}s)")
                if detector_issues:
                    for issue in detector_issues[:3]:  # Show first 3 issues
                        print(f"    - {issue.severity}: {issue.message}")
                    if len(detector_issues) > 3:
                        print(f"    ... and {len(detector_issues) - 3} more")
        
        except Exception as e:
            if verbose:
                print(f"  ERROR: Error analyzing {py_file.name}: {e}")
            
            results['file_results'][py_file.name] = {
                'error': str(e),
                'analysis_time': 0,
                'issues_found': 0
            }
    
    # Analyze subdirectories (multi-file scenarios)
    for subdir in subdirectories:
        dir_start_time = time.time()
        
        try:
            # Find all Python files in subdirectory
            subdir_files = list(subdir.rglob("*.py"))
            
            if not subdir_files:
                continue
                
            # Analyze entire subdirectory
            issues = analyzer.analyze([str(f) for f in subdir_files])
            
            dir_end_time = time.time()
            dir_duration = dir_end_time - dir_start_time
            
            # Filter issues for this detector only
            detector_issues = [i for i in issues if i.detector_id == detector_name]
            
            results['directory_results'][subdir.name] = {
                'issues_found': len(detector_issues),
                'analysis_time': dir_duration,
                'files_in_directory': len(subdir_files),
                'total_size': sum(f.stat().st_size for f in subdir_files),
                'issues': [
                    {
                        'id': issue.id,
                        'severity': issue.severity,
                        'message': issue.message,
                        'file': issue.location.file if issue.location else None,
                        'line': issue.location.line if issue.location else None
                    }
                    for issue in detector_issues
                ]
            }
            
            results['total_issues'] += len(detector_issues)
            results['directories_tested'] += 1
            
            if verbose:
                print(f"  DIR: {subdir.name}: {len(detector_issues)} issues in {len(subdir_files)} files ({dir_duration:.3f}s)")
                if detector_issues:
                    for issue in detector_issues[:3]:  # Show first 3 issues
                        file_part = f" in {Path(issue.location.file).name}" if issue.location and issue.location.file else ""
                        print(f"    - {issue.severity}: {issue.message}{file_part}")
                    if len(detector_issues) > 3:
                        print(f"    ... and {len(detector_issues) - 3} more")
        
        except Exception as e:
            if verbose:
                print(f"  ERROR: Error analyzing directory {subdir.name}: {e}")
            
            results['directory_results'][subdir.name] = {
                'error': str(e),
                'analysis_time': 0,
                'issues_found': 0
            }
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Calculate performance metrics
    total_analyzed = results['files_tested'] + results['directories_tested']
    results['performance'] = {
        'total_time': total_duration,
        'avg_time_per_target': total_duration / max(total_analyzed, 1),
        'issues_per_second': results['total_issues'] / max(total_duration, 0.001),
        'targets_per_second': total_analyzed / max(total_duration, 0.001)
    }
    
    # Generate summary
    file_issue_counts = [
        result.get('issues_found', 0) 
        for result in results['file_results'].values()
        if 'issues_found' in result
    ]
    dir_issue_counts = [
        result.get('issues_found', 0) 
        for result in results['directory_results'].values()
        if 'issues_found' in result
    ]
    all_issue_counts = file_issue_counts + dir_issue_counts
    
    results['summary'] = {
        'avg_issues_per_target': sum(all_issue_counts) / max(len(all_issue_counts), 1),
        'max_issues_in_target': max(all_issue_counts) if all_issue_counts else 0,
        'min_issues_in_target': min(all_issue_counts) if all_issue_counts else 0,
        'targets_with_issues': len([c for c in all_issue_counts if c > 0]),
        'targets_without_issues': len([c for c in all_issue_counts if c == 0]),
        'multi_file_scenarios': results['directories_tested']
    }
    
    return results


def analyze_validation_effectiveness(results: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """
    Analyze the effectiveness of validation files in testing the detector.
    
    Args:
        results: Results from validate_detector
        verbose: Whether to print detailed analysis
        
    Returns:
        Dictionary containing effectiveness analysis
    """
    analysis = {
        'coverage': {},
        'distribution': {},
        'recommendations': []
    }
    
    file_results = results.get('file_results', {})
    
    # Analyze file coverage
    true_positive_files = [name for name, result in file_results.items() 
                          if 'true_positive' in name.lower() or 'edge_case' in name.lower()]
    false_positive_files = [name for name, result in file_results.items() 
                           if 'false_positive' in name.lower()]
    
    # Calculate issue distribution
    issue_severity_counts = defaultdict(int)
    issue_type_counts = defaultdict(int)
    
    for file_result in file_results.values():
        if 'issues' in file_result:
            for issue in file_result['issues']:
                issue_severity_counts[issue['severity']] += 1
                issue_type = issue['id'].split('.')[-1] if '.' in issue['id'] else issue['id']
                issue_type_counts[issue_type] += 1
    
    analysis['coverage'] = {
        'true_positive_files': len(true_positive_files),
        'false_positive_files': len(false_positive_files),
        'total_validation_files': len(file_results),
        'coverage_ratio': len(true_positive_files + false_positive_files) / max(len(file_results), 1)
    }
    
    analysis['distribution'] = {
        'severity_distribution': dict(issue_severity_counts),
        'issue_type_distribution': dict(issue_type_counts)
    }
    
    # Generate recommendations
    if len(true_positive_files) == 0:
        analysis['recommendations'].append("Add files with known true positives to validate detection accuracy")
    
    if len(false_positive_files) == 0:
        analysis['recommendations'].append("Add files with potential false positives to tune precision")
    
    if results['total_issues'] == 0:
        analysis['recommendations'].append("No issues detected - verify detector is working or add more test cases")
    
    if results['performance']['total_time'] > 10:
        analysis['recommendations'].append("Consider optimizing detector performance - analysis is slow")
    
    # Check for issue diversity
    unique_issue_types = len(issue_type_counts)
    if unique_issue_types < 3:
        analysis['recommendations'].append("Add more diverse test cases to cover different issue types")
    
    return analysis


def main():
    """Main validation script."""
    parser = argparse.ArgumentParser(description="Validate Pythonium detectors")
    parser.add_argument('--detector', '-d', help="Specific detector to validate")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    parser.add_argument('--output', '-o', help="Output file for results (JSON)")
    parser.add_argument('--report', '-r', action='store_true', help="Generate detailed report")
    parser.add_argument('--enable-cache', action='store_true', 
                       help="Enable caching (disabled by default for clean validation)")
    parser.add_argument('--enable-optimizations', action='store_true',
                       help="Enable all performance optimizations (parallel, incremental, etc.)")
    
    args = parser.parse_args()
    
    # Find validation directory
    validation_root = Path(__file__).parent / "detectors"
    
    if not validation_root.exists():
        print("ERROR: Validation directory not found")
        return 1
    
    # Get list of detectors to validate
    if args.detector:
        detector_dirs = [validation_root / args.detector]
        if not detector_dirs[0].exists():
            print(f"ERROR: Validation directory for {args.detector} not found")
            return 1
    else:
        detector_dirs = [d for d in validation_root.iterdir() if d.is_dir()]
    
    all_results = {}
    total_start_time = time.time()
    
    print("Starting detector validation...")
    print(f"Validation root: {validation_root}")
    print(f"Detectors to test: {len(detector_dirs)}")
    
    # Show configuration status
    if not getattr(args, 'enable_cache', False) and not getattr(args, 'enable_optimizations', False):
        print("Running with clean validation settings (caching and optimizations disabled)")
    else:
        if getattr(args, 'enable_cache', False):
            print("Caching enabled")
        if getattr(args, 'enable_optimizations', False):
            print("Performance optimizations enabled")
    print()
    
    for detector_dir in detector_dirs:
        detector_name = detector_dir.name
        
        if args.verbose:
            print(f"Testing detector: {detector_name}")
        
        results = validate_detector(
            detector_name, 
            detector_dir, 
            args.verbose,
            getattr(args, 'enable_cache', False),
            getattr(args, 'enable_optimizations', False)
        )
        effectiveness = analyze_validation_effectiveness(results, args.verbose)
        
        all_results[detector_name] = {
            'validation_results': results,
            'effectiveness_analysis': effectiveness
        }
        
        # Print summary for this detector
        total_targets = results['files_tested'] + results['directories_tested']
        if total_targets > 0:
            targets_desc = []
            if results['files_tested'] > 0:
                targets_desc.append(f"{results['files_tested']} files")
            if results['directories_tested'] > 0:
                targets_desc.append(f"{results['directories_tested']} directories")
            
            targets_str = " + ".join(targets_desc)
            multi_file_note = f" (includes {results['directories_tested']} multi-file scenarios)" if results['directories_tested'] > 0 else ""
            
            print(f"SUCCESS: {detector_name}: {results['total_issues']} issues in {targets_str} "
                  f"({results['performance']['total_time']:.2f}s){multi_file_note}")
            
            if effectiveness['recommendations']:
                print(f"Recommendations:")
                for rec in effectiveness['recommendations'][:2]:  # Show first 2
                    print(f"   - {rec}")
        else:
            print(f"WARNING: {detector_name}: No files or directories tested")
        
        if args.verbose:
            print()
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Generate overall summary
    total_files = sum(r['validation_results']['files_tested'] for r in all_results.values())
    total_directories = sum(r['validation_results']['directories_tested'] for r in all_results.values())
    total_issues = sum(r['validation_results']['total_issues'] for r in all_results.values())
    
    print(f"\nOverall Summary:")
    print(f"   Total detectors validated: {len(all_results)}")
    print(f"   Total files analyzed: {total_files}")
    print(f"   Total directories analyzed: {total_directories}")
    print(f"   Total multi-file scenarios: {total_directories}")
    print(f"   Total issues found: {total_issues}")
    print(f"   Total validation time: {total_duration:.2f}s")
    print(f"   Average issues per detector: {total_issues / max(len(all_results), 1):.1f}")
    
    # Summary of multi-file testing
    detectors_with_multi_file = len([r for r in all_results.values() if r['validation_results']['directories_tested'] > 0])
    if detectors_with_multi_file > 0:
        print(f"   Detectors with multi-file scenarios: {detectors_with_multi_file}")
        print(f"   Average multi-file scenarios per detector: {total_directories / max(len(all_results), 1):.1f}")
    
    # Save results to file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"Results saved to: {output_path}")
    
    # Generate detailed report if requested
    if args.report:
        report_path = Path("validation_report.md")
        generate_markdown_report(all_results, report_path)
        print(f"Detailed report saved to: {report_path}")
    
    return 0


def generate_markdown_report(results: Dict[str, Any], output_path: Path):
    """Generate a detailed markdown report of validation results."""
    
    with open(output_path, 'w') as f:
        f.write("# Pythonium Detector Validation Report\n\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overall summary
        f.write("## Overall Summary\n\n")
        total_detectors = len(results)
        total_files = sum(r['validation_results']['files_tested'] for r in results.values())
        total_directories = sum(r['validation_results']['directories_tested'] for r in results.values())
        total_issues = sum(r['validation_results']['total_issues'] for r in results.values())
        
        f.write(f"- **Detectors Validated**: {total_detectors}\n")
        f.write(f"- **Total Files Analyzed**: {total_files}\n")
        f.write(f"- **Total Directories Analyzed**: {total_directories}\n")
        f.write(f"- **Multi-File Scenarios**: {total_directories}\n")
        f.write(f"- **Total Issues Found**: {total_issues}\n")
        f.write(f"- **Average Issues per Detector**: {total_issues / max(total_detectors, 1):.1f}\n\n")
        
        # Detector details
        f.write("## Detector Results\n\n")
        
        for detector_name, detector_results in results.items():
            validation = detector_results['validation_results']
            effectiveness = detector_results['effectiveness_analysis']
            
            f.write(f"### {detector_name}\n\n")
            
            # Basic stats
            f.write(f"- **Files Tested**: {validation['files_tested']}\n")
            f.write(f"- **Directories Tested**: {validation['directories_tested']}\n")
            f.write(f"- **Multi-File Scenarios**: {validation['directories_tested']}\n")
            f.write(f"- **Issues Found**: {validation['total_issues']}\n")
            f.write(f"- **Analysis Time**: {validation['performance']['total_time']:.2f}s\n")
            f.write(f"- **Issues per Second**: {validation['performance']['issues_per_second']:.1f}\n\n")
            
            # File breakdown
            if validation['file_results']:
                f.write("#### Individual File Results\n\n")
                f.write("| File | Issues | Time (s) | Size (bytes) |\n")
                f.write("|------|--------|----------|-------------|\n")
                
                for filename, file_result in validation['file_results'].items():
                    issues = file_result.get('issues_found', 0)
                    time_taken = file_result.get('analysis_time', 0)
                    size = file_result.get('file_size', 0)
                    f.write(f"| {filename} | {issues} | {time_taken:.3f} | {size} |\n")
                
                f.write("\n")
            
            # Directory breakdown  
            if validation['directory_results']:
                f.write("#### Multi-File Scenario Results\n\n")
                f.write("| Directory | Issues | Files | Time (s) | Total Size (bytes) |\n")
                f.write("|-----------|--------|-------|----------|-----------------|\n")
                
                for dirname, dir_result in validation['directory_results'].items():
                    issues = dir_result.get('issues_found', 0)
                    files = dir_result.get('files_in_directory', 0)
                    time_taken = dir_result.get('analysis_time', 0)
                    size = dir_result.get('total_size', 0)
                    f.write(f"| {dirname} | {issues} | {files} | {time_taken:.3f} | {size} |\n")
                
                f.write("\n")
            
            # Directory breakdown
            if validation['directory_results']:
                f.write("#### Directory Results\n\n")
                f.write("| Directory | Issues | Time (s) | Files | Total Size (bytes) |\n")
                f.write("|-----------|--------|----------|-------|-------------------|\n")
                
                for dir_name, dir_result in validation['directory_results'].items():
                    issues = dir_result.get('issues_found', 0)
                    time_taken = dir_result.get('analysis_time', 0)
                    file_count = dir_result.get('files_in_directory', 0)
                    total_size = dir_result.get('total_size', 0)
                    f.write(f"| {dir_name} | {issues} | {time_taken:.3f} | {file_count} | {total_size} |\n")
                
                f.write("\n")
            
            # Recommendations
            if effectiveness['recommendations']:
                f.write("#### Recommendations\n\n")
                for rec in effectiveness['recommendations']:
                    f.write(f"- {rec}\n")
                f.write("\n")
            
            f.write("---\n\n")


if __name__ == "__main__":
    sys.exit(main())
