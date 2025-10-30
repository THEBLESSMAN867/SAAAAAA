"""
Aggregation Module - Hierarchical Score Aggregation System

This module implements the complete aggregation pipeline for the policy analysis system:
- FASE 4: Dimension aggregation (60 dimensions: 6 × 10 policy areas)
- FASE 5: Policy area aggregation (10 areas)
- FASE 6: Cluster aggregation (4 MESO questions)
- FASE 7: Macro evaluation (1 holistic question)

Requirements:
- Validation of weights, thresholds, and hermeticity
- Comprehensive logging and abortability at each level
- No strategic simplification
- Full alignment with monolith specifications

Architecture:
- DimensionAggregator: Aggregates 5 micro questions → 1 dimension score
- AreaPolicyAggregator: Aggregates 6 dimension scores → 1 area score
- ClusterAggregator: Aggregates multiple area scores → 1 cluster score
- MacroAggregator: Aggregates all cluster scores → 1 holistic evaluation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ScoredResult:
    """Scored result for a micro question."""
    question_global: int
    base_slot: str
    policy_area: str
    dimension: str
    score: float
    quality_level: str
    evidence: Dict[str, Any]
    raw_results: Dict[str, Any]


@dataclass
class DimensionScore:
    """Aggregated score for a dimension."""
    dimension_id: str
    area_id: str
    score: float
    quality_level: str
    contributing_questions: List[int]
    validation_passed: bool = True
    validation_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AreaScore:
    """Aggregated score for a policy area."""
    area_id: str
    area_name: str
    score: float
    quality_level: str
    dimension_scores: List[DimensionScore]
    validation_passed: bool = True
    validation_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterScore:
    """Aggregated score for a MESO cluster."""
    cluster_id: str
    cluster_name: str
    areas: List[str]
    score: float
    coherence: float
    area_scores: List[AreaScore]
    validation_passed: bool = True
    validation_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MacroScore:
    """Holistic macro evaluation score."""
    score: float
    quality_level: str
    cross_cutting_coherence: float
    systemic_gaps: List[str]
    strategic_alignment: float
    cluster_scores: List[ClusterScore]
    validation_passed: bool = True
    validation_details: Dict[str, Any] = field(default_factory=dict)


class AggregationError(Exception):
    """Base exception for aggregation errors."""
    pass


class ValidationError(AggregationError):
    """Raised when validation fails."""
    pass


class WeightValidationError(ValidationError):
    """Raised when weight validation fails."""
    pass


class ThresholdValidationError(ValidationError):
    """Raised when threshold validation fails."""
    pass


class HermeticityValidationError(ValidationError):
    """Raised when hermeticity validation fails."""
    pass


class CoverageError(AggregationError):
    """Raised when coverage requirements are not met."""
    pass


class DimensionAggregator:
    """
    Aggregates micro question scores into dimension scores.
    
    Responsibilities:
    - Aggregate 5 micro questions (Q1-Q5) per dimension
    - Validate weights sum to 1.0
    - Apply rubric thresholds
    - Ensure coverage (abort if insufficient)
    - Provide detailed logging
    """
    
    def __init__(self, monolith: Dict[str, Any], abort_on_insufficient: bool = True):
        """
        Initialize dimension aggregator.
        
        Args:
            monolith: Questionnaire monolith configuration
            abort_on_insufficient: Whether to abort on insufficient coverage
        """
        self.monolith = monolith
        self.abort_on_insufficient = abort_on_insufficient
        
        # Extract configuration
        self.scoring_config = monolith["blocks"]["scoring"]
        self.niveles = monolith["blocks"]["niveles_abstraccion"]
        
        logger.info("DimensionAggregator initialized")
    
    def validate_weights(self, weights: List[float]) -> Tuple[bool, str]:
        """
        Validate that weights sum to 1.0 (within tolerance).
        
        Args:
            weights: List of weights
            
        Returns:
            Tuple of (is_valid, message)
            
        Raises:
            WeightValidationError: If weights don't sum to 1.0
        """
        if not weights:
            return False, "No weights provided"
        
        weight_sum = sum(weights)
        tolerance = 1e-6
        
        if abs(weight_sum - 1.0) > tolerance:
            msg = f"Weight sum validation failed: sum={weight_sum:.6f}, expected=1.0"
            logger.error(msg)
            if self.abort_on_insufficient:
                raise WeightValidationError(msg)
            return False, msg
        
        logger.debug(f"Weight validation passed: sum={weight_sum:.6f}")
        return True, "Weights valid"
    
    def validate_coverage(
        self,
        results: List[ScoredResult],
        expected_count: int = 5
    ) -> Tuple[bool, str]:
        """
        Validate coverage requirements.
        
        Args:
            results: List of scored results
            expected_count: Expected number of results
            
        Returns:
            Tuple of (is_valid, message)
            
        Raises:
            CoverageError: If coverage is insufficient
        """
        actual_count = len(results)
        
        if actual_count < expected_count:
            msg = (
                f"Coverage validation failed: "
                f"expected {expected_count} questions, got {actual_count}"
            )
            logger.error(msg)
            if self.abort_on_insufficient:
                raise CoverageError(msg)
            return False, msg
        
        logger.debug(f"Coverage validation passed: {actual_count}/{expected_count} questions")
        return True, "Coverage sufficient"
    
    def calculate_weighted_average(
        self,
        scores: List[float],
        weights: Optional[List[float]] = None
    ) -> float:
        """
        Calculate weighted average of scores.
        
        Args:
            scores: List of scores
            weights: Optional list of weights (defaults to equal weights)
            
        Returns:
            Weighted average score
        """
        if not scores:
            return 0.0
        
        if weights is None:
            # Equal weights
            weights = [1.0 / len(scores)] * len(scores)
        
        # Validate weights
        self.validate_weights(weights)
        
        # Calculate weighted sum
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        
        logger.debug(
            f"Weighted average calculated: "
            f"scores={scores}, weights={weights}, result={weighted_sum:.4f}"
        )
        
        return weighted_sum
    
    def apply_rubric_thresholds(
        self,
        score: float,
        thresholds: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Apply rubric thresholds to determine quality level.
        
        Args:
            score: Aggregated score (0-3 range)
            thresholds: Optional threshold definitions
            
        Returns:
            Quality level (EXCELENTE, BUENO, ACEPTABLE, INSUFICIENTE)
        """
        # Clamp score to valid range [0, 3]
        clamped_score = max(0.0, min(3.0, score))
        
        # Normalize to 0-1 range
        normalized_score = clamped_score / 3.0
        
        # Apply standard thresholds
        if normalized_score >= 0.85:
            quality = "EXCELENTE"
        elif normalized_score >= 0.70:
            quality = "BUENO"
        elif normalized_score >= 0.55:
            quality = "ACEPTABLE"
        else:
            quality = "INSUFICIENTE"
        
        logger.debug(
            f"Rubric applied: score={score:.4f}, "
            f"normalized={normalized_score:.4f}, quality={quality}"
        )
        
        return quality
    
    def aggregate_dimension(
        self,
        dimension_id: str,
        area_id: str,
        scored_results: List[ScoredResult],
        weights: Optional[List[float]] = None
    ) -> DimensionScore:
        """
        Aggregate a single dimension from micro question results.
        
        Args:
            dimension_id: Dimension ID (e.g., "DIM01")
            area_id: Policy area ID (e.g., "PA01")
            scored_results: List of scored results for this dimension/area
            weights: Optional weights for questions (defaults to equal weights)
            
        Returns:
            DimensionScore with aggregated score and quality level
            
        Raises:
            ValidationError: If validation fails
            CoverageError: If coverage is insufficient
        """
        logger.info(f"Aggregating dimension {dimension_id} for area {area_id}")
        
        validation_details = {}
        
        # Filter results for this dimension/area
        dim_results = [
            r for r in scored_results
            if r.dimension == dimension_id and r.policy_area == area_id
        ]
        
        # Validate coverage
        try:
            coverage_valid, coverage_msg = self.validate_coverage(dim_results)
            validation_details["coverage"] = {
                "valid": coverage_valid,
                "message": coverage_msg,
                "count": len(dim_results)
            }
        except CoverageError as e:
            logger.error(f"Coverage validation failed for {dimension_id}/{area_id}: {e}")
            # Return minimal score if aborted
            return DimensionScore(
                dimension_id=dimension_id,
                area_id=area_id,
                score=0.0,
                quality_level="INSUFICIENTE",
                contributing_questions=[],
                validation_passed=False,
                validation_details={"error": str(e), "type": "coverage"}
            )
        
        if not dim_results:
            logger.warning(f"No results for dimension {dimension_id}/{area_id}")
            return DimensionScore(
                dimension_id=dimension_id,
                area_id=area_id,
                score=0.0,
                quality_level="INSUFICIENTE",
                contributing_questions=[],
                validation_passed=False,
                validation_details={"error": "No results", "type": "empty"}
            )
        
        # Extract scores
        scores = [r.score for r in dim_results]
        
        # Calculate weighted average
        try:
            avg_score = self.calculate_weighted_average(scores, weights)
            validation_details["weights"] = {
                "valid": True,
                "weights": weights if weights else "equal",
                "score": avg_score
            }
        except WeightValidationError as e:
            logger.error(f"Weight validation failed for {dimension_id}/{area_id}: {e}")
            return DimensionScore(
                dimension_id=dimension_id,
                area_id=area_id,
                score=0.0,
                quality_level="INSUFICIENTE",
                contributing_questions=[r.question_global for r in dim_results],
                validation_passed=False,
                validation_details={"error": str(e), "type": "weights"}
            )
        
        # Apply rubric thresholds
        quality_level = self.apply_rubric_thresholds(avg_score)
        validation_details["rubric"] = {
            "score": avg_score,
            "quality_level": quality_level
        }
        
        logger.info(
            f"✓ Dimension {dimension_id}/{area_id}: "
            f"score={avg_score:.4f}, quality={quality_level}"
        )
        
        return DimensionScore(
            dimension_id=dimension_id,
            area_id=area_id,
            score=avg_score,
            quality_level=quality_level,
            contributing_questions=[r.question_global for r in dim_results],
            validation_passed=True,
            validation_details=validation_details
        )


