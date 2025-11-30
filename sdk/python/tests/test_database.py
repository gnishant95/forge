"""
Tests for Forge database operations.

These tests verify:
- Query and execute operations via SDK
- SQLAlchemy integration
- Connection info retrieval
- Database isolation and cleanup
"""

import pytest


class TestDatabaseQuery:
    """Tests for database query operations."""

    def test_query_show_databases(self, forge):
        """Test querying list of databases."""
        result = forge.db.query("SHOW DATABASES")
        
        assert result is not None
        assert "rows" in result
        assert "columns" in result
        assert result["row_count"] >= 0
        
        # Should have at least information_schema
        databases = [row[0] for row in result["rows"]]
        assert "information_schema" in databases

    def test_query_with_database(self, forge, cleanup_db):
        """Test querying with specific database context."""
        db_name = cleanup_db
        
        # Create a table in the test database
        forge.db.execute(
            f"CREATE TABLE IF NOT EXISTS {db_name}.test_table (id INT PRIMARY KEY, name VARCHAR(255))",
            database=db_name
        )
        
        # Query the table
        result = forge.db.query(f"SELECT * FROM {db_name}.test_table")
        
        assert result is not None
        assert "rows" in result
        assert result["row_count"] == 0  # Empty table

    def test_query_returns_columns(self, forge):
        """Test that query returns column information."""
        result = forge.db.query("SELECT 1 as num, 'hello' as greeting")
        
        assert result is not None
        assert "columns" in result
        assert len(result["columns"]) == 2
        assert "num" in result["columns"]
        assert "greeting" in result["columns"]


class TestDatabaseExecute:
    """Tests for database execute operations."""

    def test_execute_create_table(self, forge, cleanup_db):
        """Test executing CREATE TABLE statement."""
        db_name = cleanup_db
        
        result = forge.db.execute(
            f"CREATE TABLE {db_name}.users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255))"
        )
        
        assert result is not None

    def test_execute_insert(self, forge, cleanup_db):
        """Test executing INSERT statement."""
        db_name = cleanup_db
        
        # Create table
        forge.db.execute(
            f"CREATE TABLE {db_name}.items (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255))"
        )
        
        # Insert data
        result = forge.db.execute(
            f"INSERT INTO {db_name}.items (name) VALUES ('Test Item')"
        )
        
        assert result is not None
        assert result.get("rows_affected", 0) >= 1 or result.get("rowsAffected", 0) >= 1

    def test_execute_insert_returns_last_id(self, forge, cleanup_db):
        """Test that INSERT returns last insert ID."""
        db_name = cleanup_db
        
        # Create table with auto increment
        forge.db.execute(
            f"CREATE TABLE {db_name}.products (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255))"
        )
        
        # Insert first item
        result = forge.db.execute(
            f"INSERT INTO {db_name}.products (name) VALUES ('Product 1')"
        )
        
        last_id = result.get("last_insert_id", result.get("lastInsertId", 0))
        assert last_id >= 1

    def test_execute_update(self, forge, cleanup_db):
        """Test executing UPDATE statement."""
        db_name = cleanup_db
        
        # Create and populate table
        forge.db.execute(
            f"CREATE TABLE {db_name}.status (id INT PRIMARY KEY, active BOOLEAN)"
        )
        forge.db.execute(f"INSERT INTO {db_name}.status VALUES (1, FALSE)")
        
        # Update
        result = forge.db.execute(
            f"UPDATE {db_name}.status SET active = TRUE WHERE id = 1"
        )
        
        rows_affected = result.get("rows_affected", result.get("rowsAffected", 0))
        assert rows_affected == 1

    def test_execute_delete(self, forge, cleanup_db):
        """Test executing DELETE statement."""
        db_name = cleanup_db
        
        # Create and populate table
        forge.db.execute(
            f"CREATE TABLE {db_name}.temp (id INT PRIMARY KEY)"
        )
        forge.db.execute(f"INSERT INTO {db_name}.temp VALUES (1), (2), (3)")
        
        # Delete
        result = forge.db.execute(
            f"DELETE FROM {db_name}.temp WHERE id > 1"
        )
        
        rows_affected = result.get("rows_affected", result.get("rowsAffected", 0))
        assert rows_affected == 2


