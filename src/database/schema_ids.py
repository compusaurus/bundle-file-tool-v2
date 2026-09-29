# ===================================================================================================
# SOURCEFILE: schema_ids.py
# Relative Path: src/database/schema_ids.py
# Purpose: Strong-typed DB schema references with immutable UIDs from project_manifest.json.
# Call Chain: scripts/manifest_manager.py --export → generate_schema_ids.py
# Project: BFT_v2
# Team: Ringo / George / John / Paul
# Version: 3.0.4
# Lifecycle: Generated
# Status: Production
# Updated: 2026-09-23 02:48:13Z
# independent_entry_point: false
# ===================================================================================================

# AUTO-GENERATED SCHEMA IDENTIFIERS
# DO NOT EDIT MANUALLY
#
# Generated from: project_manifest.json v3.0.4
# Generated at: see Updated above
# Generator: scripts/generate_schema_ids.py (called by manifest_manager.py --export)
# Manifest hash: sha256:189af2e39503021a61ff1dd1719365e5ee895294972c7c4e04a24d2a3e99c174


from typing import Final
from pathlib import Path
from database.schema_refs import TableRef, ColRef, DatabaseRef

# ============================================================================
# MANIFEST METADATA
# ===================================================================================================

# NEW: Metadata extracted from ManifestContext (three-tier system)
MANIFEST_VERSION: Final[str] = "3.0.4"
MANIFEST_HASH: Final[str] = "189af2e39503021a61ff1dd1719365e5ee895294972c7c4e04a24d2a3e99c174"
PROJECT_NAME: Final[str] = "BFT_v2"
PROJECT_VERSION: Final[str] = "2.1.136"

# Schema Statistics
TOTAL_TABLES: Final[int] = 6
TOTAL_COLUMNS: Final[int] = 66
TOTAL_DATABASES: Final[int] = 1

# ============================================================================
# DATABASE: AssetsDB (UID: db-6f3763f2)
# ============================================================================

