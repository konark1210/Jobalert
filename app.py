from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
import glob
import os
import logging
import traceback
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def clean_column_name(name):
    """Clean and standardize column names"""
    if isinstance(name, str):
        # Remove special characters and extra spaces
        cleaned = name.strip().replace(' ', '_').replace('-', '_')
        # Convert to lowercase
        return cleaned.lower()
    return str(name)

def clean_value(value):
    """Clean and format cell values"""
    if pd.isna(value) or value is None:
        return None
    elif isinstance(value, (pd.Timestamp, pd.DatetimeTZDtype)):
        return value.isoformat()
    elif isinstance(value, (float, np.float64)):
        # Check if it's actually an integer
        if value.is_integer():
            return int(value)
        return float(value)
    elif isinstance(value, (int, np.int64)):
        return int(value)
    else:
        # Clean string values
        cleaned = str(value).strip()
        # Log location values for debugging
        if any(key in str(value).lower() for key in ['location', 'place', 'city', 'area']):
            logger.debug(f"Cleaning location value: {value} -> {cleaned}")
        return cleaned

def get_consolidated_file():
    try:
        # Look for the most recent consolidated file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Base directory: {base_dir}")
        
        files = glob.glob(os.path.join(base_dir, "consolidated_jobs_*.xlsx"))
        logger.info(f"Files found in base directory: {files}")
        
        # If no files found in current directory, try parent directory
        if not files:
            parent_dir = os.path.dirname(base_dir)
            logger.info(f"Trying parent directory: {parent_dir}")
            files = glob.glob(os.path.join(parent_dir, "consolidated_jobs_*.xlsx"))
            logger.info(f"Files found in parent directory: {files}")
        
        if not files:
            logger.error("No consolidated jobs file found")
            return None
            
        latest_file = max(files)
        logger.info(f"Found consolidated file: {latest_file}")
        
        # Verify file exists and is readable
        if not os.path.isfile(latest_file):
            logger.error(f"File does not exist: {latest_file}")
            return None
            
        if not os.access(latest_file, os.R_OK):
            logger.error(f"File is not readable: {latest_file}")
            return None
            
        # Log file size and permissions
        file_stats = os.stat(latest_file)
        logger.info(f"File size: {file_stats.st_size} bytes")
        logger.info(f"File permissions: {oct(file_stats.st_mode)}")
        
        return latest_file
    except Exception as e:
        logger.error(f"Error finding consolidated file: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def load_jobs():
    consolidated_file = get_consolidated_file()
    if not consolidated_file:
        logger.error("No consolidated file found")
        return {
            "error": None,
            "last_updated": None,
            "jobs": {}
        }
    
    try:
        logger.info(f"Loading jobs from {consolidated_file}")
        excel_file = pd.ExcelFile(consolidated_file)
        jobs_data = {}
        
        # Get file modification time
        last_updated = datetime.fromtimestamp(os.path.getmtime(consolidated_file))
        logger.info(f"File last modified: {last_updated}")
        
        # Read each sheet from the consolidated file
        for sheet_name in excel_file.sheet_names:
            logger.info(f"Processing sheet: {sheet_name}")
            
            # Read the Excel sheet
            df = pd.read_excel(consolidated_file, sheet_name=sheet_name)
            logger.info(f"Found {len(df)} jobs in sheet {sheet_name}")
            
            # Clean column names
            df.columns = [clean_column_name(col) for col in df.columns]
            logger.info(f"Columns in sheet {sheet_name}: {list(df.columns)}")
            
            # Log location-related columns for debugging
            location_columns = [col for col in df.columns if any(key in col.lower() for key in ['location', 'place', 'city', 'area'])]
            if location_columns:
                logger.info(f"Found location columns in sheet {sheet_name}: {location_columns}")
            
            # Convert DataFrame to list of dictionaries with proper handling of data types
            jobs = []
            for idx, row in df.iterrows():
                try:
                    # Clean all values in the row
                    job_dict = {col: clean_value(row[col]) for col in df.columns}
                    
                    # Ensure there's an ID field
                    if 'id' not in job_dict or not job_dict['id']:
                        job_dict['id'] = str(idx + 1)
                    
                    # Log location data for debugging
                    location_data = {k: v for k, v in job_dict.items() if any(key in k.lower() for key in ['location', 'place', 'city', 'area'])}
                    if location_data:
                        logger.debug(f"Job {job_dict.get('id')} location data: {location_data}")
                    
                    jobs.append(job_dict)
                    
                except Exception as e:
                    logger.error(f"Error processing job at index {idx} in sheet {sheet_name}: {str(e)}")
                    logger.error(f"Row data: {row.to_dict()}")
                    logger.error(traceback.format_exc())
                    continue
            
            jobs_data[sheet_name] = jobs
            logger.info(f"Successfully processed {len(jobs)} jobs from sheet {sheet_name}")
        
        return {
            "error": None,
            "last_updated": last_updated.isoformat(),
            "jobs": jobs_data
        }
    except Exception as e:
        logger.error(f"Error loading jobs: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "error": None,
            "last_updated": None,
            "jobs": {}
        }

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/jobs')
def get_jobs():
    try:
        result = load_jobs()
        if result["error"]:
            return jsonify(result), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting jobs: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Internal server error",
            "last_updated": None,
            "jobs": {}
        }), 500

@app.route('/health')
def health_check():
    try:
        # Get the consolidated file
        consolidated_file = get_consolidated_file()
        if not consolidated_file:
            return jsonify({
                "status": "error",
                "message": "No consolidated file found",
                "file_path": None
            }), 500
            
        # Try to read the file
        try:
            excel_file = pd.ExcelFile(consolidated_file)
            sheets = excel_file.sheet_names
            total_jobs = 0
            
            # Count jobs in each sheet
            for sheet in sheets:
                df = pd.read_excel(consolidated_file, sheet_name=sheet)
                total_jobs += len(df)
            
            return jsonify({
                "status": "healthy",
                "message": "File loaded successfully",
                "file_path": consolidated_file,
                "sheets": sheets,
                "total_jobs": total_jobs,
                "file_size": os.path.getsize(consolidated_file),
                "file_permissions": oct(os.stat(consolidated_file).st_mode),
                "current_directory": os.getcwd(),
                "script_directory": os.path.dirname(os.path.abspath(__file__))
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error reading file: {str(e)}",
                "file_path": consolidated_file,
                "traceback": traceback.format_exc()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error in health check: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    # Use environment variable for port if available (for production)
    port = int(os.environ.get('PORT', 8000))
    # Only run in debug mode if not in production
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug) 