class AreaPolicyAggregator:
    """
    Aggregates dimension scores into policy area scores.
    
    Responsibilities:
    - Aggregate 6 dimension scores per policy area
    - Validate dimension completeness
    - Apply area-level rubric thresholds
    - Ensure hermeticity (no dimension overlap)
    """
    
    def __init__(self, monolith: Dict[str, Any], abort_on_insufficient: bool = True):
        """
        Initialize area aggregator.
        
        Args:
            monolith: Questionnaire monolith configuration
            abort_on_insufficient: Whether to abort on insufficient coverage
        """
        self.monolith = monolith
        self.abort_on_insufficient = abort_on_insufficient
        
        # Extract configuration
        self.scoring_config = monolith["blocks"]["scoring"]
        self.niveles = monolith["blocks"]["niveles_abstraccion"]
        self.policy_areas = self.niveles["policy_areas"]
        self.dimensions = self.niveles["dimensions"]
        
        logger.info("AreaPolicyAggregator initialized")
    
    def validate_hermeticity(
        self,
        dimension_scores: List[DimensionScore],
        area_id: str
    ) -> Tuple[bool, str]:
        """
        Validate hermeticity (no dimension overlap/gaps).
        
        Args:
            dimension_scores: List of dimension scores for the area
            area_id: Policy area ID
            
        Returns:
            Tuple of (is_valid, message)
            
        Raises:
            HermeticityValidationError: If hermeticity is violated
        """
        # Check that we have exactly 6 dimensions
        expected_count = len(self.dimensions)
        actual_count = len(dimension_scores)
        
        if actual_count != expected_count:
            msg = (
                f"Hermeticity violation for area {area_id}: "
                f"expected {expected_count} dimensions, got {actual_count}"
            )
            logger.error(msg)
            if self.abort_on_insufficient:
                raise HermeticityValidationError(msg)
            return False, msg
        
        # Check for duplicate dimensions
        dimension_ids = [d.dimension_id for d in dimension_scores]
        if len(dimension_ids) != len(set(dimension_ids)):
            msg = f"Hermeticity violation for area {area_id}: duplicate dimensions found"
            logger.error(msg)
            if self.abort_on_insufficient:
                raise HermeticityValidationError(msg)
            return False, msg
        
        logger.debug(f"Hermeticity validation passed for area {area_id}")
        return True, "Hermeticity validated"
    
    def normalize_scores(self, dimension_scores: List[DimensionScore]) -> List[float]:
        """
        Normalize dimension scores to 0-1 range.
        
        Args:
            dimension_scores: List of dimension scores
            
        Returns:
            List of normalized scores
        """
        normalized = [max(0.0, min(3.0, d.score)) / 3.0 for d in dimension_scores]
        logger.debug(f"Scores normalized: {normalized}")
        return normalized
    
    def apply_rubric_thresholds(
        self,
        score: float,
        thresholds: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Apply area-level rubric thresholds.
        
        Args:
            score: Aggregated score (0-3 range)
            thresholds: Optional threshold definitions
            
        Returns:
            Quality level (EXCELENTE, BUENO, ACEPTABLE, INSUFICIENTE)
        """
        # Clamp score to valid range [0, 3]
        clamped_score = max(0.0, min(3.0, score))
        
        # Normalize to 0-1 range
        normalized_score = clamped_score / 3.0
        
        # Apply standard thresholds
        if normalized_score >= 0.85:
            quality = "EXCELENTE"
        elif normalized_score >= 0.70:
            quality = "BUENO"
        elif normalized_score >= 0.55:
            quality = "ACEPTABLE"
        else:
            quality = "INSUFICIENTE"
        
        logger.debug(
            f"Area rubric applied: score={score:.4f}, "
            f"normalized={normalized_score:.4f}, quality={quality}"
        )
        
        return quality
    
    def aggregate_area(
        self,
        area_id: str,
        dimension_scores: List[DimensionScore]
    ) -> AreaScore:
        """
        Aggregate a single policy area from dimension scores.
        
        Args:
            area_id: Policy area ID (e.g., "PA01")
            dimension_scores: List of dimension scores for this area
            
        Returns:
            AreaScore with aggregated score and quality level
            
        Raises:
            ValidationError: If validation fails
        """
        logger.info(f"Aggregating policy area {area_id}")
        
        validation_details = {}
        
        # Filter dimension scores for this area
        area_dim_scores = [
            d for d in dimension_scores
            if d.area_id == area_id
        ]
        
        # Validate hermeticity
        try:
            hermetic_valid, hermetic_msg = self.validate_hermeticity(area_dim_scores, area_id)
            validation_details["hermeticity"] = {
                "valid": hermetic_valid,
                "message": hermetic_msg,
                "dimension_count": len(area_dim_scores)
            }
        except HermeticityValidationError as e:
            logger.error(f"Hermeticity validation failed for area {area_id}: {e}")
            # Get area name
            area_name = next(
                (a["i18n"]["keys"]["label_es"] for a in self.policy_areas 
                 if a["policy_area_id"] == area_id),
                area_id
            )
            return AreaScore(
                area_id=area_id,
                area_name=area_name,
                score=0.0,
                quality_level="INSUFICIENTE",
                dimension_scores=[],
                validation_passed=False,
                validation_details={"error": str(e), "type": "hermeticity"}
            )
        
        if not area_dim_scores:
            logger.warning(f"No dimension scores for area {area_id}")
            area_name = next(
                (a["i18n"]["keys"]["label_es"] for a in self.policy_areas 
                 if a["policy_area_id"] == area_id),
                area_id
            )
            return AreaScore(
                area_id=area_id,
                area_name=area_name,
                score=0.0,
                quality_level="INSUFICIENTE",
                dimension_scores=[],
                validation_passed=False,
                validation_details={"error": "No dimensions", "type": "empty"}
            )
        
        # Normalize scores
        normalized = self.normalize_scores(area_dim_scores)
        validation_details["normalization"] = {
            "original": [d.score for d in area_dim_scores],
            "normalized": normalized
        }
        
        # Calculate average score
        avg_score = sum(d.score for d in area_dim_scores) / len(area_dim_scores)
        
        # Apply rubric thresholds
        quality_level = self.apply_rubric_thresholds(avg_score)
        validation_details["rubric"] = {
            "score": avg_score,
            "quality_level": quality_level
        }
        
        # Get area name
        area_name = next(
            (a["i18n"]["keys"]["label_es"] for a in self.policy_areas 
             if a["policy_area_id"] == area_id),
            area_id
        )
        
        logger.info(
            f"✓ Policy area {area_id} ({area_name}): "
            f"score={avg_score:.4f}, quality={quality_level}"
        )
        
        return AreaScore(
            area_id=area_id,
            area_name=area_name,
            score=avg_score,
            quality_level=quality_level,
            dimension_scores=area_dim_scores,
            validation_passed=True,
            validation_details=validation_details
        )


class ClusterAggregator:
    """
    Aggregates policy area scores into cluster scores (MESO level).
    
    Responsibilities:
    - Aggregate multiple area scores per cluster
    - Apply cluster-specific weights
    - Calculate coherence metrics
    - Validate cluster hermeticity
    """
    
    def __init__(self, monolith: Dict[str, Any], abort_on_insufficient: bool = True):
        """
        Initialize cluster aggregator.
        
        Args:
            monolith: Questionnaire monolith configuration
            abort_on_insufficient: Whether to abort on insufficient coverage
        """
        self.monolith = monolith
        self.abort_on_insufficient = abort_on_insufficient
        
        # Extract configuration
        self.scoring_config = monolith["blocks"]["scoring"]
        self.niveles = monolith["blocks"]["niveles_abstraccion"]
        self.clusters = self.niveles["clusters"]
        
        logger.info("ClusterAggregator initialized")
    
    def validate_cluster_hermeticity(
        self,
        cluster_def: Dict[str, Any],
        area_scores: List[AreaScore]
    ) -> Tuple[bool, str]:
        """
        Validate cluster hermeticity.
        
        Args:
            cluster_def: Cluster definition from monolith
            area_scores: List of area scores for this cluster
            
        Returns:
            Tuple of (is_valid, message)
            
        Raises:
            HermeticityValidationError: If hermeticity is violated
        """
        expected_areas = cluster_def.get("policy_area_ids", [])
        actual_areas = [a.area_id for a in area_scores]
        
        # Check that all expected areas are present
        missing_areas = set(expected_areas) - set(actual_areas)
        if missing_areas:
            msg = (
                f"Cluster hermeticity violation: "
                f"missing areas {missing_areas} for cluster {cluster_def['cluster_id']}"
            )
            logger.error(msg)
            if self.abort_on_insufficient:
                raise HermeticityValidationError(msg)
            return False, msg
        
        # Check for unexpected areas
        extra_areas = set(actual_areas) - set(expected_areas)
        if extra_areas:
            msg = (
                f"Cluster hermeticity violation: "
                f"unexpected areas {extra_areas} for cluster {cluster_def['cluster_id']}"
            )
            logger.error(msg)
            if self.abort_on_insufficient:
                raise HermeticityValidationError(msg)
            return False, msg
        
        logger.debug(f"Cluster hermeticity validated for {cluster_def['cluster_id']}")
        return True, "Cluster hermeticity validated"
    
    def apply_cluster_weights(
        self,
        area_scores: List[AreaScore],
        weights: Optional[List[float]] = None
    ) -> float:
        """
        Apply cluster-specific weights to area scores.
        
        Args:
            area_scores: List of area scores
            weights: Optional weights (defaults to equal weights)
            
        Returns:
            Weighted average score
        """
        scores = [a.score for a in area_scores]
        
        if weights is None:
            # Equal weights
            weights = [1.0 / len(scores)] * len(scores)
        
        # Validate weights sum to 1.0
        weight_sum = sum(weights)
        tolerance = 1e-6
        if abs(weight_sum - 1.0) > tolerance:
            msg = f"Cluster weight validation failed: sum={weight_sum:.6f}"
            logger.error(msg)
            if self.abort_on_insufficient:
                raise WeightValidationError(msg)
        
        # Calculate weighted average
        weighted_avg = sum(s * w for s, w in zip(scores, weights))
        
        logger.debug(
            f"Cluster weights applied: scores={scores}, "
            f"weights={weights}, result={weighted_avg:.4f}"
        )
        
        return weighted_avg
    
    def analyze_coherence(self, area_scores: List[AreaScore]) -> float:
        """
        Analyze cluster coherence.
        
        Coherence is measured as the inverse of standard deviation.
        Higher coherence means scores are more consistent.
        
        Args:
            area_scores: List of area scores
            
        Returns:
            Coherence value (0-1, where 1 is perfect coherence)
        """
        scores = [a.score for a in area_scores]
        
        if len(scores) <= 1:
            return 1.0
        
        # Calculate mean
        mean = sum(scores) / len(scores)
        
        # Calculate standard deviation
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Convert to coherence (inverse relationship)
        # Normalize by max possible std dev (3.0 for 0-3 range)
        max_std = 3.0
        coherence = max(0.0, 1.0 - (std_dev / max_std))
        
        logger.debug(
            f"Coherence analysis: mean={mean:.4f}, "
            f"std_dev={std_dev:.4f}, coherence={coherence:.4f}"
        )
        
        return coherence
    
    def aggregate_cluster(
        self,
        cluster_id: str,
        area_scores: List[AreaScore],
        weights: Optional[List[float]] = None
    ) -> ClusterScore:
        """
        Aggregate a single MESO cluster from area scores.
        
        Args:
            cluster_id: Cluster ID (e.g., "CL01")
            area_scores: List of area scores for this cluster
            weights: Optional cluster-specific weights
            
        Returns:
            ClusterScore with aggregated score and coherence
            
        Raises:
            ValidationError: If validation fails
        """
        logger.info(f"Aggregating cluster {cluster_id}")
        
        validation_details = {}
        
        # Get cluster definition
        cluster_def = next(
            (c for c in self.clusters if c["cluster_id"] == cluster_id),
            None
        )
        
        if not cluster_def:
            logger.error(f"Cluster definition not found: {cluster_id}")
            return ClusterScore(
                cluster_id=cluster_id,
                cluster_name=cluster_id,
                areas=[],
                score=0.0,
                coherence=0.0,
                area_scores=[],
                validation_passed=False,
                validation_details={"error": "Definition not found", "type": "config"}
            )
        
        cluster_name = cluster_def["i18n"]["keys"]["label_es"]
        expected_areas = cluster_def["policy_area_ids"]
        
        # Filter area scores for this cluster
        cluster_area_scores = [
            a for a in area_scores
            if a.area_id in expected_areas
        ]
        
        # Validate hermeticity
        try:
            hermetic_valid, hermetic_msg = self.validate_cluster_hermeticity(
                cluster_def,
                cluster_area_scores
            )
            validation_details["hermeticity"] = {
                "valid": hermetic_valid,
                "message": hermetic_msg
            }
        except HermeticityValidationError as e:
            logger.error(f"Cluster hermeticity validation failed: {e}")
            return ClusterScore(
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                areas=expected_areas,
                score=0.0,
                coherence=0.0,
                area_scores=[],
                validation_passed=False,
                validation_details={"error": str(e), "type": "hermeticity"}
            )
        
        if not cluster_area_scores:
            logger.warning(f"No area scores for cluster {cluster_id}")
            return ClusterScore(
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                areas=expected_areas,
                score=0.0,
                coherence=0.0,
                area_scores=[],
                validation_passed=False,
                validation_details={"error": "No areas", "type": "empty"}
            )
        
        # Apply cluster weights
        try:
            weighted_score = self.apply_cluster_weights(cluster_area_scores, weights)
            validation_details["weights"] = {
                "valid": True,
                "weights": weights if weights else "equal",
                "score": weighted_score
            }
        except WeightValidationError as e:
            logger.error(f"Cluster weight validation failed: {e}")
            return ClusterScore(
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                areas=expected_areas,
                score=0.0,
                coherence=0.0,
                area_scores=cluster_area_scores,
                validation_passed=False,
                validation_details={"error": str(e), "type": "weights"}
            )
        
        # Analyze coherence
        coherence = self.analyze_coherence(cluster_area_scores)
        validation_details["coherence"] = {
            "value": coherence,
            "interpretation": "high" if coherence > 0.8 else "medium" if coherence > 0.6 else "low"
        }
        
        logger.info(
            f"✓ Cluster {cluster_id} ({cluster_name}): "
            f"score={weighted_score:.4f}, coherence={coherence:.4f}"
        )
        
        return ClusterScore(
            cluster_id=cluster_id,
            cluster_name=cluster_name,
            areas=expected_areas,
            score=weighted_score,
            coherence=coherence,
            area_scores=cluster_area_scores,
            validation_passed=True,
            validation_details=validation_details
        )


class MacroAggregator:
    """
    Performs holistic macro evaluation (Q305).
    
    Responsibilities:
    - Aggregate all cluster scores
    - Calculate cross-cutting coherence
    - Identify systemic gaps
    - Assess strategic alignment
    """
    
    def __init__(self, monolith: Dict[str, Any], abort_on_insufficient: bool = True):
        """
        Initialize macro aggregator.
        
        Args:
            monolith: Questionnaire monolith configuration
            abort_on_insufficient: Whether to abort on insufficient coverage
        """
        self.monolith = monolith
        self.abort_on_insufficient = abort_on_insufficient
        
        # Extract configuration
        self.scoring_config = monolith["blocks"]["scoring"]
        self.niveles = monolith["blocks"]["niveles_abstraccion"]
        
        logger.info("MacroAggregator initialized")
    
    def calculate_cross_cutting_coherence(
        self,
        cluster_scores: List[ClusterScore]
    ) -> float:
        """
        Calculate cross-cutting coherence across all clusters.
        
        Args:
            cluster_scores: List of cluster scores
            
        Returns:
            Cross-cutting coherence value (0-1)
        """
        scores = [c.score for c in cluster_scores]
        
        if len(scores) <= 1:
            return 1.0
        
        # Calculate mean
        mean = sum(scores) / len(scores)
        
        # Calculate standard deviation
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Convert to coherence
        max_std = 3.0
        coherence = max(0.0, 1.0 - (std_dev / max_std))
        
        logger.debug(
            f"Cross-cutting coherence: mean={mean:.4f}, "
            f"std_dev={std_dev:.4f}, coherence={coherence:.4f}"
        )
        
        return coherence
    
    def identify_systemic_gaps(
        self,
        area_scores: List[AreaScore]
    ) -> List[str]:
        """
        Identify systemic gaps (areas with INSUFICIENTE quality).
        
        Args:
            area_scores: List of area scores
            
        Returns:
            List of area names with systemic gaps
        """
        gaps = []
        for area in area_scores:
            if area.quality_level == "INSUFICIENTE":
                gaps.append(area.area_name)
                logger.warning(f"Systemic gap identified: {area.area_name}")
        
        logger.info(f"Systemic gaps identified: {len(gaps)}")
        return gaps
    
    def assess_strategic_alignment(
        self,
        cluster_scores: List[ClusterScore],
        dimension_scores: List[DimensionScore]
    ) -> float:
        """
        Assess strategic alignment across all levels.
        
        Args:
            cluster_scores: List of cluster scores
            dimension_scores: List of dimension scores
            
        Returns:
            Strategic alignment score (0-1)
        """
        # Calculate average cluster coherence
        cluster_coherence = (
            sum(c.coherence for c in cluster_scores) / len(cluster_scores)
            if cluster_scores else 0.0
        )
        
        # Calculate dimension validation rate
        validated_dims = sum(1 for d in dimension_scores if d.validation_passed)
        validation_rate = validated_dims / len(dimension_scores) if dimension_scores else 0.0
        
        # Strategic alignment is weighted combination
        alignment = (0.6 * cluster_coherence) + (0.4 * validation_rate)
        
        logger.debug(
            f"Strategic alignment: cluster_coherence={cluster_coherence:.4f}, "
            f"validation_rate={validation_rate:.4f}, alignment={alignment:.4f}"
        )
        
        return alignment
    
    def apply_rubric_thresholds(
        self,
        score: float,
        thresholds: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Apply macro-level rubric thresholds.
        
        Args:
            score: Aggregated macro score (0-3 range)
            thresholds: Optional threshold definitions
            
        Returns:
            Quality level (EXCELENTE, BUENO, ACEPTABLE, INSUFICIENTE)
        """
        # Clamp score to valid range [0, 3]
        clamped_score = max(0.0, min(3.0, score))
        
        # Normalize to 0-1 range
        normalized_score = clamped_score / 3.0
        
        # Apply standard thresholds
        if normalized_score >= 0.85:
            quality = "EXCELENTE"
        elif normalized_score >= 0.70:
            quality = "BUENO"
        elif normalized_score >= 0.55:
            quality = "ACEPTABLE"
        else:
            quality = "INSUFICIENTE"
        
        logger.debug(
            f"Macro rubric applied: score={score:.4f}, "
            f"normalized={normalized_score:.4f}, quality={quality}"
        )
        
        return quality
    
    def evaluate_macro(
        self,
        cluster_scores: List[ClusterScore],
        area_scores: List[AreaScore],
        dimension_scores: List[DimensionScore]
    ) -> MacroScore:
        """
        Perform holistic macro evaluation (Q305).
        
        Args:
            cluster_scores: List of cluster scores (MESO level)
            area_scores: List of area scores
            dimension_scores: List of dimension scores
            
        Returns:
            MacroScore with holistic evaluation
        """
        logger.info("Performing macro holistic evaluation (Q305)")
        
        validation_details = {}
        
        if not cluster_scores:
            logger.error("No cluster scores available for macro evaluation")
            return MacroScore(
                score=0.0,
                quality_level="INSUFICIENTE",
                cross_cutting_coherence=0.0,
                systemic_gaps=[],
                strategic_alignment=0.0,
                cluster_scores=[],
                validation_passed=False,
                validation_details={"error": "No clusters", "type": "empty"}
            )
        
        # Calculate cross-cutting coherence
        cross_cutting_coherence = self.calculate_cross_cutting_coherence(cluster_scores)
        validation_details["coherence"] = {
            "value": cross_cutting_coherence,
            "clusters": len(cluster_scores)
        }
        
        # Identify systemic gaps
        systemic_gaps = self.identify_systemic_gaps(area_scores)
        validation_details["gaps"] = {
            "count": len(systemic_gaps),
            "areas": systemic_gaps
        }
        
        # Assess strategic alignment
        strategic_alignment = self.assess_strategic_alignment(
            cluster_scores,
            dimension_scores
        )
        validation_details["alignment"] = {
            "value": strategic_alignment
        }
        
        # Calculate overall macro score (weighted average of clusters)
        cluster_score_values = [c.score for c in cluster_scores]
        macro_score = sum(cluster_score_values) / len(cluster_score_values)
        
        # Apply quality rubric
        quality_level = self.apply_rubric_thresholds(macro_score)
        validation_details["rubric"] = {
            "score": macro_score,
            "quality_level": quality_level
        }
        
        logger.info(
            f"✓ Macro evaluation (Q305): score={macro_score:.4f}, "
            f"quality={quality_level}, coherence={cross_cutting_coherence:.4f}, "
            f"alignment={strategic_alignment:.4f}, gaps={len(systemic_gaps)}"
        )
        
        return MacroScore(
            score=macro_score,
            quality_level=quality_level,
            cross_cutting_coherence=cross_cutting_coherence,
            systemic_gaps=systemic_gaps,
            strategic_alignment=strategic_alignment,
            cluster_scores=cluster_scores,
            validation_passed=True,
            validation_details=validation_details
        )
