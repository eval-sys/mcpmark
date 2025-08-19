Analyze vector database storage, identify vector columns, and assess space utilization for a PostgreSQL database with pgvector extension.

## Your Mission:

You are a PostgreSQL DBA tasked with analyzing a vector database that stores embeddings for RAG (Retrieval-Augmented Generation) applications. The database uses the pgvector extension and contains multiple tables with vector columns storing high-dimensional embeddings.

## Analysis Requirements:

1. **Vector Column Discovery**:
   - Identify all tables containing vector columns
   - Determine the dimensions of each vector column
   - Find which schemas contain vector data
   - Catalog the vector column data types and constraints

2. **Storage Analysis**:
   - Calculate storage space used by vector columns
   - Determine total table sizes including vector data
   - Analyze storage efficiency and space utilization
   - Compare vector storage vs. regular column storage

3. **Performance Assessment**:
   - Identify existing vector indexes (HNSW, IVFFlat)
   - Analyze index types and their configurations
   - Assess query performance implications
   - Review index storage overhead

4. **Data Quality Evaluation**:
   - Check for NULL vector values
   - Verify vector dimension consistency
   - Identify any orphaned or incomplete vector data
   - Validate vector normalization (if applicable)

5. **Extension Analysis**:
   - Verify pgvector extension installation and version
   - Check extension permissions and availability
   - Review vector-specific functions and operators
   - Assess extension configuration

## Expected Deliverables:

Store your analysis results in the following database tables:

1. **vector_column_inventory**: Complete inventory of vector columns
   - Include: table_name, column_name, schema_name, vector_dimensions, data_type
   
2. **vector_storage_analysis**: Storage space analysis for vector data
   - Include: table_name, total_size_bytes, vector_storage_bytes, regular_storage_bytes, record_count
   
3. **vector_index_analysis**: Analysis of vector indexes and performance
   - Include: index_name, table_name, index_type, index_size_bytes, index_method
   
4. **vector_data_quality**: Data quality assessment results
   - Include: table_name, quality_check_type, issue_count, total_records, quality_status
   
5. **vector_analysis_summary**: Overall findings and recommendations
   - Include: analysis_category, finding_description, severity_level, recommendation

## Key Questions to Answer:

1. Which tables and schemas contain vector columns?
2. What are the dimensions and data types of each vector column?
3. How much storage space is consumed by vector data vs. regular data?
4. What types of vector indexes exist and how effective are they?
5. Are there any data quality issues with the vector columns?
6. What is the total overhead of the pgvector extension?
7. How can storage efficiency be improved?
8. What are the performance characteristics of vector operations?

## Technical Focus Areas:

- **Storage Management**: Understanding vector storage patterns and optimization
- **Index Strategy**: Analyzing vector index effectiveness and configuration
- **Performance Monitoring**: Assessing query performance for vector operations
- **Capacity Planning**: Projecting future storage requirements
- **Data Governance**: Ensuring vector data quality and consistency

Use PostgreSQL system catalogs, pgvector-specific views, and storage analysis functions to gather comprehensive metrics about the vector database implementation.