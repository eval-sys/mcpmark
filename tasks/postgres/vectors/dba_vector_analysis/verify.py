"""
Verification script for Vector Database DBA Analysis task.

This script verifies that the candidate has properly analyzed the vector database
and stored their findings in appropriate result tables.
"""

import logging
import psycopg2
import os
import sys
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


def get_connection_params():
    """Get database connection parameters from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USERNAME"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


def verify_vector_column_inventory(conn) -> Dict[str, Any]:
    """Verify that vector columns were properly inventoried."""
    results = {'score': 0, 'max_score': 25, 'issues': []}
    
    try:
        with conn.cursor() as cur:
            # Check if vector column inventory table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'vector_column_inventory'
                );
            """)
            
            if not cur.fetchone()[0]:
                results['issues'].append("vector_column_inventory table not found")
                return results
            
            # Get the inventory results
            cur.execute("SELECT * FROM vector_column_inventory ORDER BY table_name, column_name;")
            inventory = cur.fetchall()
            
            if not inventory:
                results['issues'].append("No vector columns found in inventory")
                return results
            
            # Expected vector columns in the test database
            expected_vector_columns = {
                ('documents', 'embedding'),
                ('document_chunks', 'embedding'), 
                ('user_queries', 'embedding')
            }
            
            found_columns = set()
            for row in inventory:
                # Extract table and column names (adjust based on actual table structure)
                if len(row) >= 2:
                    table_name = row[0] if row[0] else row[1]  # flexible column order
                    column_name = row[1] if row[0] else row[2]
                    found_columns.add((table_name, column_name))
            
            # Calculate score based on coverage
            matched_columns = found_columns & expected_vector_columns
            results['score'] = (len(matched_columns) / len(expected_vector_columns)) * results['max_score']
            
            if len(matched_columns) < len(expected_vector_columns):
                missing = expected_vector_columns - matched_columns
                results['issues'].append(f"Missing vector columns: {missing}")
            
            print(f"✅ Vector column inventory: {len(found_columns)} columns found, {len(matched_columns)}/{len(expected_vector_columns)} expected columns")
            
    except psycopg2.Error as e:
        results['issues'].append(f"Database error in vector column inventory: {e}")
    
    return results


def verify_storage_analysis(conn) -> Dict[str, Any]:
    """Verify that storage analysis was performed."""
    results = {'score': 0, 'max_score': 25, 'issues': []}
    
    try:
        with conn.cursor() as cur:
            # Check if storage analysis table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'vector_storage_analysis'
                );
            """)
            
            if not cur.fetchone()[0]:
                results['issues'].append("vector_storage_analysis table not found")
                return results
            
            # Get storage analysis results
            cur.execute("SELECT * FROM vector_storage_analysis;")
            storage_analysis = cur.fetchall()
            
            if not storage_analysis:
                results['issues'].append("No storage analysis results found")
                return results
            
            # Check that key tables are analyzed
            expected_tables = {'documents', 'document_chunks', 'user_queries'}
            analyzed_tables = set()
            
            for row in storage_analysis:
                # Extract table name (flexible based on column structure)
                if len(row) >= 1:
                    table_name = str(row[0]).strip() if row[0] else ''
                    if table_name:
                        analyzed_tables.add(table_name)
            
            matched_tables = analyzed_tables & expected_tables
            results['score'] = (len(matched_tables) / len(expected_tables)) * results['max_score']
            
            if len(matched_tables) < len(expected_tables):
                missing = expected_tables - matched_tables
                results['issues'].append(f"Missing storage analysis for tables: {missing}")
            
            print(f"✅ Storage analysis: {len(analyzed_tables)} tables analyzed, {len(matched_tables)}/{len(expected_tables)} expected tables")
            
    except psycopg2.Error as e:
        results['issues'].append(f"Database error in storage analysis: {e}")
    
    return results


def verify_index_analysis(conn) -> Dict[str, Any]:
    """Verify that vector index analysis was performed."""
    results = {'score': 0, 'max_score': 20, 'issues': []}
    
    try:
        with conn.cursor() as cur:
            # Check if index analysis table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'vector_index_analysis'
                );
            """)
            
            if not cur.fetchone()[0]:
                results['issues'].append("vector_index_analysis table not found")
                return results
            
            # Get index analysis results
            cur.execute("SELECT * FROM vector_index_analysis;")
            index_analysis = cur.fetchall()
            
            if not index_analysis:
                results['issues'].append("No index analysis results found")
                return results
            
            # Check that vector indexes were identified
            # The test database should have at least 3 vector indexes
            if len(index_analysis) >= 3:
                results['score'] = results['max_score']
                print(f"✅ Index analysis: {len(index_analysis)} indexes analyzed")
            else:
                results['score'] = (len(index_analysis) / 3) * results['max_score']
                results['issues'].append(f"Expected at least 3 vector indexes, found {len(index_analysis)}")
            
    except psycopg2.Error as e:
        results['issues'].append(f"Database error in index analysis: {e}")
    
    return results


