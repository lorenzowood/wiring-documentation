import os
import csv
import sys
from datetime import datetime

def extract_zone_data(directory, plan_name, tabs_list_file, zones_list_file, output_filename, custom_timestamp=None):
    # Read the tabs and zones list from the files
    try:
        with open(tabs_list_file, 'r') as f:
            tabs_list = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        print(f"Error: The file {tabs_list_file} does not exist.")
        return

    try:
        with open(zones_list_file, 'r') as f:
            zones_list = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        print(f"Error: The file {zones_list_file} does not exist.")
        return
    
    # Generate timestamp for footer
    if custom_timestamp:
        timestamp = custom_timestamp
    else:
        current_time = datetime.now()
        # Format: "6 October 2025 at 15:56" (no leading zeros)
        timestamp = current_time.strftime("%-d %B %Y at %H:%M")

    # Open the output file for writing
    with open(output_filename, 'w') as out_file:
        sys.stdout = out_file  # Redirect output to the file

        print(f'''<html>
<head>
<style>
    :root {{
        font-family: 'Helvetica';
        font-size: 11px;
    }}
    @page {{
        size: A3 landscape;
        margin: 1 in;
        @bottom-left {{
            content: "{plan_name}";
        }}
        @bottom-center {{
            content: "Generated on {timestamp}";
        }}
        @bottom-right {{
            content: "Page " counter(page) " of " counter(pages);
        }}
    }}
    table {{
        width: auto;
        border-collapse: collapse;
        text-align: left;
        vertical-align: top;
    }}
    
    th, td {{
        padding: 8px;
        border: 1px solid #ccc;
    }}
    
    tr:nth-child(even) {{
        background-color: #e0e0e0; /* 20% grey */
    }}
    
    tr:nth-child(odd) {{
        background-color: #ffffff; /* White for odd rows */
    }}
</style>
</head>
<body>
''')
        
        print(f"<h1>{plan_name}</h1>")

        # Process each tab
        for tab in tabs_list:
            # Find all CSV files that start with the tab name
            matching_files = [
                f for f in os.listdir(directory) if f.startswith(tab) and f.endswith(".csv")
            ]
            
            if len(matching_files) == 0:
                print(f"Error: No CSV files found for tab {tab}.")
            elif len(matching_files) > 1:
                print(f"Error: Ambiguous choice of CSV files for tab {tab}. Files found:")
                for f in matching_files:
                    print(f"  - {f}")
            else:
                tab_filename = os.path.join(directory, matching_files[0])
                print(f"<h2>{tab}</h2>")
                
                with open(tab_filename, 'r') as csvfile:
                    print('<table>')
                    reader = csv.reader(csvfile)
                    
                    row_zone = ''
                    # Iterate through each row
                    for i, row in enumerate(reader):
                        if row:  # Skip empty rows
                            # If it's the first row (header), print "true"
                            if i == 0:
                                print('<tr><th>' + '</th><th>'.join(cell for cell in row) + '</th></tr>')
                                #print(f'th,"' + '","'.join(cell.replace('"', '""') for cell in row) + '"')
                            else:
                                if row[1] != '':
                                    row_zone = row[1]            
                                # Check if the second column matches any zone
                                if row_zone in zones_list and row[0] !='':
                                    print(
                                        unicode_to_html_entities(
                                            '<tr><td>'
                                            + '</td><td>'.join(cell for cell in row)
                                            + '</td></tr>'
                                        )
                                    )
                                    #print(f'td,"'+'","'.join(cell.replace('"', '""') for cell in row) + '"')
                    print('</table>')
                    
        print('''
</body>
</html>
''')
        # Reset sys.stdout after writing to file
        sys.stdout = sys.__stdout__

    print(f"Data extraction complete. Output written to {output_filename}")

def unicode_to_html_entities(text):
    return ''.join(f'&#{ord(c)};' if ord(c) > 127 else c for c in text)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Extract zone data and generate HTML output')
    parser.add_argument('directory', help='Directory containing CSV data files')
    parser.add_argument('plan_name', help='Name of the plan/room')
    parser.add_argument('tabs_list_file', help='File containing list of tabs')
    parser.add_argument('zones_list_file', help='File containing list of zones')
    parser.add_argument('output_filename', help='Output HTML filename')
    parser.add_argument('--set-timestamp', type=str, help='Use specified timestamp string instead of current time')

    args = parser.parse_args()

    # Run the data extraction function
    extract_zone_data(args.directory, args.plan_name, args.tabs_list_file,
                     args.zones_list_file, args.output_filename, args.set_timestamp)

if __name__ == '__main__':
    main()
