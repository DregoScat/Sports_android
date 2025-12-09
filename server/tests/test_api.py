"""
Integration tests for API routes.

Tests for Flask endpoints and streaming functionality.
"""

import pytest
import sys
import os
import json
import base64
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAPIRoutes:
    """Test suite for API routes."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the Flask app."""
        from run import create_app
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_index_route(self, client):
        """Test that index page loads correctly."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_health_check(self, client):
        """Test health check endpoint if available."""
        # Add health check endpoint tests
        pass
    
    def test_process_frame_invalid_json(self, client):
        """Test process_frame with invalid JSON."""
        response = client.post(
            '/process_frame',
            data='not json',
            content_type='application/json'
        )
        # Should handle gracefully
        assert response.status_code in [400, 500]
    
    def test_process_frame_missing_image(self, client):
        """Test process_frame with missing image field."""
        response = client.post(
            '/process_frame',
            json={'type': 'squat'}
        )
        assert response.status_code == 400
    
    def test_process_frame_valid_request(self, client):
        """Test process_frame with valid request."""
        # Create a small test image
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Encode to base64
        import cv2
        _, buffer = cv2.imencode('.jpg', test_image)
        base64_image = base64.b64encode(buffer).decode('utf-8')
        
        response = client.post(
            '/process_frame',
            json={
                'image': base64_image,
                'type': 'squat'
            }
        )
        
        # Should process successfully
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'image' in data
    
    def test_reset_analyzer(self, client):
        """Test analyzer reset endpoint."""
        response = client.post(
            '/reset_analyzer',
            json={'type': 'squat'}
        )
        assert response.status_code == 200


class TestStreamingEndpoints:
    """Test suite for video streaming endpoints."""
    
    def test_squat_feed_content_type(self, client):
        """Test that squat_feed returns correct content type."""
        # Note: This test may require mocking the camera
        pass
    
    def test_jump_feed_content_type(self, client):
        """Test that jump_feed returns correct content type."""
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