class AssetsDB:
    """
    Database: AssetsDB
    
    UID: db-6f3763f2 (IMMUTABLE)
    Physical Name: AssetsDB (renameable)
    Path: .pyprojectmgr/assets.db
    Tables: 6
    
    George's Path Resolution:
          Code defines default: DB_PATH = Path(".pyprojectmgr/assets.db")
          Runtime can override via ProjectSpec (see schema_context.py)
    """
    
    DB_UID: Final[str] = "db-6f3763f2"
    DB_NAME: Final[str] = "AssetsDB"
    LOGICAL_NAME: Final[str] = "AssetsDB"
    DB_PATH: Final[Path] = Path(".pyprojectmgr/assets.db")
    
    REF: Final[DatabaseRef] = DatabaseRef(
        uid="db-6f3763f2",
        name="AssetsDB",
        logical_name="AssetsDB"
    )

    # ------------------------------------------------------------------------
    # TABLE: assets (UID: db-6f3763f2.tbl001)
    # ------------------------------------------------------------------------
    
    class Assets:
        """
        Primary registry of project files and code units
        
        UID: db-6f3763f2.tbl001 (IMMUTABLE)
        Physical Name: assets (renameable)
        Primary Key: asset_id
        Columns: 34
        """
        
        TABLE_UID: Final[str] = "db-6f3763f2.tbl001"
        TABLE_NAME: Final[str] = "assets"
        PRIMARY_KEY: Final[str] = "asset_id"
        
        REF: Final[TableRef] = TableRef(
            uid="db-6f3763f2.tbl001",
            name="assets",
            db_uid="db-6f3763f2",
            primary_key="asset_id"
        )
        
        class Cols:
            """Column identifiers for assets table"""
            
            # Column: asset_id (UID: db-6f3763f2.tbl001.col001)
            ASSET_ID: Final[str] = "asset_id"
            ASSET_ID_UID: Final[str] = "db-6f3763f2.tbl001.col001"
            ASSET_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col001",
                name="asset_id",
                table_uid="db-6f3763f2.tbl001",
                col_type="INTEGER"
            )
            
            # Column: asset_uid (UID: db-6f3763f2.tbl001.col002)
            ASSET_UID: Final[str] = "asset_uid"
            ASSET_UID_UID: Final[str] = "db-6f3763f2.tbl001.col002"
            ASSET_UID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col002",
                name="asset_uid",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: symbol_fqn (UID: db-6f3763f2.tbl001.col003)
            SYMBOL_FQN: Final[str] = "symbol_fqn"
            SYMBOL_FQN_UID: Final[str] = "db-6f3763f2.tbl001.col003"
            SYMBOL_FQN_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col003",
                name="symbol_fqn",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: asset_name (UID: db-6f3763f2.tbl001.col004)
            ASSET_NAME: Final[str] = "asset_name"
            ASSET_NAME_UID: Final[str] = "db-6f3763f2.tbl001.col004"
            ASSET_NAME_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col004",
                name="asset_name",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: asset_type (UID: db-6f3763f2.tbl001.col005)
            ASSET_TYPE: Final[str] = "asset_type"
            ASSET_TYPE_UID: Final[str] = "db-6f3763f2.tbl001.col005"
            ASSET_TYPE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col005",
                name="asset_type",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: file_path (UID: db-6f3763f2.tbl001.col006)
            FILE_PATH: Final[str] = "file_path"
            FILE_PATH_UID: Final[str] = "db-6f3763f2.tbl001.col006"
            FILE_PATH_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col006",
                name="file_path",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: line_number (UID: db-6f3763f2.tbl001.col007)
            LINE_NUMBER: Final[str] = "line_number"
            LINE_NUMBER_UID: Final[str] = "db-6f3763f2.tbl001.col007"
            LINE_NUMBER_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col007",
                name="line_number",
                table_uid="db-6f3763f2.tbl001",
                col_type="INTEGER"
            )
            
            # Column: module_path (UID: db-6f3763f2.tbl001.col008)
            MODULE_PATH: Final[str] = "module_path"
            MODULE_PATH_UID: Final[str] = "db-6f3763f2.tbl001.col008"
            MODULE_PATH_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col008",
                name="module_path",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: logical_name (UID: db-6f3763f2.tbl001.col009)
            LOGICAL_NAME: Final[str] = "logical_name"
            LOGICAL_NAME_UID: Final[str] = "db-6f3763f2.tbl001.col009"
            LOGICAL_NAME_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col009",
                name="logical_name",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: status (UID: db-6f3763f2.tbl001.col010)
            STATUS: Final[str] = "status"
            STATUS_UID: Final[str] = "db-6f3763f2.tbl001.col010"
            STATUS_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col010",
                name="status",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: created_at (UID: db-6f3763f2.tbl001.col011)
            CREATED_AT: Final[str] = "created_at"
            CREATED_AT_UID: Final[str] = "db-6f3763f2.tbl001.col011"
            CREATED_AT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col011",
                name="created_at",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: updated_at (UID: db-6f3763f2.tbl001.col012)
            UPDATED_AT: Final[str] = "updated_at"
            UPDATED_AT_UID: Final[str] = "db-6f3763f2.tbl001.col012"
            UPDATED_AT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col012",
                name="updated_at",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: session_id (UID: db-6f3763f2.tbl001.col013)
            SESSION_ID: Final[str] = "session_id"
            SESSION_ID_UID: Final[str] = "db-6f3763f2.tbl001.col013"
            SESSION_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col013",
                name="session_id",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: notes (UID: db-6f3763f2.tbl001.col014)
            NOTES: Final[str] = "notes"
            NOTES_UID: Final[str] = "db-6f3763f2.tbl001.col014"
            NOTES_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col014",
                name="notes",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: parent_name (UID: db-6f3763f2.tbl001.col015)
            PARENT_NAME: Final[str] = "parent_name"
            PARENT_NAME_UID: Final[str] = "db-6f3763f2.tbl001.col015"
            PARENT_NAME_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col015",
                name="parent_name",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: component (UID: db-6f3763f2.tbl001.col016)
            COMPONENT: Final[str] = "component"
            COMPONENT_UID: Final[str] = "db-6f3763f2.tbl001.col016"
            COMPONENT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col016",
                name="component",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: module_alias (UID: db-6f3763f2.tbl001.col017)
            MODULE_ALIAS: Final[str] = "module_alias"
            MODULE_ALIAS_UID: Final[str] = "db-6f3763f2.tbl001.col017"
            MODULE_ALIAS_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col017",
                name="module_alias",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: signature (UID: db-6f3763f2.tbl001.col018)
            SIGNATURE: Final[str] = "signature"
            SIGNATURE_UID: Final[str] = "db-6f3763f2.tbl001.col018"
            SIGNATURE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col018",
                name="signature",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: description (UID: db-6f3763f2.tbl001.col019)
            DESCRIPTION: Final[str] = "description"
            DESCRIPTION_UID: Final[str] = "db-6f3763f2.tbl001.col019"
            DESCRIPTION_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col019",
                name="description",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: asset_hash (UID: db-6f3763f2.tbl001.col020)
            ASSET_HASH: Final[str] = "asset_hash"
            ASSET_HASH_UID: Final[str] = "db-6f3763f2.tbl001.col020"
            ASSET_HASH_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col020",
                name="asset_hash",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: discovered_by (UID: db-6f3763f2.tbl001.col021)
            DISCOVERED_BY: Final[str] = "discovered_by"
            DISCOVERED_BY_UID: Final[str] = "db-6f3763f2.tbl001.col021"
            DISCOVERED_BY_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col021",
                name="discovered_by",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: discovered_at (UID: db-6f3763f2.tbl001.col022)
            DISCOVERED_AT: Final[str] = "discovered_at"
            DISCOVERED_AT_UID: Final[str] = "db-6f3763f2.tbl001.col022"
            DISCOVERED_AT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col022",
                name="discovered_at",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: last_modified (UID: db-6f3763f2.tbl001.col023)
            LAST_MODIFIED: Final[str] = "last_modified"
            LAST_MODIFIED_UID: Final[str] = "db-6f3763f2.tbl001.col023"
            LAST_MODIFIED_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col023",
                name="last_modified",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: approved_by (UID: db-6f3763f2.tbl001.col024)
            APPROVED_BY: Final[str] = "approved_by"
            APPROVED_BY_UID: Final[str] = "db-6f3763f2.tbl001.col024"
            APPROVED_BY_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col024",
                name="approved_by",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: approved_at (UID: db-6f3763f2.tbl001.col025)
            APPROVED_AT: Final[str] = "approved_at"
            APPROVED_AT_UID: Final[str] = "db-6f3763f2.tbl001.col025"
            APPROVED_AT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col025",
                name="approved_at",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: endpoint (UID: db-6f3763f2.tbl001.col026)
            ENDPOINT: Final[str] = "endpoint"
            ENDPOINT_UID: Final[str] = "db-6f3763f2.tbl001.col026"
            ENDPOINT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col026",
                name="endpoint",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: docstring (UID: db-6f3763f2.tbl001.col027)
            DOCSTRING: Final[str] = "docstring"
            DOCSTRING_UID: Final[str] = "db-6f3763f2.tbl001.col027"
            DOCSTRING_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col027",
                name="docstring",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: complexity_score (UID: db-6f3763f2.tbl001.col028)
            COMPLEXITY_SCORE: Final[str] = "complexity_score"
            COMPLEXITY_SCORE_UID: Final[str] = "db-6f3763f2.tbl001.col028"
            COMPLEXITY_SCORE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col028",
                name="complexity_score",
                table_uid="db-6f3763f2.tbl001",
                col_type="INTEGER"
            )
            
            # Column: checksum (UID: db-6f3763f2.tbl001.col029)
            CHECKSUM: Final[str] = "checksum"
            CHECKSUM_UID: Final[str] = "db-6f3763f2.tbl001.col029"
            CHECKSUM_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col029",
                name="checksum",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: code_signature (UID: db-6f3763f2.tbl001.col030)
            CODE_SIGNATURE: Final[str] = "code_signature"
            CODE_SIGNATURE_UID: Final[str] = "db-6f3763f2.tbl001.col030"
            CODE_SIGNATURE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col030",
                name="code_signature",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: signature_metadata (UID: db-6f3763f2.tbl001.col031)
            SIGNATURE_METADATA: Final[str] = "signature_metadata"
            SIGNATURE_METADATA_UID: Final[str] = "db-6f3763f2.tbl001.col031"
            SIGNATURE_METADATA_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col031",
                name="signature_metadata",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: content_hash (UID: db-6f3763f2.tbl001.col032)
            CONTENT_HASH: Final[str] = "content_hash"
            CONTENT_HASH_UID: Final[str] = "db-6f3763f2.tbl001.col032"
            CONTENT_HASH_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col032",
                name="content_hash",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Column: file_size (UID: db-6f3763f2.tbl001.col033)
            FILE_SIZE: Final[str] = "file_size"
            FILE_SIZE_UID: Final[str] = "db-6f3763f2.tbl001.col033"
            FILE_SIZE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col033",
                name="file_size",
                table_uid="db-6f3763f2.tbl001",
                col_type="INTEGER"
            )
            
            # Column: last_verified_date (UID: db-6f3763f2.tbl001.col034)
            LAST_VERIFIED_DATE: Final[str] = "last_verified_date"
            LAST_VERIFIED_DATE_UID: Final[str] = "db-6f3763f2.tbl001.col034"
            LAST_VERIFIED_DATE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl001.col034",
                name="last_verified_date",
                table_uid="db-6f3763f2.tbl001",
                col_type="TEXT"
            )
            
            # Utility lists for iteration
            ALL_NAMES: Final[tuple] = ('asset_id', 'asset_uid', 'symbol_fqn', 'asset_name', 'asset_type', 'file_path', 'line_number', 'module_path', 'logical_name', 'status', 'created_at', 'updated_at', 'session_id', 'notes', 'parent_name', 'component', 'module_alias', 'signature', 'description', 'asset_hash', 'discovered_by', 'discovered_at', 'last_modified', 'approved_by', 'approved_at', 'endpoint', 'docstring', 'complexity_score', 'checksum', 'code_signature', 'signature_metadata', 'content_hash', 'file_size', 'last_verified_date')
            ALL_UIDS: Final[tuple] = ('db-6f3763f2.tbl001.col001', 'db-6f3763f2.tbl001.col002', 'db-6f3763f2.tbl001.col003', 'db-6f3763f2.tbl001.col004', 'db-6f3763f2.tbl001.col005', 'db-6f3763f2.tbl001.col006', 'db-6f3763f2.tbl001.col007', 'db-6f3763f2.tbl001.col008', 'db-6f3763f2.tbl001.col009', 'db-6f3763f2.tbl001.col010', 'db-6f3763f2.tbl001.col011', 'db-6f3763f2.tbl001.col012', 'db-6f3763f2.tbl001.col013', 'db-6f3763f2.tbl001.col014', 'db-6f3763f2.tbl001.col015', 'db-6f3763f2.tbl001.col016', 'db-6f3763f2.tbl001.col017', 'db-6f3763f2.tbl001.col018', 'db-6f3763f2.tbl001.col019', 'db-6f3763f2.tbl001.col020', 'db-6f3763f2.tbl001.col021', 'db-6f3763f2.tbl001.col022', 'db-6f3763f2.tbl001.col023', 'db-6f3763f2.tbl001.col024', 'db-6f3763f2.tbl001.col025', 'db-6f3763f2.tbl001.col026', 'db-6f3763f2.tbl001.col027', 'db-6f3763f2.tbl001.col028', 'db-6f3763f2.tbl001.col029', 'db-6f3763f2.tbl001.col030', 'db-6f3763f2.tbl001.col031', 'db-6f3763f2.tbl001.col032', 'db-6f3763f2.tbl001.col033', 'db-6f3763f2.tbl001.col034')
            ALL_REFS: Final[tuple] = (ASSET_ID_REF, ASSET_UID_REF, SYMBOL_FQN_REF, ASSET_NAME_REF, ASSET_TYPE_REF, FILE_PATH_REF, LINE_NUMBER_REF, MODULE_PATH_REF, LOGICAL_NAME_REF, STATUS_REF, CREATED_AT_REF, UPDATED_AT_REF, SESSION_ID_REF, NOTES_REF, PARENT_NAME_REF, COMPONENT_REF, MODULE_ALIAS_REF, SIGNATURE_REF, DESCRIPTION_REF, ASSET_HASH_REF, DISCOVERED_BY_REF, DISCOVERED_AT_REF, LAST_MODIFIED_REF, APPROVED_BY_REF, APPROVED_AT_REF, ENDPOINT_REF, DOCSTRING_REF, COMPLEXITY_SCORE_REF, CHECKSUM_REF, CODE_SIGNATURE_REF, SIGNATURE_METADATA_REF, CONTENT_HASH_REF, FILE_SIZE_REF, LAST_VERIFIED_DATE_REF)

    # ------------------------------------------------------------------------
    # TABLE: relationships (UID: db-6f3763f2.tbl004)
    # ------------------------------------------------------------------------
    
    class Relationships:
        """
        Relationships between assets
        
        UID: db-6f3763f2.tbl004 (IMMUTABLE)
        Physical Name: relationships (renameable)
        Primary Key: relationship_id
        Columns: 6
        """
        
        TABLE_UID: Final[str] = "db-6f3763f2.tbl004"
        TABLE_NAME: Final[str] = "relationships"
        PRIMARY_KEY: Final[str] = "relationship_id"
        
        REF: Final[TableRef] = TableRef(
            uid="db-6f3763f2.tbl004",
            name="relationships",
            db_uid="db-6f3763f2",
            primary_key="relationship_id"
        )
        
        class Cols:
            """Column identifiers for relationships table"""
            
            # Column: relationship_id (UID: db-6f3763f2.tbl004.col101)
            RELATIONSHIP_ID: Final[str] = "relationship_id"
            RELATIONSHIP_ID_UID: Final[str] = "db-6f3763f2.tbl004.col101"
            RELATIONSHIP_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl004.col101",
                name="relationship_id",
                table_uid="db-6f3763f2.tbl004",
                col_type="INTEGER"
            )
            
            # Column: source_uid (UID: db-6f3763f2.tbl004.col102)
            SOURCE_UID: Final[str] = "source_uid"
            SOURCE_UID_UID: Final[str] = "db-6f3763f2.tbl004.col102"
            SOURCE_UID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl004.col102",
                name="source_uid",
                table_uid="db-6f3763f2.tbl004",
                col_type="TEXT"
            )
            
            # Column: target_uid (UID: db-6f3763f2.tbl004.col103)
            TARGET_UID: Final[str] = "target_uid"
            TARGET_UID_UID: Final[str] = "db-6f3763f2.tbl004.col103"
            TARGET_UID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl004.col103",
                name="target_uid",
                table_uid="db-6f3763f2.tbl004",
                col_type="TEXT"
            )
            
            # Column: relationship_type (UID: db-6f3763f2.tbl004.col104)
            RELATIONSHIP_TYPE: Final[str] = "relationship_type"
            RELATIONSHIP_TYPE_UID: Final[str] = "db-6f3763f2.tbl004.col104"
            RELATIONSHIP_TYPE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl004.col104",
                name="relationship_type",
                table_uid="db-6f3763f2.tbl004",
                col_type="TEXT"
            )
            
            # Column: created_at (UID: db-6f3763f2.tbl004.col105)
            CREATED_AT: Final[str] = "created_at"
            CREATED_AT_UID: Final[str] = "db-6f3763f2.tbl004.col105"
            CREATED_AT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl004.col105",
                name="created_at",
                table_uid="db-6f3763f2.tbl004",
                col_type="TEXT"
            )
            
            # Column: session_id (UID: db-6f3763f2.tbl004.col106)
            SESSION_ID: Final[str] = "session_id"
            SESSION_ID_UID: Final[str] = "db-6f3763f2.tbl004.col106"
            SESSION_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl004.col106",
                name="session_id",
                table_uid="db-6f3763f2.tbl004",
                col_type="TEXT"
            )
            
            # Utility lists for iteration
            ALL_NAMES: Final[tuple] = ('relationship_id', 'source_uid', 'target_uid', 'relationship_type', 'created_at', 'session_id')
            ALL_UIDS: Final[tuple] = ('db-6f3763f2.tbl004.col101', 'db-6f3763f2.tbl004.col102', 'db-6f3763f2.tbl004.col103', 'db-6f3763f2.tbl004.col104', 'db-6f3763f2.tbl004.col105', 'db-6f3763f2.tbl004.col106')
            ALL_REFS: Final[tuple] = (RELATIONSHIP_ID_REF, SOURCE_UID_REF, TARGET_UID_REF, RELATIONSHIP_TYPE_REF, CREATED_AT_REF, SESSION_ID_REF)

    # ------------------------------------------------------------------------
    # TABLE: asset_dependencies (UID: db-6f3763f2.tbl005)
    # ------------------------------------------------------------------------
    
    class AssetDependencies:
        """
        Low-level call graph edges from AST analysis
        
        UID: db-6f3763f2.tbl005 (IMMUTABLE)
        Physical Name: asset_dependencies (renameable)
        Primary Key: dependency_id
        Columns: 11
        """
        
        TABLE_UID: Final[str] = "db-6f3763f2.tbl005"
        TABLE_NAME: Final[str] = "asset_dependencies"
        PRIMARY_KEY: Final[str] = "dependency_id"
        
        REF: Final[TableRef] = TableRef(
            uid="db-6f3763f2.tbl005",
            name="asset_dependencies",
            db_uid="db-6f3763f2",
            primary_key="dependency_id"
        )
        
        class Cols:
            """Column identifiers for asset_dependencies table"""
            
            # Column: dependency_id (UID: db-6f3763f2.tbl005.col501)
            DEPENDENCY_ID: Final[str] = "dependency_id"
            DEPENDENCY_ID_UID: Final[str] = "db-6f3763f2.tbl005.col501"
            DEPENDENCY_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col501",
                name="dependency_id",
                table_uid="db-6f3763f2.tbl005",
                col_type="INTEGER"
            )
            
            # Column: source_asset_id (UID: db-6f3763f2.tbl005.col502)
            SOURCE_ASSET_ID: Final[str] = "source_asset_id"
            SOURCE_ASSET_ID_UID: Final[str] = "db-6f3763f2.tbl005.col502"
            SOURCE_ASSET_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col502",
                name="source_asset_id",
                table_uid="db-6f3763f2.tbl005",
                col_type="INTEGER"
            )
            
            # Column: target_asset_id (UID: db-6f3763f2.tbl005.col503)
            TARGET_ASSET_ID: Final[str] = "target_asset_id"
            TARGET_ASSET_ID_UID: Final[str] = "db-6f3763f2.tbl005.col503"
            TARGET_ASSET_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col503",
                name="target_asset_id",
                table_uid="db-6f3763f2.tbl005",
                col_type="INTEGER"
            )
            
            # Column: dependency_type (UID: db-6f3763f2.tbl005.col504)
            DEPENDENCY_TYPE: Final[str] = "dependency_type"
            DEPENDENCY_TYPE_UID: Final[str] = "db-6f3763f2.tbl005.col504"
            DEPENDENCY_TYPE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col504",
                name="dependency_type",
                table_uid="db-6f3763f2.tbl005",
                col_type="TEXT"
            )
            
            # Column: relationship_type (UID: db-6f3763f2.tbl005.col505)
            RELATIONSHIP_TYPE: Final[str] = "relationship_type"
            RELATIONSHIP_TYPE_UID: Final[str] = "db-6f3763f2.tbl005.col505"
            RELATIONSHIP_TYPE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col505",
                name="relationship_type",
                table_uid="db-6f3763f2.tbl005",
                col_type="TEXT"
            )
            
            # Column: call_path (UID: db-6f3763f2.tbl005.col506)
            CALL_PATH: Final[str] = "call_path"
            CALL_PATH_UID: Final[str] = "db-6f3763f2.tbl005.col506"
            CALL_PATH_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col506",
                name="call_path",
                table_uid="db-6f3763f2.tbl005",
                col_type="TEXT"
            )
            
            # Column: notes (UID: db-6f3763f2.tbl005.col507)
            NOTES: Final[str] = "notes"
            NOTES_UID: Final[str] = "db-6f3763f2.tbl005.col507"
            NOTES_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col507",
                name="notes",
                table_uid="db-6f3763f2.tbl005",
                col_type="TEXT"
            )
            
            # Column: created_at (UID: db-6f3763f2.tbl005.col508)
            CREATED_AT: Final[str] = "created_at"
            CREATED_AT_UID: Final[str] = "db-6f3763f2.tbl005.col508"
            CREATED_AT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col508",
                name="created_at",
                table_uid="db-6f3763f2.tbl005",
                col_type="TIMESTAMP"
            )
            
            # Column: asset_id (UID: db-6f3763f2.tbl005.col509)
            ASSET_ID: Final[str] = "asset_id"
            ASSET_ID_UID: Final[str] = "db-6f3763f2.tbl005.col509"
            ASSET_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col509",
                name="asset_id",
                table_uid="db-6f3763f2.tbl005",
                col_type="INTEGER"
            )
            
            # Column: depends_on_asset_id (UID: db-6f3763f2.tbl005.col510)
            DEPENDS_ON_ASSET_ID: Final[str] = "depends_on_asset_id"
            DEPENDS_ON_ASSET_ID_UID: Final[str] = "db-6f3763f2.tbl005.col510"
            DEPENDS_ON_ASSET_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col510",
                name="depends_on_asset_id",
                table_uid="db-6f3763f2.tbl005",
                col_type="INTEGER"
            )
            
            # Column: call_metadata (UID: db-6f3763f2.tbl005.col511)
            CALL_METADATA: Final[str] = "call_metadata"
            CALL_METADATA_UID: Final[str] = "db-6f3763f2.tbl005.col511"
            CALL_METADATA_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl005.col511",
                name="call_metadata",
                table_uid="db-6f3763f2.tbl005",
                col_type="TEXT"
            )
            
            # Utility lists for iteration
            ALL_NAMES: Final[tuple] = ('dependency_id', 'source_asset_id', 'target_asset_id', 'dependency_type', 'relationship_type', 'call_path', 'notes', 'created_at', 'asset_id', 'depends_on_asset_id', 'call_metadata')
            ALL_UIDS: Final[tuple] = ('db-6f3763f2.tbl005.col501', 'db-6f3763f2.tbl005.col502', 'db-6f3763f2.tbl005.col503', 'db-6f3763f2.tbl005.col504', 'db-6f3763f2.tbl005.col505', 'db-6f3763f2.tbl005.col506', 'db-6f3763f2.tbl005.col507', 'db-6f3763f2.tbl005.col508', 'db-6f3763f2.tbl005.col509', 'db-6f3763f2.tbl005.col510', 'db-6f3763f2.tbl005.col511')
            ALL_REFS: Final[tuple] = (DEPENDENCY_ID_REF, SOURCE_ASSET_ID_REF, TARGET_ASSET_ID_REF, DEPENDENCY_TYPE_REF, RELATIONSHIP_TYPE_REF, CALL_PATH_REF, NOTES_REF, CREATED_AT_REF, ASSET_ID_REF, DEPENDS_ON_ASSET_ID_REF, CALL_METADATA_REF)

    # ------------------------------------------------------------------------
    # TABLE: session_transactions (UID: db-6f3763f2.tbl013)
    # ------------------------------------------------------------------------
    
    class SessionTransactions:
        """
        Session audit trail
        
        UID: db-6f3763f2.tbl013 (IMMUTABLE)
        Physical Name: session_transactions (renameable)
        Primary Key: session_id
        Columns: 5
        """
        
        TABLE_UID: Final[str] = "db-6f3763f2.tbl013"
        TABLE_NAME: Final[str] = "session_transactions"
        PRIMARY_KEY: Final[str] = "session_id"
        
        REF: Final[TableRef] = TableRef(
            uid="db-6f3763f2.tbl013",
            name="session_transactions",
            db_uid="db-6f3763f2",
            primary_key="session_id"
        )
        
        class Cols:
            """Column identifiers for session_transactions table"""
            
            # Column: session_id (UID: db-6f3763f2.tbl013.col201)
            SESSION_ID: Final[str] = "session_id"
            SESSION_ID_UID: Final[str] = "db-6f3763f2.tbl013.col201"
            SESSION_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl013.col201",
                name="session_id",
                table_uid="db-6f3763f2.tbl013",
                col_type="TEXT"
            )
            
            # Column: start_timestamp (UID: db-6f3763f2.tbl013.col202)
            START_TIMESTAMP: Final[str] = "start_timestamp"
            START_TIMESTAMP_UID: Final[str] = "db-6f3763f2.tbl013.col202"
            START_TIMESTAMP_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl013.col202",
                name="start_timestamp",
                table_uid="db-6f3763f2.tbl013",
                col_type="TEXT"
            )
            
            # Column: end_timestamp (UID: db-6f3763f2.tbl013.col203)
            END_TIMESTAMP: Final[str] = "end_timestamp"
            END_TIMESTAMP_UID: Final[str] = "db-6f3763f2.tbl013.col203"
            END_TIMESTAMP_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl013.col203",
                name="end_timestamp",
                table_uid="db-6f3763f2.tbl013",
                col_type="TEXT"
            )
            
            # Column: os_user (UID: db-6f3763f2.tbl013.col204)
            OS_USER: Final[str] = "os_user"
            OS_USER_UID: Final[str] = "db-6f3763f2.tbl013.col204"
            OS_USER_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl013.col204",
                name="os_user",
                table_uid="db-6f3763f2.tbl013",
                col_type="TEXT"
            )
            
            # Column: host (UID: db-6f3763f2.tbl013.col205)
            HOST: Final[str] = "host"
            HOST_UID: Final[str] = "db-6f3763f2.tbl013.col205"
            HOST_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl013.col205",
                name="host",
                table_uid="db-6f3763f2.tbl013",
                col_type="TEXT"
            )
            
            # Utility lists for iteration
            ALL_NAMES: Final[tuple] = ('session_id', 'start_timestamp', 'end_timestamp', 'os_user', 'host')
            ALL_UIDS: Final[tuple] = ('db-6f3763f2.tbl013.col201', 'db-6f3763f2.tbl013.col202', 'db-6f3763f2.tbl013.col203', 'db-6f3763f2.tbl013.col204', 'db-6f3763f2.tbl013.col205')
            ALL_REFS: Final[tuple] = (SESSION_ID_REF, START_TIMESTAMP_REF, END_TIMESTAMP_REF, OS_USER_REF, HOST_REF)

    # ------------------------------------------------------------------------
    # TABLE: qc_results (UID: db-6f3763f2.tbl009)
    # ------------------------------------------------------------------------
    
    class QcResults:
        """
        Quality control run results
        
        UID: db-6f3763f2.tbl009 (IMMUTABLE)
        Physical Name: qc_results (renameable)
        Primary Key: qc_id
        Columns: 7
        """
        
        TABLE_UID: Final[str] = "db-6f3763f2.tbl009"
        TABLE_NAME: Final[str] = "qc_results"
        PRIMARY_KEY: Final[str] = "qc_id"
        
        REF: Final[TableRef] = TableRef(
            uid="db-6f3763f2.tbl009",
            name="qc_results",
            db_uid="db-6f3763f2",
            primary_key="qc_id"
        )
        
        class Cols:
            """Column identifiers for qc_results table"""
            
            # Column: qc_id (UID: db-6f3763f2.tbl009.col301)
            QC_ID: Final[str] = "qc_id"
            QC_ID_UID: Final[str] = "db-6f3763f2.tbl009.col301"
            QC_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl009.col301",
                name="qc_id",
                table_uid="db-6f3763f2.tbl009",
                col_type="INTEGER"
            )
            
            # Column: asset_uid (UID: db-6f3763f2.tbl009.col302)
            ASSET_UID: Final[str] = "asset_uid"
            ASSET_UID_UID: Final[str] = "db-6f3763f2.tbl009.col302"
            ASSET_UID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl009.col302",
                name="asset_uid",
                table_uid="db-6f3763f2.tbl009",
                col_type="TEXT"
            )
            
            # Column: rule_id (UID: db-6f3763f2.tbl009.col303)
            RULE_ID: Final[str] = "rule_id"
            RULE_ID_UID: Final[str] = "db-6f3763f2.tbl009.col303"
            RULE_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl009.col303",
                name="rule_id",
                table_uid="db-6f3763f2.tbl009",
                col_type="TEXT"
            )
            
            # Column: result (UID: db-6f3763f2.tbl009.col304)
            RESULT: Final[str] = "result"
            RESULT_UID: Final[str] = "db-6f3763f2.tbl009.col304"
            RESULT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl009.col304",
                name="result",
                table_uid="db-6f3763f2.tbl009",
                col_type="TEXT"
            )
            
            # Column: message (UID: db-6f3763f2.tbl009.col305)
            MESSAGE: Final[str] = "message"
            MESSAGE_UID: Final[str] = "db-6f3763f2.tbl009.col305"
            MESSAGE_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl009.col305",
                name="message",
                table_uid="db-6f3763f2.tbl009",
                col_type="TEXT"
            )
            
            # Column: created_at (UID: db-6f3763f2.tbl009.col306)
            CREATED_AT: Final[str] = "created_at"
            CREATED_AT_UID: Final[str] = "db-6f3763f2.tbl009.col306"
            CREATED_AT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl009.col306",
                name="created_at",
                table_uid="db-6f3763f2.tbl009",
                col_type="TEXT"
            )
            
            # Column: session_id (UID: db-6f3763f2.tbl009.col307)
            SESSION_ID: Final[str] = "session_id"
            SESSION_ID_UID: Final[str] = "db-6f3763f2.tbl009.col307"
            SESSION_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl009.col307",
                name="session_id",
                table_uid="db-6f3763f2.tbl009",
                col_type="TEXT"
            )
            
            # Utility lists for iteration
            ALL_NAMES: Final[tuple] = ('qc_id', 'asset_uid', 'rule_id', 'result', 'message', 'created_at', 'session_id')
            ALL_UIDS: Final[tuple] = ('db-6f3763f2.tbl009.col301', 'db-6f3763f2.tbl009.col302', 'db-6f3763f2.tbl009.col303', 'db-6f3763f2.tbl009.col304', 'db-6f3763f2.tbl009.col305', 'db-6f3763f2.tbl009.col306', 'db-6f3763f2.tbl009.col307')
            ALL_REFS: Final[tuple] = (QC_ID_REF, ASSET_UID_REF, RULE_ID_REF, RESULT_REF, MESSAGE_REF, CREATED_AT_REF, SESSION_ID_REF)

    # ------------------------------------------------------------------------
    # TABLE: schema_metadata (UID: db-6f3763f2.tbl012)
    # ------------------------------------------------------------------------
    
    class SchemaMetadata:
        """
        Schema version tracking
        
        UID: db-6f3763f2.tbl012 (IMMUTABLE)
        Physical Name: schema_metadata (renameable)
        Primary Key: meta_id
        Columns: 3
        """
        
        TABLE_UID: Final[str] = "db-6f3763f2.tbl012"
        TABLE_NAME: Final[str] = "schema_metadata"
        PRIMARY_KEY: Final[str] = "meta_id"
        
        REF: Final[TableRef] = TableRef(
            uid="db-6f3763f2.tbl012",
            name="schema_metadata",
            db_uid="db-6f3763f2",
            primary_key="meta_id"
        )
        
        class Cols:
            """Column identifiers for schema_metadata table"""
            
            # Column: meta_id (UID: db-6f3763f2.tbl012.col401)
            META_ID: Final[str] = "meta_id"
            META_ID_UID: Final[str] = "db-6f3763f2.tbl012.col401"
            META_ID_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl012.col401",
                name="meta_id",
                table_uid="db-6f3763f2.tbl012",
                col_type="INTEGER"
            )
            
            # Column: schema_version (UID: db-6f3763f2.tbl012.col402)
            SCHEMA_VERSION: Final[str] = "schema_version"
            SCHEMA_VERSION_UID: Final[str] = "db-6f3763f2.tbl012.col402"
            SCHEMA_VERSION_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl012.col402",
                name="schema_version",
                table_uid="db-6f3763f2.tbl012",
                col_type="TEXT"
            )
            
            # Column: applied_at (UID: db-6f3763f2.tbl012.col403)
            APPLIED_AT: Final[str] = "applied_at"
            APPLIED_AT_UID: Final[str] = "db-6f3763f2.tbl012.col403"
            APPLIED_AT_REF: Final[ColRef] = ColRef(
                uid="db-6f3763f2.tbl012.col403",
                name="applied_at",
                table_uid="db-6f3763f2.tbl012",
                col_type="TEXT"
            )
            
            # Utility lists for iteration
            ALL_NAMES: Final[tuple] = ('meta_id', 'schema_version', 'applied_at')
            ALL_UIDS: Final[tuple] = ('db-6f3763f2.tbl012.col401', 'db-6f3763f2.tbl012.col402', 'db-6f3763f2.tbl012.col403')
            ALL_REFS: Final[tuple] = (META_ID_REF, SCHEMA_VERSION_REF, APPLIED_AT_REF)

