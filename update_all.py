#!/usr/bin/env python3
"""
Master script to update all internship data
Run this locally or via GitHub Actions
"""
import subprocess
import sys

def run_command(command, description):
    """Run a command and report results"""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def main():
    print("Starting comprehensive internship data update...")
    
    # Step 1: Scrape GitHub repos
    if not run_command("python3 scrape_github_repos.py", "Scraping GitHub repositories"):
        print("Failed to scrape GitHub repos")
        sys.exit(1)
    
    # Step 2: Merge data
    if not run_command("python3 merge_internship_data.py", "Merging internship data"):
        print("Failed to merge data")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("Update completed successfully!")
    print("="*50)
    print("\nUpdated files:")
    print("- scraped_internships.csv (raw data from GitHub repos)")
    print("- Summer2027_SWE_Tracker.csv (comprehensive tracker)")

if __name__ == "__main__":
    main()