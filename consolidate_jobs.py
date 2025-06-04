import pandas as pd
import glob
import os

# Get all Excel files excluding temporary files
excel_files = [f for f in glob.glob("job_matches_*.xlsx") if not f.startswith("~")]

# Sort files by timestamp (newest first)
excel_files.sort(reverse=True)

# Dictionary to store dataframes for each sheet
sheet_dfs = {}

# Read each Excel file
for file in excel_files:
    try:
        # Read all sheets in the Excel file
        xlsx = pd.ExcelFile(file)
        sheet_names = xlsx.sheet_names
        
        for sheet_name in sheet_names:
            df = pd.read_excel(file, sheet_name=sheet_name)
            # Add columns to track source
            df['Source File'] = file
            df['Original Sheet'] = sheet_name
            
            if sheet_name not in sheet_dfs:
                sheet_dfs[sheet_name] = []
            
            sheet_dfs[sheet_name].append(df)
            print(f"Successfully read sheet '{sheet_name}' from {file}")
            
    except Exception as e:
        print(f"Error reading {file}: {str(e)}")

if sheet_dfs:
    # Create output filename with timestamp
    output_file = f"consolidated_jobs_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # Create Excel writer object
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        total_unique_jobs = 0
        
        # Process each sheet type
        for sheet_name, dfs in sheet_dfs.items():
            if dfs:
                # Combine all dataframes for this sheet type
                combined_df = pd.concat(dfs, ignore_index=True)
                
                # Remove duplicates (based on all columns except 'Source File' and 'Original Sheet')
                columns_for_dedup = [col for col in combined_df.columns if col not in ['Source File', 'Original Sheet']]
                combined_df = combined_df.drop_duplicates(subset=columns_for_dedup)
                
                # Save to the Excel file
                combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
                total_unique_jobs += len(combined_df)
                print(f"\nSheet '{sheet_name}': {len(combined_df)} unique entries")
        
        print(f"\nSuccessfully consolidated {len(excel_files)} files into {output_file}")
        print(f"Total number of unique jobs across all sheets: {total_unique_jobs}")
else:
    print("No Excel files found to consolidate") 