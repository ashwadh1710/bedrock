import os
from dotenv import load_dotenv
from app import create_app
from app.utils.logger import setup_logger

# Set up logging
logger = setup_logger(__name__)

# Load environment variables
load_dotenv()

def main():
    try:
        app = create_app()
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5001))
        debug = os.getenv('DEBUG', 'False').lower() == 'true'

        logger.info(f"Starting application on {host}:{port}")
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise

if __name__ == '__main__':
    main()