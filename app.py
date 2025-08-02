"""
Flask application for lottery web
Main entry point for the web application
"""
import os
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime
import traceback

from config import config

# Import services (to be implemented)
# from src.main.python.services.scrapers import ThreadsScraper, InstagramScraper
# from src.main.python.services.lottery import LotteryEngine
# from src.main.python.utils.excel_export import ExcelExporter

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Enable CORS
    CORS(app)
    
    # Register routes
    register_routes(app)
    
    return app


def register_routes(app):
    """Register all application routes"""
    
    @app.route('/')
    def index():
        """Main page"""
        return render_template('index.html')
    
    @app.route('/lottery', methods=['POST'])
    def lottery():
        """Execute lottery"""
        try:
            data = request.get_json()
            
            # Extract parameters
            url = data.get('url')
            mode = data.get('mode')
            keyword = data.get('keyword', '')
            mention_count = data.get('mention_count', 0)
            winner_count = data.get('winner_count', 1)
            
            # Validate inputs
            if not url:
                return jsonify({'error': 'URL is required'}), 400
            
            if mode not in ['1', '2', '3']:
                return jsonify({'error': 'Invalid lottery mode'}), 400
            
            # TODO: Implement lottery logic
            # 1. Detect platform (Threads or Instagram)
            # 2. Scrape comments
            # 3. Apply lottery logic based on mode
            # 4. Generate results
            
            # Placeholder response
            result = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'mode': mode,
                'total_participants': 0,
                'winners': [],
                'result_id': 'placeholder_id'
            }
            
            return jsonify(result)
            
        except Exception as e:
            app.logger.error(f"Lottery error: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({'error': 'An error occurred during lottery'}), 500
    
    @app.route('/download/<result_id>')
    def download(result_id):
        """Download Excel file with lottery results"""
        try:
            # TODO: Implement Excel download
            # 1. Retrieve lottery results by ID
            # 2. Generate Excel file
            # 3. Return file for download
            
            # Placeholder
            return jsonify({'error': 'Download not yet implemented'}), 501
            
        except Exception as e:
            app.logger.error(f"Download error: {str(e)}")
            return jsonify({'error': 'An error occurred during download'}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)