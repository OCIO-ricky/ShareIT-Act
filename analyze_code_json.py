#!/usr/bin/env python3
"""
Analyze code.json file for repository statistics
"""

import json
import argparse
from collections import defaultdict, Counter
from pathlib import Path


def analyze_code_json(file_path, group_by_org=False):
    """Analyze code.json file and return statistics"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    projects = data.get('projects', [])
    
    # Initialize counters
    visibility_count = Counter()
    usage_type_count = Counter()
    exemption_text_count = Counter()
    org_stats = defaultdict(lambda: {
        'visibility': Counter(),
        'usage_type': Counter(),
        'exemption_text': Counter(),
        'total': 0
    })
    
    # Analyze each project
    for project in projects:
        # Repository visibility
        visibility = project.get('repositoryVisibility', 'unknown')
        visibility_count[visibility] += 1
        
        # Usage type and exemption
        permissions = project.get('permissions', {})
        usage_type = permissions.get('usageType', 'unknown')
        exemption_text = permissions.get('exemptionText', 'No exemption text')
        
        usage_type_count[usage_type] += 1
        exemption_text_count[exemption_text] += 1
        
        # Organization breakdown if requested
        if group_by_org:
            org = project.get('organization', 'Unknown')
            org_stats[org]['visibility'][visibility] += 1
            org_stats[org]['usage_type'][usage_type] += 1
            org_stats[org]['exemption_text'][exemption_text] += 1
            org_stats[org]['total'] += 1
    
    return {
        'total_projects': len(projects),
        'visibility': dict(visibility_count),
        'usage_type': dict(usage_type_count),
        'exemption_text': dict(exemption_text_count),
        'organizations': dict(org_stats) if group_by_org else {}
    }


def print_results(stats, group_by_org=False):
    """Print analysis results in a readable format"""
    
    print(f"📊 CODE.JSON ANALYSIS REPORT")
    print(f"{'='*50}")
    print(f"Total Projects: {stats['total_projects']}")
    print()
    
    # Repository Visibility
    print("🔒 REPOSITORY VISIBILITY")
    print("-" * 30)
    for visibility, count in sorted(stats['visibility'].items()):
        percentage = (count / stats['total_projects']) * 100
        print(f"  {visibility.capitalize()}: {count:,} ({percentage:.1f}%)")
    print()
    
    # Usage Type (Exempted vs Non-exempted)
    print("⚖️  USAGE TYPE")
    print("-" * 30)
    exempted_count = 0
    non_exempted_count = 0
    
    for usage_type, count in sorted(stats['usage_type'].items()):
        percentage = (count / stats['total_projects']) * 100
        print(f"  {usage_type}: {count:,} ({percentage:.1f}%)")
        
        if 'exempt' in usage_type.lower():
            exempted_count += count
        else:
            non_exempted_count += count
    
    print(f"\n  📈 SUMMARY:")
    print(f"    Exempted: {exempted_count:,} ({(exempted_count/stats['total_projects'])*100:.1f}%)")
    print(f"    Non-exempted: {non_exempted_count:,} ({(non_exempted_count/stats['total_projects'])*100:.1f}%)")
    print()
    
    # Exemption Text Breakdown
    print("📋 EXEMPTION CODES/TEXT")
    print("-" * 30)
    for exemption, count in sorted(stats['exemption_text'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_projects']) * 100
        # Truncate long exemption text
        display_text = exemption[:60] + "..." if len(exemption) > 60 else exemption
        print(f"  {display_text}: {count:,} ({percentage:.1f}%)")
    print()
    
    # Organization breakdown
    if group_by_org and stats['organizations']:
        print("🏢 BY ORGANIZATION")
        print("-" * 30)
        for org, org_data in sorted(stats['organizations'].items(), key=lambda x: x[1]['total'], reverse=True):
            print(f"\n  📂 {org} ({org_data['total']:,} projects)")
            
            # Visibility for this org
            print(f"    Visibility:")
            for visibility, count in sorted(org_data['visibility'].items()):
                percentage = (count / org_data['total']) * 100
                print(f"      {visibility}: {count:,} ({percentage:.1f}%)")
            
            # Usage type for this org
            print(f"    Usage Type:")
            for usage_type, count in sorted(org_data['usage_type'].items()):
                percentage = (count / org_data['total']) * 100
                print(f"      {usage_type}: {count:,} ({percentage:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Analyze code.json file for repository statistics')
    parser.add_argument('file', help='Path to code.json file')
    parser.add_argument('--by-org', action='store_true', help='Group results by organization')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"❌ Error: File '{args.file}' not found")
        return 1
    
    try:
        stats = analyze_code_json(args.file, group_by_org=args.by_org)
        print_results(stats, group_by_org=args.by_org)
    except Exception as e:
        print(f"❌ Error analyzing file: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
