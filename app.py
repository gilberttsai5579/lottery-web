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

# Import services
from src.main.python.services.lottery import LotteryEngine
from src.main.python.services.scrapers import ScraperFactory, ScrapingError
from src.main.python.utils import ExcelExporter

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
    
    # Initialize services
    lottery_engine = LotteryEngine()
    excel_exporter = ExcelExporter(output_dir=app.config['OUTPUT_DIR'])
    
    @app.route('/')
    def index():
        """Main page"""
        return render_template('index.html')
    
    @app.route('/lottery', methods=['POST'])
    def lottery():
        """Execute lottery"""
        try:
            data = request.get_json()
            app.logger.info(f"Lottery request: {data}")
            
            # Extract parameters
            url = data.get('url')
            mode = data.get('mode')
            keyword = data.get('keyword', '')
            mention_count = data.get('mention_count', 1)
            winner_count = data.get('winner_count', 1)
            
            # Validate inputs
            if not url:
                return jsonify({'error': 'URL is required'}), 400
            
            if mode not in ['1', '2', '3']:
                return jsonify({'error': 'Invalid lottery mode'}), 400
            
            if winner_count < 1:
                return jsonify({'error': 'Winner count must be at least 1'}), 400
            
            # Check if URL is supported
            if not ScraperFactory.is_supported_url(url):
                return jsonify({'error': 'Unsupported URL format. Please use Threads or Instagram post URLs.'}), 400
            
            # Conduct lottery
            try:
                result = lottery_engine.conduct_lottery(
                    url=url,
                    mode=mode,
                    winner_count=winner_count,
                    keyword=keyword,
                    mention_count_required=mention_count
                )
                
                # Return result
                return jsonify(result.to_dict())
                
            except ScrapingError as e:
                app.logger.error(f"Scraping error: {e}")
                return jsonify({'error': f'Failed to scrape comments: {str(e)}'}), 400
            
            except ValueError as e:
                app.logger.error(f"Validation error: {e}")
                return jsonify({'error': str(e)}), 400
            
        except Exception as e:
            app.logger.error(f"Lottery error: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({'error': 'An unexpected error occurred during lottery'}), 500
    
    @app.route('/preview', methods=['POST'])
    def preview():
        """Preview participants without conducting lottery"""
        try:
            data = request.get_json()
            
            # Extract parameters
            url = data.get('url')
            mode = data.get('mode')
            keyword = data.get('keyword', '')
            mention_count = data.get('mention_count', 1)
            
            # Validate inputs
            if not url:
                return jsonify({'error': 'URL is required'}), 400
            
            if mode not in ['1', '2', '3']:
                return jsonify({'error': 'Invalid lottery mode'}), 400
            
            if not ScraperFactory.is_supported_url(url):
                return jsonify({'error': 'Unsupported URL format'}), 400
            
            # Get preview
            preview_result = lottery_engine.preview_participants(
                url=url,
                mode=mode,
                keyword=keyword,
                mention_count_required=mention_count
            )
            
            return jsonify(preview_result)
            
        except Exception as e:
            app.logger.error(f"Preview error: {str(e)}")
            return jsonify({'error': 'An error occurred during preview'}), 500
    
    @app.route('/download/<result_id>')
    def download(result_id):
        """Download Excel file with lottery results"""
        try:
            # Retrieve lottery result
            result = lottery_engine.get_result(result_id)
            if not result:
                return jsonify({'error': 'Lottery result not found'}), 404
            
            # Generate Excel file
            filename = excel_exporter.export_lottery_result(result)
            
            # Return file for download
            return send_file(
                filename,
                as_attachment=True,
                download_name=f"lottery_result_{result_id}.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            app.logger.error(f"Download error: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({'error': 'An error occurred during download'}), 500
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'supported_platforms': ScraperFactory.get_supported_platforms()
        })
    
    @app.route('/api/validate-url', methods=['POST'])
    def validate_url():
        """Validate if URL is supported"""
        try:
            data = request.get_json()
            url = data.get('url')
            
            if not url:
                return jsonify({'valid': False, 'error': 'URL is required'})
            
            is_valid = ScraperFactory.is_supported_url(url)
            platform = None
            
            if is_valid:
                try:
                    platform = ScraperFactory.detect_platform(url)
                except:
                    pass
            
            return jsonify({
                'valid': is_valid,
                'platform': platform,
                'supported_platforms': ScraperFactory.get_supported_platforms()
            })
            
        except Exception as e:
            return jsonify({'valid': False, 'error': str(e)})
    
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