def verify_data_quality_analysis(conn) -> Dict[str, Any]:
    """Verify that data quality analysis was performed."""
    results = {'score': 0, 'max_score': 15, 'issues': []}
    
    try:
        with conn.cursor() as cur:
            # Check if data quality analysis table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'vector_data_quality'
                );
            """)
            
            if not cur.fetchone()[0]:
                results['issues'].append("vector_data_quality table not found")
                return results
            
            # Get data quality results
            cur.execute("SELECT * FROM vector_data_quality;")
            quality_analysis = cur.fetchall()
            
            if not quality_analysis:
                results['issues'].append("No data quality analysis found")
                return results
            
            # Check for analysis of null values, dimension consistency, etc.
            if len(quality_analysis) >= 3:  # Expect analysis of at least 3 quality aspects
                results['score'] = results['max_score']
                print(f"✅ Data quality analysis: {len(quality_analysis)} quality checks performed")
            else:
                results['score'] = (len(quality_analysis) / 3) * results['max_score']
                results['issues'].append(f"Expected at least 3 quality checks, found {len(quality_analysis)}")
            
    except psycopg2.Error as e:
        results['issues'].append(f"Database error in data quality analysis: {e}")
    
    return results


def verify_analysis_summary(conn) -> Dict[str, Any]:
    """Verify that an overall analysis summary was created."""
    results = {'score': 0, 'max_score': 15, 'issues': []}
    
    try:
        with conn.cursor() as cur:
            # Check if analysis summary table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'vector_analysis_summary'
                );
            """)
            
            if not cur.fetchone()[0]:
                results['issues'].append("vector_analysis_summary table not found")
                return results
            
            # Get summary results
            cur.execute("SELECT * FROM vector_analysis_summary;")
            summary = cur.fetchall()
            
            if not summary:
                results['issues'].append("No analysis summary found")
                return results
            
            # Check for comprehensive summary
            if len(summary) >= 1:  # At least one summary record
                results['score'] = results['max_score']
                print(f"✅ Analysis summary: {len(summary)} summary records created")
            else:
                results['issues'].append("Analysis summary is incomplete")
            
    except psycopg2.Error as e:
        results['issues'].append(f"Database error in analysis summary: {e}")
    
    return results


def main():
    """Main verification function."""
    print("=" * 60)
    print("Verifying Vector Database DBA Analysis Results")
    print("=" * 60)
    
    conn_params = get_connection_params()
    
    if not conn_params["database"]:
        print("❌ No database specified")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(**conn_params)
        
        # Run all verification checks
        total_score = 0
        max_total_score = 100
        all_issues = []
        
        print("\n1. Verifying vector column inventory...")
        inventory_results = verify_vector_column_inventory(conn)
        total_score += inventory_results['score']
        all_issues.extend(inventory_results['issues'])
        
        print("\n2. Verifying storage analysis...")
        storage_results = verify_storage_analysis(conn)
        total_score += storage_results['score']
        all_issues.extend(storage_results['issues'])
        
        print("\n3. Verifying index analysis...")
        index_results = verify_index_analysis(conn)
        total_score += index_results['score']
        all_issues.extend(index_results['issues'])
        
        print("\n4. Verifying data quality analysis...")
        quality_results = verify_data_quality_analysis(conn)
        total_score += quality_results['score']
        all_issues.extend(quality_results['issues'])
        
        print("\n5. Verifying analysis summary...")
        summary_results = verify_analysis_summary(conn)
        total_score += summary_results['score']
        all_issues.extend(summary_results['issues'])
        
        conn.close()
        
        # Calculate percentage score
        percentage_score = (total_score / max_total_score) * 100
        
        print(f"\n{'='*60}")
        print(f"Verification Results:")
        print(f"Vector Column Inventory: {inventory_results['score']:.1f}/{inventory_results['max_score']}")
        print(f"Storage Analysis: {storage_results['score']:.1f}/{storage_results['max_score']}")
        print(f"Index Analysis: {index_results['score']:.1f}/{index_results['max_score']}")
        print(f"Data Quality Analysis: {quality_results['score']:.1f}/{quality_results['max_score']}")
        print(f"Analysis Summary: {summary_results['score']:.1f}/{summary_results['max_score']}")
        print(f"Total Score: {total_score:.1f}/{max_total_score} ({percentage_score:.1f}%)")
        
        # Show issues if any
        if all_issues:
            print(f"\nIssues found:")
            for issue in all_issues:
                print(f"  - {issue}")
        
        # Determine overall result
        if percentage_score >= 80:
            print("\n🎉 Vector DBA Analysis verification: PASS")
            print("Comprehensive analysis completed successfully.")
            sys.exit(0)
        elif percentage_score >= 60:
            print("\n⚠️ Vector DBA Analysis verification: PARTIAL PASS")
            print("Analysis completed but some aspects were missed.")
            sys.exit(0)
        else:
            print("\n❌ Vector DBA Analysis verification: FAIL")
            print("Analysis incomplete or missing critical components.")
            sys.exit(1)
            
    except psycopg2.Error as e:
        print(f"❌ Database connection error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()