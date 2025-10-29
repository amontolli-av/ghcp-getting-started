"""
Tests for the activities API endpoints
"""
import pytest
from fastapi import status


class TestActivitiesAPI:
    """Test class for activities API endpoints."""
    
    def test_get_activities_success(self, client, reset_activities):
        """Test successful retrieval of activities."""
        response = client.get("/activities")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check that we get the expected activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Check structure of an activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_get_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static files."""
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "/static/index.html"


class TestSignupAPI:
    """Test class for signup API endpoints."""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity."""
        email = "newstudent@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == f"Signed up {email} for {activity_name}"
        
        # Verify the student was added to the activity
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test signup fails when student is already registered."""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity_name = "Chess Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup fails for non-existent activity."""
        email = "student@mergington.edu"
        activity_name = "Nonexistent Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_activities(self, client, reset_activities):
        """Test student can sign up for multiple different activities."""
        email = "multistudent@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Sign up for Programming Class
        response2 = client.post(f"/activities/Programming Class/signup?email={email}")
        assert response2.status_code == status.HTTP_200_OK
        
        # Verify student is in both activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Programming Class"]["participants"]


class TestUnregisterAPI:
    """Test class for unregister API endpoints."""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistering from an activity."""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity_name = "Chess Club"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == f"Unregistered {email} from {activity_name}"
        
        # Verify the student was removed from the activity
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregister fails when student is not registered."""
        email = "notregistered@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister fails for non-existent activity."""
        email = "student@mergington.edu"
        activity_name = "Nonexistent Club"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_then_unregister_workflow(self, client, reset_activities):
        """Test complete workflow: signup -> unregister."""
        email = "workflow@mergington.edu"
        activity_name = "Programming Class"
        
        # First, sign up
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == status.HTTP_200_OK
        
        # Verify signup worked
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
        
        # Then unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == status.HTTP_200_OK
        
        # Verify unregister worked
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]


class TestActivityConstraints:
    """Test class for activity business logic and constraints."""
    
    def test_participant_count_tracking(self, client, reset_activities):
        """Test that participant counts are tracked correctly."""
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        # Chess Club should have 2 initial participants
        chess_club = activities_data["Chess Club"]
        assert len(chess_club["participants"]) == 2
        assert chess_club["max_participants"] == 12
        
        # Add a new participant
        email = "newchess@mergington.edu"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Check updated count
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        chess_club = activities_data["Chess Club"]
        assert len(chess_club["participants"]) == 3
        assert email in chess_club["participants"]
    
    def test_activity_data_integrity(self, client, reset_activities):
        """Test that activity data maintains its integrity."""
        # Get initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        
        # Perform some operations
        client.post("/activities/Chess Club/signup?email=test1@mergington.edu")
        client.post("/activities/Programming Class/signup?email=test2@mergington.edu")
        client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        # Check that non-participant data remains unchanged
        final_response = client.get("/activities")
        final_data = final_response.json()
        
        for activity_name in initial_data:
            initial_activity = initial_data[activity_name]
            final_activity = final_data[activity_name]
            
            # These should remain unchanged
            assert initial_activity["description"] == final_activity["description"]
            assert initial_activity["schedule"] == final_activity["schedule"]
            assert initial_activity["max_participants"] == final_activity["max_participants"]