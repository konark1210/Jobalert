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
        files = glob.glob(os.path.join(base_dir, "consolidated_jobs_*.xlsx"))
        if not files:
            logger.error("No consolidated jobs file found")
            return None
        latest_file = max(files)
        logger.info(f"Found consolidated file: {latest_file}")
        return latest_file
    except Exception as e:
        logger.error(f"Error finding consolidated file: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def load_jobs():
    consolidated_file = get_consolidated_file()
    if not consolidated_file:
        return {
            "error": "No data file found",
            "last_updated": None,
            "jobs": {}
        }
    
    try:
        logger.info(f"Loading jobs from {consolidated_file}")
        excel_file = pd.ExcelFile(consolidated_file)
        jobs_data = {}
        
        # Get file modification time
        last_updated = datetime.fromtimestamp(os.path.getmtime(consolidated_file))
        
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
            "error": "Error loading jobs data",
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

@app.route('/api/apply', methods=['POST'])
def apply_job():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        job_id = data.get('job_id')
        sheet_name = data.get('sheet_name')
        
        if not job_id or not sheet_name:
            return jsonify({"error": "Missing job_id or sheet_name"}), 400
            
        logger.info(f"Applying for job {job_id} from sheet {sheet_name}")
        # Here you would typically handle the job application
        # For now, we'll just return a success message
        return jsonify({
            'status': 'success',
            'message': f'Successfully applied for job {job_id} from {sheet_name}'
        })
    except Exception as e:
        logger.error(f"Error applying for job: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Use environment variable for port if available (for production)
    port = int(os.environ.get('PORT', 8000))
    # Only run in debug mode if not in production
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug) 