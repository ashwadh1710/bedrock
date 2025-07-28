from flask import Blueprint, request, jsonify
from app.services.bedrock_service import BedrockService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
api_bp = Blueprint('api', __name__)
bedrock_service = BedrockService()

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@api_bp.route('/model/invoke', methods=['POST'])
def invoke_model():
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt in request'}), 400

        response = bedrock_service.invoke_model(data['prompt'])
        return jsonify(response), 200
    except Exception as e:
        logger.error(f"Error invoking model: {str(e)}")
        return jsonify({'error': str(e)}), 500