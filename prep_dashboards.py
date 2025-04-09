#!/usr/bin/env python
import argparse
from glob import glob
import json
import os
import re

def extract_rhoso_dashboard(file_path, data):
    if 'openstack-openstack-network' in file_path:
        match1 = re.search(r'`(\{.*?\})`', data, re.DOTALL)
        if match1:
            dashBoardOVN = match1.group(1)

        match2 = re.search(r'dashBoardDpdk := `(.*?\})`', data, re.DOTALL)
        if match2:
            dashBoardDpdk = match2.group(1)

        # NOTE - the typo is in the source dashboard
        match3 = re.search(r'dashBaordFooter := `(\],.*?\})`', data, re.DOTALL)
        if match3:
            dashBoardFooter = match3.group(1)

        full = dashBoardOVN + "," + dashBoardDpdk + dashBoardFooter
        return full

    else:
        match = re.search(r'"[\w\-]+.json": `(.*)`,', data, re.DOTALL)  # `(.*})`,
        if match:
            return match.group(1)

def prep_eliminate_rows(dashboard):
    if 'rows' in dashboard and isinstance(dashboard['rows'], list):
        combined_panels = []

        for row in dashboard['rows']:
            if 'panels' in row and isinstance(row['panels'], list):
                combined_panels.extend(row['panels'])
            else:
                print(f"WARNING - Invalid structure in row: {row}")

        dashboard['panels'] = combined_panels
        del dashboard['rows']

def prep_add_name(dashboard, name):
    if 'metadata' not in dashboard:
        dashboard["metadata"] = {}
    if 'UID' not in dashboard:
        dashboard["UID"] = name

def prep_raw_empty_queries(dashboard_data):
    return re.sub(r'"expr": ""', '"expr": "#"', dashboard_data)

def prep_raw_drop_DS_PROMETHEUS(dashboard_data):
    return re.sub(r'\$\{DS_PROMETHEUS\}', '', dashboard_data)

def prep_raw(dashboard_data, name=None):
    dashboard_data = prep_raw_empty_queries(dashboard_data)
    dashboard_data = prep_raw_drop_DS_PROMETHEUS(dashboard_data)
    return dashboard_data

def prep_panel_sizes(dashboard_data):
    for panel in dashboard_data["panels"]:
        if ('gridPos' not in panel) or ('h' not in panel["gridPos"]):
            panel["gridPos"] = {
                "h": 8,
                "w": 12
            }

def prep(dashboard, name):
    prep_eliminate_rows(dashboard)
    prep_add_name(dashboard, name)
    prep_panel_sizes(dashboard)

def main():
    parser = argparse.ArgumentParser(description="Prep dashboards for import to Perses")
    parser.add_argument("-r", "--rhoso-dashboards-dir", required=False, default="./telemetry-operator/pkg/dashboards/", help="Path to RHOSO dashboards")
    parser.add_argument("-d", "--dashboards-dir", required=False, default="./dashboards", help="Path to non-rhoso .json dashboards")
    parser.add_argument("-o", "--output-dir", required=False, default="./out", help="Path to write dashboards")

    args = parser.parse_args()

    if not os.path.isdir(args.rhoso_dashboards_dir):
        print(f"ERROR - {args.rhoso_dashboards_dir} is not a valid directory.")
        return

    process_paths = []
    for file in glob(args.rhoso_dashboards_dir + '/*.go'):
        process_paths.append(file)

    for file in glob(args.dashboards_dir + "/*.json"):
        process_paths.append(file)

    for file_path in process_paths:
        print(f"INFO - Processing file: {file_path}")
        name = os.path.basename(file_path).replace('.go$', '').replace('.json$', '')
        with open(file_path, 'r') as file:
            data = file.read()

        if args.rhoso_dashboards_dir in file_path:
            json_string = extract_rhoso_dashboard(file_path, data)
        else:
            json_string = data

        if json_string:
            json_string = prep_raw(json_string)

            dashboard = json.loads(json_string)
            if not dashboard:
                print(f"WARNING - Could not part JSON from {file_path}")

            prep(dashboard, name)

            with open(os.path.join(args.output_dir, os.path.basename(file_path).replace('.go', '.json')), 'w') as file:
                json.dump(dashboard, file, indent=4)
        else:
            print(f"WARNING - Could not find JSON data to parse from {file_path}")

if __name__ == "__main__":
    main()



