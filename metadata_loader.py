"""
Metadata Loader with Supply-Chain Security
Implements fail-fast validation with version pinning, checksum verification, and schema validation
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logging.warning("jsonschema not available - schema validation disabled")


logger = logging.getLogger(__name__)


class MetadataError(Exception):
    """Base exception for metadata errors"""
    pass


class MetadataVersionError(MetadataError):
    """Version mismatch error"""
    def __init__(self, expected: str, actual: str, file_path: str):
        self.expected = expected
        self.actual = actual
        self.file_path = file_path
        super().__init__(
            f"Version mismatch in {file_path}: expected {expected}, got {actual}"
        )


class MetadataIntegrityError(MetadataError):
    """Checksum/integrity violation error"""
    def __init__(self, file_path: str, expected_checksum: Optional[str] = None, actual_checksum: Optional[str] = None):
        self.file_path = file_path
        self.expected_checksum = expected_checksum
        self.actual_checksum = actual_checksum
        msg = f"Integrity violation in {file_path}"
        if expected_checksum and actual_checksum:
            msg += f": expected checksum {expected_checksum}, got {actual_checksum}"
        super().__init__(msg)


class MetadataSchemaError(MetadataError):
    """Schema validation error"""
    def __init__(self, file_path: str, validation_errors: list):
        self.file_path = file_path
        self.validation_errors = validation_errors
        error_msgs = '\n'.join(f"  - {err}" for err in validation_errors)
        super().__init__(
            f"Schema validation failed for {file_path}:\n{error_msgs}"
        )


class MetadataMissingKeyError(MetadataError):
    """Required key missing in metadata"""
    def __init__(self, file_path: str, missing_key: str, context: str = ""):
        self.file_path = file_path
        self.missing_key = missing_key
        self.context = context
        msg = f"Required key '{missing_key}' missing in {file_path}"
        if context:
            msg += f" ({context})"
        super().__init__(msg)


class MetadataLoader:
    """
    Unified metadata loader with strict validation
    
    Features:
    - Version pinning with semantic versioning
    - SHA-256 checksum verification
    - JSON Schema validation
    - Fail-fast on any violation
    - Structured logging of all errors
    """
    
    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.schemas_dir = self.workspace_root / "schemas"
        
        # Loaded schemas cache
        self._schema_cache: Dict[str, Dict] = {}
    
    def load_and_validate_metadata(
        self,
        path: Path,
        schema_ref: Optional[str] = None,
        required_version: Optional[str] = None,
        expected_checksum: Optional[str] = None,
        checksum_algorithm: str = "sha256"
    ) -> Dict[str, Any]:
        """
        Load and validate metadata file with all safeguards
        
        Args:
            path: Path to metadata file (JSON or YAML)
            schema_ref: Schema file name (e.g., "rubric.schema.json")
            required_version: Required version string (e.g., "2.0.0")
            expected_checksum: Expected SHA-256 checksum (hex)
            checksum_algorithm: Hash algorithm ("sha256", "md5")
        
        Returns:
            Validated metadata dictionary
        
        Raises:
            MetadataVersionError: Version mismatch
            MetadataIntegrityError: Checksum mismatch
            MetadataSchemaError: Schema validation failure
            MetadataMissingKeyError: Required key missing
        """
        
        # 1. Load file
        metadata = self._load_file(path)
        
        # 2. Version check
        if required_version:
            actual_version = metadata.get("version")
            if not actual_version:
                raise MetadataMissingKeyError(str(path), "version", "version field required")
            
            if actual_version != required_version:
                self._log_error(
                    rule_id="VERSION_MISMATCH",
                    file_path=str(path),
                    expected=required_version,
                    actual=actual_version
                )
                raise MetadataVersionError(required_version, actual_version, str(path))
            
            logger.info(f"✓ Version validated: {path.name} v{actual_version}")
        
        # 3. Checksum verification
        if expected_checksum:
            actual_checksum = self._calculate_checksum(metadata, checksum_algorithm)
            
            if actual_checksum != expected_checksum:
                self._log_error(
                    rule_id="CHECKSUM_MISMATCH",
                    file_path=str(path),
                    expected=expected_checksum,
                    actual=actual_checksum
                )
                raise MetadataIntegrityError(str(path), expected_checksum, actual_checksum)
            
            logger.info(f"✓ Checksum validated: {path.name} ({checksum_algorithm})")
        
        # 4. Schema validation
        if schema_ref and JSONSCHEMA_AVAILABLE:
            schema = self._load_schema(schema_ref)
            errors = self._validate_schema(metadata, schema)
            
            if errors:
                self._log_error(
                    rule_id="SCHEMA_VALIDATION_FAILED",
                    file_path=str(path),
                    errors=errors
                )
                raise MetadataSchemaError(str(path), errors)
            
            logger.info(f"✓ Schema validated: {path.name}")
        
        return metadata
    
    def _load_file(self, path: Path) -> Dict[str, Any]:
        """Load JSON or YAML file"""
        if not path.exists():
            raise FileNotFoundError(f"Metadata file not found: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if path.suffix in ['.json']:
                return json.loads(content)
            elif path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(content)
            else:
                raise ValueError(f"Unsupported file type: {path.suffix}")
        
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise MetadataError(f"Failed to parse {path}: {e}")
    
    def _calculate_checksum(self, metadata: Dict[str, Any], algorithm: str = "sha256") -> str:
        """
        Calculate reproducible checksum of metadata
        
        Normalization:
        - JSON serialization with sorted keys
        - UTF-8 encoding
        - No whitespace variations
        """
        normalized = json.dumps(metadata, sort_keys=True, separators=(',', ':'))
        
        if algorithm == "sha256":
            return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        elif algorithm == "md5":
            return hashlib.md5(normalized.encode('utf-8')).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def _load_schema(self, schema_ref: str) -> Dict[str, Any]:
        """Load JSON Schema from schemas directory"""
        if schema_ref in self._schema_cache:
            return self._schema_cache[schema_ref]
        
        schema_path = self.schemas_dir / schema_ref
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        self._schema_cache[schema_ref] = schema
        return schema
    
    def _validate_schema(self, metadata: Dict[str, Any], schema: Dict[str, Any]) -> list:
        """Validate metadata against JSON Schema"""
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema not available - skipping schema validation")
            return []
        
        # Import check for type checker
        import jsonschema as js
        validator = js.Draft7Validator(schema)
        errors = []
        
        for error in validator.iter_errors(metadata):
            error_path = '.'.join(str(p) for p in error.path) if error.path else 'root'
            errors.append(f"{error_path}: {error.message}")
        
        return errors
    
    def _log_error(self, rule_id: str, file_path: str, **kwargs):
        """Structured error logging"""
        from datetime import datetime, timezone
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "rule_id": rule_id,
            "file_path": file_path,
            **kwargs
        }
        
        logger.error(json.dumps(log_entry, indent=2))


def load_cuestionario(
    path: Optional[Path] = None,
    required_version: str = "2.0.0"
) -> Dict[str, Any]:
    """
    Load and validate cuestionario_FIXED.json
    
    Args:
        path: Path to cuestionario file (default: cuestionario_FIXED.json)
        required_version: Required version
    
    Returns:
        Validated cuestionario data
    """
    if path is None:
        path = Path.cwd() / "cuestionario_FIXED.json"
    
    loader = MetadataLoader()
    return loader.load_and_validate_metadata(
        path=path,
        schema_ref=None,  # TODO: Create cuestionario schema
        required_version=required_version
    )


def load_execution_mapping(
    path: Optional[Path] = None,
    required_version: str = "2.0.0"
) -> Dict[str, Any]:
    """
    Load and validate execution_mapping.yaml
    
    Args:
        path: Path to execution mapping (default: execution_mapping.yaml)
        required_version: Required version
    
    Returns:
        Validated execution mapping
    """
    if path is None:
        path = Path.cwd() / "execution_mapping.yaml"
    
    loader = MetadataLoader()
    return loader.load_and_validate_metadata(
        path=path,
        schema_ref="execution_mapping.schema.json",
        required_version=required_version
    )


def load_rubric_scoring(
    path: Optional[Path] = None,
    required_version: str = "2.0.0"
) -> Dict[str, Any]:
    """
    Load and validate rubric_scoring.json
    
    Args:
        path: Path to rubric scoring (default: rubric_scoring.json)
        required_version: Required version
    
    Returns:
        Validated rubric scoring configuration
    """
    if path is None:
        path = Path.cwd() / "rubric_scoring.json"
    
    loader = MetadataLoader()
    return loader.load_and_validate_metadata(
        path=path,
        schema_ref="rubric.schema.json",
        required_version=required_version
    )