# ============================================================================
# SYNC VERIFICATION
# ===================================================================================================

def verify_sync() -> None:
    """
    Verify that generated schema_ids.py is in sync with current manifest.
    
    Called automatically on import (fail fast).
    Checks manifest hash and retired UIDs.
    
    Raises:
        RuntimeError: If bindings are out of sync or retired UID in use
    """
    import hashlib
    import json
    from pathlib import Path
    
    # Use three-tier system for manifest reading.
    # host_only=True: this function runs at import time. If a workspace session
    # points to a peer project, locate_project_root() Priority 3 would return
    # the peer root, causing the host hash to be compared against the peer
    # manifest. host_only=True skips Priority 3 (session context) and resolves
    # deterministically against the host project root via Priority 3.5.
    try:
        from utils.manifest_io import read_manifest_bytes
        manifest_bytes = read_manifest_bytes(host_only=True)
    except ImportError:
        # Fallback for compatibility (if three-tier not available)
        manifest_path = Path('project_manifest.json')
        if not manifest_path.exists():
            raise RuntimeError(
                "[ERROR] Manifest not found: project_manifest.json\n"
                "   Schema bindings cannot be verified."
            )
        with open(manifest_path, 'rb') as f:
            manifest_bytes = f.read()
    
    current_hash = hashlib.sha256(manifest_bytes).hexdigest()
    
    if current_hash != MANIFEST_HASH:
        raise RuntimeError(
            f"[ERROR] Schema bindings out of sync!\n"
            f"   Expected manifest hash: {MANIFEST_HASH[:16]}...\n"
            f"   Current manifest hash:  {current_hash[:16]}...\n"
            f"\n"
            f"FIX: Regenerate bindings:\n"
            f"   python scripts/manifest_manager.py --export"
        )


def _collect_active_uids() -> set:
    """Collect all active UIDs from this generated file for validation"""
    # This is a simplified version - actual implementation would inspect
    # the generated classes dynamically
    return set()


# Auto-verify on import (fail fast)
verify_sync()