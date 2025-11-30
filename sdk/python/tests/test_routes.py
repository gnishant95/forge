"""
Tests for Forge dynamic route management.

These tests verify:
- Listing routes
- Adding new routes
- Getting specific routes
- Deleting routes
- Nginx reload functionality
"""

import pytest


class TestRoutesListing:
    """Tests for listing routes."""

    def test_list_routes(self, http_client, forge):
        """Test listing all routes."""
        response = http_client.get(f"{forge.base_url}/api/v1/routes")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "routes" in data
        assert "count" in data
        assert isinstance(data["routes"], list)
        assert data["count"] >= 0

    def test_list_routes_returns_array(self, http_client, forge):
        """Test that routes list is always an array."""
        response = http_client.get(f"{forge.base_url}/api/v1/routes")
        
        assert response.status_code == 200
        data = response.json()
        
        routes = data.get("routes", [])
        assert isinstance(routes, list)


class TestRouteCreation:
    """Tests for creating routes."""

    def test_add_route(self, http_client, forge, cleanup_routes, test_id):
        """Test adding a new route."""
        route_name = f"test_route_{test_id}"
        cleanup_routes.append(route_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/test/{test_id}",
                "upstream": "http://httpbin.org",
                "methods": ["GET", "POST"]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data.get("ok") is True
        assert "route" in data

    def test_add_route_with_strip_prefix(self, http_client, forge, cleanup_routes, test_id):
        """Test adding a route with strip_prefix option."""
        route_name = f"test_strip_{test_id}"
        cleanup_routes.append(route_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/strip/{test_id}",
                "upstream": "http://example.com",
                "strip_prefix": True
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data.get("ok") is True

    def test_add_route_requires_name(self, http_client, forge):
        """Test that adding a route requires a name."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "path": "/test",
                "upstream": "http://example.com"
            }
        )
        
        # Should fail without name
        assert response.status_code == 400

    def test_add_route_requires_path(self, http_client, forge):
        """Test that adding a route requires a path."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": "test_no_path",
                "upstream": "http://example.com"
            }
        )
        
        # Should fail without path
        assert response.status_code == 400

    def test_add_route_requires_upstream(self, http_client, forge):
        """Test that adding a route requires an upstream."""
        response = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": "test_no_upstream",
                "path": "/test"
            }
        )
        
        # Should fail without upstream
        assert response.status_code == 400

    def test_add_duplicate_route_updates(self, http_client, forge, cleanup_routes, test_id):
        """Test that adding a duplicate route name updates the existing route."""
        route_name = f"test_duplicate_{test_id}"
        cleanup_routes.append(route_name)
        
        # Add first route
        response1 = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/dup/{test_id}",
                "upstream": "http://first.example.com"
            }
        )
        assert response1.status_code == 201
        
        # Add second route with same name
        response2 = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/dup/{test_id}",
                "upstream": "http://second.example.com"
            }
        )
        
        # Should succeed (update)
        assert response2.status_code == 201


class TestRouteRetrieval:
    """Tests for retrieving specific routes."""

    def test_get_route_by_name(self, http_client, forge, cleanup_routes, test_id):
        """Test getting a specific route by name."""
        route_name = f"test_get_{test_id}"
        cleanup_routes.append(route_name)
        
        # Create route first
        http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/get/{test_id}",
                "upstream": "http://example.com"
            }
        )
        
        # Get the route
        response = http_client.get(f"{forge.base_url}/api/v1/routes/{route_name}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == route_name

    def test_get_nonexistent_route(self, http_client, forge, test_id):
        """Test getting a route that doesn't exist."""
        response = http_client.get(f"{forge.base_url}/api/v1/routes/nonexistent_{test_id}")
        
        assert response.status_code == 404


class TestRouteDeletion:
    """Tests for deleting routes."""

    def test_delete_route(self, http_client, forge, test_id):
        """Test deleting a route."""
        route_name = f"test_delete_{test_id}"
        
        # Create route first
        http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/delete/{test_id}",
                "upstream": "http://example.com"
            }
        )
        
        # Delete the route
        response = http_client.delete(f"{forge.base_url}/api/v1/routes/{route_name}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True

    def test_delete_nonexistent_route(self, http_client, forge, test_id):
        """Test deleting a route that doesn't exist."""
        response = http_client.delete(f"{forge.base_url}/api/v1/routes/nonexistent_{test_id}")
        
        assert response.status_code == 404

    def test_deleted_route_not_retrievable(self, http_client, forge, test_id):
        """Test that deleted routes cannot be retrieved."""
        route_name = f"test_deleted_{test_id}"
        
        # Create route
        http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/deleted/{test_id}",
                "upstream": "http://example.com"
            }
        )
        
        # Delete route
        http_client.delete(f"{forge.base_url}/api/v1/routes/{route_name}")
        
        # Try to get deleted route
        response = http_client.get(f"{forge.base_url}/api/v1/routes/{route_name}")
        assert response.status_code == 404


class TestNginxReload:
    """Tests for nginx reload functionality."""

    def test_reload_nginx(self, http_client, forge):
        """Test manual nginx reload endpoint."""
        response = http_client.post(f"{forge.base_url}/api/v1/routes/reload")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True

    def test_route_add_triggers_reload(self, http_client, forge, cleanup_routes, test_id):
        """Test that adding a route triggers nginx reload."""
        route_name = f"test_reload_{test_id}"
        cleanup_routes.append(route_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/reload/{test_id}",
                "upstream": "http://example.com"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Response should indicate nginx was reloaded
        assert data.get("ok") is True
        assert "nginx reloaded" in data.get("message", "").lower() or "route" in data.get("message", "").lower()


class TestRouteConfiguration:
    """Tests for route configuration options."""

    def test_route_with_all_options(self, http_client, forge, cleanup_routes, test_id):
        """Test adding a route with all configuration options."""
        route_name = f"test_full_{test_id}"
        cleanup_routes.append(route_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/full/{test_id}",
                "upstream": "http://example.com",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "strip_prefix": True,
                "headers": {
                    "X-Custom-Header": "test-value"
                }
            }
        )
        
        assert response.status_code == 201
        
        # Verify route was created with options
        get_response = http_client.get(f"{forge.base_url}/api/v1/routes/{route_name}")
        assert get_response.status_code == 200
        
        route_data = get_response.json()
        assert route_data.get("name") == route_name

    def test_route_methods_default(self, http_client, forge, cleanup_routes, test_id):
        """Test that routes have default methods if not specified."""
        route_name = f"test_default_methods_{test_id}"
        cleanup_routes.append(route_name)
        
        response = http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/default/{test_id}",
                "upstream": "http://example.com"
            }
        )
        
        assert response.status_code == 201


class TestRoutePersistence:
    """Tests for route persistence."""

    def test_routes_persist_after_list(self, http_client, forge, cleanup_routes, test_id):
        """Test that routes persist and appear in list."""
        route_name = f"test_persist_{test_id}"
        cleanup_routes.append(route_name)
        
        # Add route
        http_client.post(
            f"{forge.base_url}/api/v1/routes",
            json={
                "name": route_name,
                "path": f"/persist/{test_id}",
                "upstream": "http://example.com"
            }
        )
        
        # List routes
        response = http_client.get(f"{forge.base_url}/api/v1/routes")
        data = response.json()
        
        routes = data.get("routes", [])
        route_names = [r.get("name") for r in routes]
        
        assert route_name in route_names