class TestDatabaseInfo:
    """Tests for database connection info."""

    def test_db_url_format(self, forge):
        """Test that db.url() returns proper connection URL."""
        url = forge.db.url()
        
        assert url is not None
        assert url.startswith("mysql+pymysql://")
        assert "@" in url  # Contains credentials
        assert ":" in url  # Contains port

    def test_db_url_with_database(self, forge):
        """Test that db.url() accepts database parameter."""
        url = forge.db.url(database="testdb")
        
        assert url is not None
        assert url.endswith("/testdb")


class TestSQLAlchemyIntegration:
    """Tests for SQLAlchemy integration."""

    def test_create_engine(self, forge, cleanup_db):
        """Test creating SQLAlchemy engine."""
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            pytest.skip("SQLAlchemy not installed")
        
        db_name = cleanup_db
        engine = forge.db.engine(database=db_name)
        
        assert engine is not None
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row[0] == 1

    def test_sqlalchemy_create_table(self, forge, cleanup_db):
        """Test creating table via SQLAlchemy."""
        try:
            from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, text
        except ImportError:
            pytest.skip("SQLAlchemy not installed")
        
        db_name = cleanup_db
        engine = forge.db.engine(database=db_name)
        
        # Create table using SQLAlchemy
        metadata = MetaData()
        users = Table(
            'users', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(100)),
            Column('email', String(255))
        )
        
        metadata.create_all(engine)
        
        # Verify table exists
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            assert "users" in tables

    def test_sqlalchemy_crud_operations(self, forge, cleanup_db):
        """Test CRUD operations via SQLAlchemy."""
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            pytest.skip("SQLAlchemy not installed")
        
        db_name = cleanup_db
        engine = forge.db.engine(database=db_name)
        
        with engine.connect() as conn:
            # Create
            conn.execute(text(
                "CREATE TABLE items (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100))"
            ))
            conn.commit()
            
            # Insert
            conn.execute(text("INSERT INTO items (name) VALUES ('Item 1')"))
            conn.execute(text("INSERT INTO items (name) VALUES ('Item 2')"))
            conn.commit()
            
            # Read
            result = conn.execute(text("SELECT * FROM items ORDER BY id"))
            rows = result.fetchall()
            assert len(rows) == 2
            assert rows[0][1] == "Item 1"
            
            # Update
            conn.execute(text("UPDATE items SET name = 'Updated' WHERE id = 1"))
            conn.commit()
            
            result = conn.execute(text("SELECT name FROM items WHERE id = 1"))
            row = result.fetchone()
            assert row[0] == "Updated"
            
            # Delete
            conn.execute(text("DELETE FROM items WHERE id = 2"))
            conn.commit()
            
            result = conn.execute(text("SELECT COUNT(*) FROM items"))
            count = result.fetchone()[0]
            assert count == 1


class TestDatabaseIsolation:
    """Tests for database isolation between tests."""

    def test_create_isolated_database(self, forge, test_db_name):
        """Test that we can create an isolated database."""
        # Create database
        forge.db.execute(f"CREATE DATABASE IF NOT EXISTS {test_db_name}")
        
        # Verify it exists
        result = forge.db.query("SHOW DATABASES")
        databases = [row[0] for row in result["rows"]]
        assert test_db_name in databases
        
        # Cleanup
        forge.db.execute(f"DROP DATABASE IF EXISTS {test_db_name}")

    def test_databases_are_independent(self, forge, cleanup_db):
        """Test that test databases are independent."""
        db_name = cleanup_db
        
        # Create table in test database
        forge.db.execute(
            f"CREATE TABLE {db_name}.isolated_test (id INT PRIMARY KEY)"
        )
        
        # Table should exist in test database
        result = forge.db.query(f"SHOW TABLES FROM {db_name}")
        tables = [row[0] for row in result["rows"]]
        assert "isolated_test" in tables

