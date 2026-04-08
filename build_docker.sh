#!/bin/bash
# Ensure we're in the same directory as the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Parse arguments
VERSION=""
PUSH=false

for arg in "$@"; do
  case $arg in
    --push)
      PUSH=true
      ;;
    *)
      VERSION="$arg"
      ;;
  esac
done

if [ -z "$VERSION" ]; then
  echo "Error: Version parameter is missing."
  echo "Usage: ./build_docker.sh <version> [--push]"
  echo "Example: ./build_docker.sh v1.0.9.6major28"
  echo "Example: ./build_docker.sh v1.0.9.6major28 --push"
  exit 1
fi

# Generate .msg file for the latest version
# Generate .msg and .html files for the latest version
UPDATES_JSON="produksjonssystem/release_notes/release_notes.json"
MSG_FILE="$(dirname "$UPDATES_JSON")/latest.msg"
HTML_FILE="$(dirname "$UPDATES_JSON")/latest.html"

if [ -f "$UPDATES_JSON" ]; then
  echo "Generating $MSG_FILE and $HTML_FILE from $UPDATES_JSON..."
  python3 -c "
import json
import sys
import urllib.request
from datetime import datetime

try:
    # 1. Load release notes
    with open('$UPDATES_JSON', 'r') as f:
        data = json.load(f)
        latest = data['updates'][0]
        version = latest['version']
        date = latest['date']
        
        # Plain text sections
        msg_out = [
            \"Hei,\",
            \"Vi har nå publisert en ny versjon av produksjonssystemet.\",
            \"Nedenfor finner dere en oversikt over endringer, forbedringer og feilrettinger i denne oppdateringen.\",
            \"\",
            f\"Version: {version}\",
            f\"Date: {date}\",
            \"\"
        ]
        
        # HTML sections
        html_sections = []
        
        changes = latest.get('changes', {})
        for section in ['added', 'changed', 'fixed']:
            items = changes.get(section, [])
            if items and any(items):
                # Text
                msg_out.append(f\"{section.capitalize()}:\")
                for item in items:
                    if item.strip():
                        msg_out.append(f\"- {item}\")
                msg_out.append(\"\")
                
                # HTML
                color = {\"added\": \"#28a745\", \"changed\": \"#ffc107\", \"fixed\": \"#dc3545\"}.get(section, \"#666\")
                label = {\"added\": \"Lagt til\", \"changed\": \"Endret\", \"fixed\": \"Rettet\"}.get(section, section.capitalize())
                section_html = f\"\"\"
                    <div style='margin-bottom: 20px;'>
                        <span style='background-color: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; margin-right: 10px;'>{label}</span>
                        <ul style='margin-top: 10px; color: #333;'>
                \"\"\"
                for item in items:
                    if item.strip():
                        section_html += f\"<li style='margin-bottom: 5px;'>{item}</li>\"
                section_html += \"</ul></div>\"
                html_sections.append(section_html)

    # 2. Fetch GitHub issues
    issues_html = \"\"
    try:
        url = \"https://api.github.com/repos/llsynit/produksjonssystem/issues\"
        req = urllib.request.Request(url, headers={\"User-Agent\": \"Mozilla/5.0\"})
        with urllib.request.urlopen(req, timeout=5) as response:
            all_issues = json.loads(response.read().decode())
            if all_issues:
                # Group issues by parent
                sub_issues_map = {}
                top_level_issues = []
                for issue in all_issues:
                    parent_url = issue.get('parent_issue_url')
                    if parent_url:
                        sub_issues_map.setdefault(parent_url, []).append(issue)
                    else:
                        top_level_issues.append(issue)
                
                # Text
                msg_out.append(\"Issues (from https://github.com/llsynit/produksjonssystem/issues):\")
                for issue in top_level_issues[:15]:
                    msg_out.append(f\"- #{issue['number']}: {issue['title']}\")
                    msg_out.append(f\"  {issue['html_url']}\")
                    children = sub_issues_map.get(issue['url'], [])
                    for child in children:
                        msg_out.append(f\"  - #{child['number']}: {child['title']}\")
                        msg_out.append(f\"    {child['html_url']}\")
                msg_out.append(\"\")
                
                # HTML
                issues_html = \"<div style='margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px;'>\"
                issues_html += \"<h3 style='color: #005aab; margin-bottom: 5px; font-size: 16px;'>Åpne saker (GitHub)</h3>\"
                issues_html += \"<ul style='color: #444; font-size: 13px; padding-left: 20px;'>\"
                for issue in top_level_issues[:15]:
                    issues_html += f\"<li style='margin-bottom: 8px;'>#{issue['number']}: {issue['title']}<br><a href='{issue['html_url']}' style='color: #005aab; font-size: 11px;'>{issue['html_url']}</a>\"
                    children = sub_issues_map.get(issue['url'], [])
                    if children:
                        issues_html += \"<ul style='margin-top: 4px; color: #666; font-size: 12px;'>\"
                        for child in children:
                            issues_html += f\"<li style='margin-bottom: 4px;'>#{child['number']}: {child['title']}<br><a href='{child['html_url']}' style='color: #005aab; font-size: 10px;'>{child['html_url']}</a></li>\"
                        issues_html += \"</ul>\"
                    issues_html += \"</li>\"
                issues_html += \"</ul></div>\"
    except Exception as fetch_error:
        print(f\"Warning: Could not fetch GitHub issues: {fetch_error}\", file=sys.stderr)

    # 3. Add Outro
    msg_out.extend([
        \"Dersom dere opplever problemer etter oppdateringen, eller har spørsmål til endringene, ta gjerne kontakt.\",
        \"Med vennlig hilsen\"
    ])

    # 4. Write .msg file
    with open('$MSG_FILE', 'w', encoding='utf-8') as out_f:
        out_f.write(\"\\n\".join(msg_out))
        
    # 5. Build and write HTML file
    final_html = f\"\"\"
    <!DOCTYPE html>
    <html lang='no'>
    <head><meta charset='UTF-8'></head>
    <body style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif; line-height: 1.4; color: #333; max-width: 800px; margin: 0; padding: 10px;'>
        <p style='margin-bottom: 5px;'>Hei,</p>
        <p style='margin-top: 0; margin-bottom: 20px;'>Vi har nå publisert en ny versjon av produksjonssystemet.<br>Nedenfor finner dere en oversikt over endringer, forbedringer og feilrettinger i denne oppdateringen.</p>
        
        <div style='margin-bottom: 20px; border-bottom: 1px solid #005aab; padding-bottom: 5px;'>
            <h2 style='color: #005aab; margin: 0; font-size: 18px;'>Version: {version}</h2>
            <p style='margin: 0; color: #666; font-size: 13px;'>Date: {date}</p>
        </div>
        
        <div style='margin-top: 15px;'>
        {''.join(html_sections)}
        </div>
        
        {issues_html}
        
        <div style='margin-top: 25px; padding-top: 10px; border-top: 1px solid #eee; font-size: 13px;'>
            <p style='margin: 0;'>Dersom dere opplever problemer etter oppdateringen, eller har spørsmål til endringene, ta gjerne kontakt.</p>
            <p style='font-weight: bold; margin-top: 10px; margin-bottom: 0; color: #005aab;'>Med vennlig hilsen</p>
            <p style='color: #666; margin: 0;'>Produksjonssystemet</p>
        </div>
    </body>
    </html>
    \"\"\"
    with open('$HTML_FILE', 'w', encoding='utf-8') as out_f:
        out_f.write(final_html)
        
    print(\"Successfully generated $MSG_FILE and $HTML_FILE\")
except Exception as e:
    print(f\"Error: Could not generate release note files: {e}\", file=sys.stderr)
"
else
  echo "Warning: $UPDATES_JSON not found. Skipping .msg generation."
fi

if [ "$PUSH" = true ]; then
  echo "Starting docker buildx process for platform linux/amd64,linux/arm64 (with push)..."
  docker buildx build --platform linux/amd64,linux/arm64 --build-arg PRODSYS_VERSION="$VERSION" -t "llsynit/produksjonssystem:$VERSION" --push .
else
  echo "Starting docker buildx process for platform linux/amd64,linux/arm64..."
  docker buildx build --platform linux/amd64,linux/arm64 --build-arg PRODSYS_VERSION="$VERSION" -t "llsynit/produksjonssystem:$VERSION" .
fi