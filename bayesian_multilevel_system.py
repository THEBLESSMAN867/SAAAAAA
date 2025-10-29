"""
Bayesian Multi-Level Analysis System
=====================================

Complete implementation of the multi-level Bayesian analysis framework with:

MICRO LEVEL:
- Reconciliation Layer: Range/unit/period/entity validators with penalty factors
- Bayesian Updater: Probative test taxonomy with posterior estimation
- Output: posterior_table_micro.csv

MESO LEVEL:
- Dispersion Engine: CV, max_gap, Gini coefficient computation
- Peer Calibration: peer_context comparison with narrative hooks
- Bayesian Roll-Up: posterior_meso calculation with penalties
- Output: posterior_table_meso.csv

MACRO LEVEL:
- Contradiction Scanner: micro↔meso↔macro consistency detector
- Bayesian Portfolio Composer: Coverage, dispersion, contradiction penalties
- Output: posterior_table_macro.csv

Author: Integration Team
Version: 1.0.0
Python: 3.10+
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set, Protocol
from collections import defaultdict
from datetime import datetime

import numpy as np
from scipy import stats
from scipy.stats import beta


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMERATIONS AND TYPE DEFINITIONS
# ============================================================================

class ValidatorType(Enum):
    """Types of validators for reconciliation layer"""
    RANGE = auto()
    UNIT = auto()
    PERIOD = auto()
    ENTITY = auto()


class ProbativeTestType(Enum):
    """Taxonomy of probative tests for Bayesian updating"""
    STRAW_IN_WIND = "straw_in_wind"  # Weak confirmation
    HOOP_TEST = "hoop_test"  # Necessary but not sufficient
    SMOKING_GUN = "smoking_gun"  # Sufficient but not necessary
    DOUBLY_DECISIVE = "doubly_decisive"  # Both necessary and sufficient


class PenaltyCategory(Enum):
    """Categories of penalties applied to scores"""
    VALIDATION_FAILURE = "validation_failure"
    DISPERSION_HIGH = "dispersion_high"
    COVERAGE_GAP = "coverage_gap"
    CONTRADICTION = "contradiction"
    PEER_DEVIATION = "peer_deviation"


# ============================================================================
# MICRO LEVEL: RECONCILIATION LAYER
# ============================================================================

@dataclass
class ValidationRule:
    """Definition of a validation rule"""
    validator_type: ValidatorType
    field_name: str
    expected_range: Optional[Tuple[float, float]] = None
    expected_unit: Optional[str] = None
    expected_period: Optional[str] = None
    expected_entity: Optional[str] = None
    penalty_factor: float = 0.1  # Penalty multiplier for violations


@dataclass
class ValidationResult:
    """Result of a validation check"""
    rule: ValidationRule
    passed: bool
    observed_value: Any
    expected_value: Any
    violation_severity: float  # 0.0 (no violation) to 1.0 (severe)
    penalty_applied: float


class ReconciliationValidator:
    """
    Reconciliation Layer: Validates data against expected ranges, units, periods, entities
    Applies penalty factors for violations
    """
    
    def __init__(self, validation_rules: List[ValidationRule]):
        self.rules = validation_rules
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_range(self, value: float, rule: ValidationRule) -> ValidationResult:
        """Validate numeric value is within expected range"""
        if rule.expected_range is None:
            return ValidationResult(
                rule=rule, passed=True, observed_value=value,
                expected_value=None, violation_severity=0.0, penalty_applied=0.0
            )
        
        min_val, max_val = rule.expected_range
        passed = min_val <= value <= max_val
        
        if not passed:
            # Calculate violation severity based on how far outside range
            if value < min_val:
                violation_severity = min(1.0, (min_val - value) / max(abs(min_val), 1.0))
            else:
                violation_severity = min(1.0, (value - max_val) / max(abs(max_val), 1.0))
        else:
            violation_severity = 0.0
        
        penalty = violation_severity * rule.penalty_factor if not passed else 0.0
        
        return ValidationResult(
            rule=rule, passed=passed, observed_value=value,
            expected_value=rule.expected_range, violation_severity=violation_severity,
            penalty_applied=penalty
        )
    
    def validate_unit(self, unit: str, rule: ValidationRule) -> ValidationResult:
        """Validate unit matches expected unit"""
        if rule.expected_unit is None:
            return ValidationResult(
                rule=rule, passed=True, observed_value=unit,
                expected_value=None, violation_severity=0.0, penalty_applied=0.0
            )
        
        passed = unit.lower() == rule.expected_unit.lower()
        violation_severity = 1.0 if not passed else 0.0
        penalty = violation_severity * rule.penalty_factor if not passed else 0.0
        
        return ValidationResult(
            rule=rule, passed=passed, observed_value=unit,
            expected_value=rule.expected_unit, violation_severity=violation_severity,
            penalty_applied=penalty
        )
    
    def validate_period(self, period: str, rule: ValidationRule) -> ValidationResult:
        """Validate temporal period matches expected period"""
        if rule.expected_period is None:
            return ValidationResult(
                rule=rule, passed=True, observed_value=period,
                expected_value=None, violation_severity=0.0, penalty_applied=0.0
            )
        
        passed = period.lower() == rule.expected_period.lower()
        violation_severity = 1.0 if not passed else 0.0
        penalty = violation_severity * rule.penalty_factor if not passed else 0.0
        
        return ValidationResult(
            rule=rule, passed=passed, observed_value=period,
            expected_value=rule.expected_period, violation_severity=violation_severity,
            penalty_applied=penalty
        )
    
    def validate_entity(self, entity: str, rule: ValidationRule) -> ValidationResult:
        """Validate entity matches expected entity"""
        if rule.expected_entity is None:
            return ValidationResult(
                rule=rule, passed=True, observed_value=entity,
                expected_value=None, violation_severity=0.0, penalty_applied=0.0
            )
        
        passed = entity.lower() == rule.expected_entity.lower()
        violation_severity = 1.0 if not passed else 0.0
        penalty = violation_severity * rule.penalty_factor if not passed else 0.0
        
        return ValidationResult(
            rule=rule, passed=passed, observed_value=entity,
            expected_value=rule.expected_entity, violation_severity=violation_severity,
            penalty_applied=penalty
        )
    
    def validate_data(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate data against all rules"""
        results = []
        
        for rule in self.rules:
            if rule.field_name not in data:
                continue
            
            value = data[rule.field_name]
            
            if rule.validator_type == ValidatorType.RANGE:
                result = self.validate_range(value, rule)
            elif rule.validator_type == ValidatorType.UNIT:
                result = self.validate_unit(value, rule)
            elif rule.validator_type == ValidatorType.PERIOD:
                result = self.validate_period(value, rule)
            elif rule.validator_type == ValidatorType.ENTITY:
                result = self.validate_entity(value, rule)
            else:
                continue
            
            results.append(result)
        
        return results
    
    def calculate_total_penalty(self, validation_results: List[ValidationResult]) -> float:
        """Calculate total penalty from validation results"""
        return sum(r.penalty_applied for r in validation_results)


# ============================================================================
# MICRO LEVEL: BAYESIAN UPDATER
# ============================================================================

@dataclass
class ProbativeTest:
    """Definition of a probative test"""
    test_type: ProbativeTestType
    test_name: str
    evidence_strength: float  # How strong the evidence if test passes
    prior_probability: float  # Prior belief before test
    
    def calculate_likelihood_ratio(self, test_passed: bool) -> float:
        """
        Calculate Bayesian likelihood ratio
        
        Straw-in-wind: weak confirmation (LR ~ 2)
        Hoop test: strong disconfirmation if fails (LR ~ 0.1 if fails)
        Smoking gun: strong confirmation if passes (LR ~ 10)
        Doubly decisive: both necessary and sufficient (LR ~ 20 if passes, 0.05 if fails)
        """
        if self.test_type == ProbativeTestType.STRAW_IN_WIND:
            return 2.0 if test_passed else 0.8
        elif self.test_type == ProbativeTestType.HOOP_TEST:
            return 1.2 if test_passed else 0.1
        elif self.test_type == ProbativeTestType.SMOKING_GUN:
            return 10.0 if test_passed else 0.9
        elif self.test_type == ProbativeTestType.DOUBLY_DECISIVE:
            return 20.0 if test_passed else 0.05
        else:
            return 1.0


@dataclass
class BayesianUpdate:
    """Result of Bayesian updating"""
    test: ProbativeTest
    test_passed: bool
    prior: float
    likelihood_ratio: float
    posterior: float
    evidence_weight: float


class BayesianUpdater:
    """
    Bayesian Updater: Sequential Bayesian updating based on probative test taxonomy
    Generates posterior_table_micro.csv
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.updates: List[BayesianUpdate] = []
    
    def update(self, prior: float, test: ProbativeTest, test_passed: bool) -> float:
        """
        Perform Bayesian update using probative test
        
        P(H|E) = P(E|H) * P(H) / P(E)
        
        Using odds form:
        O(H|E) = LR * O(H)
        """
        # Calculate likelihood ratio
        lr = test.calculate_likelihood_ratio(test_passed)
        
        # Convert prior probability to odds
        prior_odds = prior / (1 - prior + 1e-10)
        
        # Update odds
        posterior_odds = lr * prior_odds
        
        # Convert back to probability
        posterior = posterior_odds / (1 + posterior_odds)
        
        # Ensure valid probability
        posterior = max(0.0, min(1.0, posterior))
        
        # Calculate evidence weight (KL divergence)
        evidence_weight = self._calculate_evidence_weight(prior, posterior)
        
        # Record update
        update = BayesianUpdate(
            test=test,
            test_passed=test_passed,
            prior=prior,
            likelihood_ratio=lr,
            posterior=posterior,
            evidence_weight=evidence_weight
        )
        self.updates.append(update)
        
        self.logger.debug(
            f"Bayesian update: {test.test_name} ({test.test_type.value}): "
            f"prior={prior:.3f} → posterior={posterior:.3f} (LR={lr:.2f})"
        )
        
        return posterior
    
    def sequential_update(
        self, 
        initial_prior: float, 
        tests: List[Tuple[ProbativeTest, bool]]
    ) -> float:
        """Sequentially update belief through multiple tests"""
        current_belief = initial_prior
        
        for test, test_passed in tests:
            current_belief = self.update(current_belief, test, test_passed)
        
        return current_belief
    
    def _calculate_evidence_weight(self, prior: float, posterior: float) -> float:
        """Calculate evidence weight using KL divergence"""
        # Avoid log(0)
        prior = max(1e-10, min(1 - 1e-10, prior))
        posterior = max(1e-10, min(1 - 1e-10, posterior))
        
        # KL divergence: D_KL(posterior || prior)
        kl_div = (
            posterior * np.log(posterior / prior) +
            (1 - posterior) * np.log((1 - posterior) / (1 - prior))
        )
        
        return abs(kl_div)
    
    def export_to_csv(self, output_path: Path):
        """Export posterior table to CSV"""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'test_name', 'test_type', 'test_passed', 'prior', 
                'likelihood_ratio', 'posterior', 'evidence_weight'
            ])
            
            for update in self.updates:
                writer.writerow([
                    update.test.test_name,
                    update.test.test_type.value,
                    update.test_passed,
                    f"{update.prior:.4f}",
                    f"{update.likelihood_ratio:.4f}",
                    f"{update.posterior:.4f}",
                    f"{update.evidence_weight:.4f}"
                ])
        
        self.logger.info(f"Exported {len(self.updates)} Bayesian updates to {output_path}")


# ============================================================================
# MICRO LEVEL: INTEGRATION
# ============================================================================

@dataclass
class MicroLevelAnalysis:
    """Complete micro-level analysis with reconciliation and Bayesian updating"""
    question_id: str
    raw_score: float
    validation_results: List[ValidationResult]
    validation_penalty: float
    bayesian_updates: List[BayesianUpdate]
    final_posterior: float
    adjusted_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# MESO LEVEL: DISPERSION ENGINE
# ============================================================================

class DispersionEngine:
    """
    Dispersion Engine: Computes CV, max_gap, Gini coefficient
    Integrates dispersion penalties into meso-level scoring
    """
    
    def __init__(self, dispersion_threshold: float = 0.3):
        self.dispersion_threshold = dispersion_threshold
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_cv(self, scores: List[float]) -> float:
        """Calculate Coefficient of Variation (CV = std / mean)"""
        if not scores or len(scores) < 2:
            return 0.0
        
        mean_score = np.mean(scores)
        std_score = np.std(scores, ddof=1)
        
        if mean_score == 0:
            return 0.0
        
        cv = std_score / mean_score
        return cv
    
    def calculate_max_gap(self, scores: List[float]) -> float:
        """Calculate maximum gap between adjacent scores"""
        if not scores or len(scores) < 2:
            return 0.0
        
        sorted_scores = sorted(scores)
        gaps = [sorted_scores[i+1] - sorted_scores[i] for i in range(len(sorted_scores) - 1)]
        
        return max(gaps) if gaps else 0.0
    
    def calculate_gini(self, scores: List[float]) -> float:
        """
        Calculate Gini coefficient
        0 = perfect equality, 1 = perfect inequality
        """
        if not scores or len(scores) < 2:
            return 0.0
        
        # Sort scores
        sorted_scores = np.array(sorted(scores))
        n = len(sorted_scores)
        
        # Calculate Gini
        index = np.arange(1, n + 1)
        gini = (2 * np.sum(index * sorted_scores)) / (n * np.sum(sorted_scores)) - (n + 1) / n
        
        return gini
    
    def calculate_dispersion_penalty(self, scores: List[float]) -> Tuple[float, Dict[str, float]]:
        """
        Calculate dispersion penalty based on CV, max_gap, and Gini
        Returns (penalty, metrics_dict)
        """
        cv = self.calculate_cv(scores)
        max_gap = self.calculate_max_gap(scores)
        gini = self.calculate_gini(scores)
        
        # Calculate penalties for each metric
        cv_penalty = max(0.0, (cv - self.dispersion_threshold) * 0.5)
        gap_penalty = max(0.0, (max_gap - 1.0) * 0.3)  # Penalty if gap > 1.0
        gini_penalty = max(0.0, (gini - 0.3) * 0.4)  # Penalty if Gini > 0.3
        
        # Total penalty (capped at 1.0)
        total_penalty = min(1.0, cv_penalty + gap_penalty + gini_penalty)
        
        metrics = {
            'cv': cv,
            'max_gap': max_gap,
            'gini': gini,
            'cv_penalty': cv_penalty,
            'gap_penalty': gap_penalty,
            'gini_penalty': gini_penalty,
            'total_penalty': total_penalty
        }
        
        self.logger.debug(
            f"Dispersion metrics: CV={cv:.3f}, max_gap={max_gap:.3f}, "
            f"Gini={gini:.3f}, penalty={total_penalty:.3f}"
        )
        
        return total_penalty, metrics


# ============================================================================
# MESO LEVEL: PEER CALIBRATION
# ============================================================================

@dataclass
class PeerContext:
    """Peer context for comparison"""
    peer_id: str
    peer_name: str
    scores: Dict[str, float]  # dimension -> score
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PeerComparison:
    """Result of peer comparison"""
    target_score: float
    peer_mean: float
    peer_std: float
    z_score: float
    percentile: float
    deviation_penalty: float
    narrative: str


class PeerCalibrator:
    """
    Peer Calibration: Compare scores against peer context
    Generate narrative hooks for contextualization
    """
    
    def __init__(self, deviation_threshold: float = 1.5):
        self.deviation_threshold = deviation_threshold  # Z-score threshold
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def compare_to_peers(
        self, 
        target_score: float, 
        peer_contexts: List[PeerContext],
        dimension: str
    ) -> PeerComparison:
        """Compare target score to peer contexts"""
        # Extract peer scores for this dimension
        peer_scores = [
            peer.scores.get(dimension, 0.0) 
            for peer in peer_contexts 
            if dimension in peer.scores
        ]
        
        if not peer_scores:
            return PeerComparison(
                target_score=target_score,
                peer_mean=0.0,
                peer_std=0.0,
                z_score=0.0,
                percentile=0.5,
                deviation_penalty=0.0,
                narrative="No peer data available for comparison"
            )
        
        # Calculate peer statistics
        peer_mean = np.mean(peer_scores)
        peer_std = np.std(peer_scores, ddof=1) if len(peer_scores) > 1 else 1.0
        
        # Calculate z-score
        z_score = (target_score - peer_mean) / (peer_std + 1e-10)
        
        # Calculate percentile
        percentile = stats.percentileofscore(peer_scores, target_score) / 100.0
        
        # Calculate deviation penalty
        deviation_penalty = max(0.0, (abs(z_score) - self.deviation_threshold) * 0.2)
        deviation_penalty = min(0.5, deviation_penalty)  # Cap at 0.5
        
        # Generate narrative
        narrative = self._generate_narrative(
            target_score, peer_mean, peer_std, z_score, percentile
        )
        
        return PeerComparison(
            target_score=target_score,
            peer_mean=peer_mean,
            peer_std=peer_std,
            z_score=z_score,
            percentile=percentile,
            deviation_penalty=deviation_penalty,
            narrative=narrative
        )
    
    def _generate_narrative(
        self, 
        score: float, 
        peer_mean: float, 
        peer_std: float,
        z_score: float, 
        percentile: float
    ) -> str:
        """Generate narrative hook for peer comparison"""
        # Determine performance relative to peers
        if z_score > 1.5:
            performance = "significantly above"
        elif z_score > 0.5:
            performance = "moderately above"
        elif z_score > -0.5:
            performance = "comparable to"
        elif z_score > -1.5:
            performance = "moderately below"
        else:
            performance = "significantly below"
        
        # Determine percentile description
        if percentile >= 0.9:
            rank = "top 10%"
        elif percentile >= 0.75:
            rank = "top quartile"
        elif percentile >= 0.5:
            rank = "above median"
        elif percentile >= 0.25:
            rank = "below median"
        else:
            rank = "bottom quartile"
        
        narrative = (
            f"Score of {score:.2f} is {performance} peer average "
            f"({peer_mean:.2f} ± {peer_std:.2f}), "
            f"placing in the {rank} (percentile: {percentile:.1%})"
        )
        
        return narrative


# ============================================================================
# MESO LEVEL: BAYESIAN ROLL-UP
# ============================================================================

@dataclass
class MesoLevelAnalysis:
    """Complete meso-level analysis with dispersion and peer calibration"""
    cluster_id: str
    micro_scores: List[float]
    raw_meso_score: float
    dispersion_metrics: Dict[str, float]
    dispersion_penalty: float
    peer_comparison: Optional[PeerComparison]
    peer_penalty: float
    total_penalty: float
    final_posterior: float
    adjusted_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BayesianRollUp:
    """
    Bayesian Roll-Up: Aggregate micro posteriors to meso level with penalties
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def aggregate_micro_to_meso(
        self,
        micro_analyses: List[MicroLevelAnalysis],
        dispersion_penalty: float = 0.0,
        peer_penalty: float = 0.0,
        additional_penalties: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Aggregate micro-level posteriors to meso-level posterior
        
        Uses hierarchical Bayesian model:
        - Micro posteriors are observations
        - Meso posterior is hyperparameter
        """
        if not micro_analyses:
            return 0.0
        
        # Extract posteriors
        posteriors = [m.final_posterior for m in micro_analyses]
        
        # Calculate weighted mean (could use Beta-Binomial hierarchical model)
        raw_meso_posterior = np.mean(posteriors)
        
        # Apply penalties
        total_penalty = dispersion_penalty + peer_penalty
        if additional_penalties:
            total_penalty += sum(additional_penalties.values())
        
        # Adjust posterior (multiplicative penalty)
        adjusted_posterior = raw_meso_posterior * (1 - total_penalty)
        adjusted_posterior = max(0.0, min(1.0, adjusted_posterior))
        
        self.logger.debug(
            f"Meso roll-up: {len(micro_analyses)} micro → "
            f"raw={raw_meso_posterior:.3f}, penalty={total_penalty:.3f}, "
            f"adjusted={adjusted_posterior:.3f}"
        )
        
        return adjusted_posterior
    
    def export_to_csv(
        self, 
        meso_analyses: List[MesoLevelAnalysis], 
        output_path: Path
    ):
        """Export meso posterior table to CSV"""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'cluster_id', 'raw_meso_score', 'dispersion_penalty',
                'peer_penalty', 'total_penalty', 'adjusted_score',
                'cv', 'max_gap', 'gini'
            ])
            
            for analysis in meso_analyses:
                writer.writerow([
                    analysis.cluster_id,
                    f"{analysis.raw_meso_score:.4f}",
                    f"{analysis.dispersion_penalty:.4f}",
                    f"{analysis.peer_penalty:.4f}",
                    f"{analysis.total_penalty:.4f}",
                    f"{analysis.adjusted_score:.4f}",
                    f"{analysis.dispersion_metrics.get('cv', 0.0):.4f}",
                    f"{analysis.dispersion_metrics.get('max_gap', 0.0):.4f}",
                    f"{analysis.dispersion_metrics.get('gini', 0.0):.4f}"
                ])
        
        self.logger.info(
            f"Exported {len(meso_analyses)} meso analyses to {output_path}"
        )


# ============================================================================
# MACRO LEVEL: CONTRADICTION SCANNER
# ============================================================================

@dataclass
class ContradictionDetection:
    """Detected contradiction between levels"""
    level_a: str  # e.g., "micro:P1-D1-Q1"
    level_b: str  # e.g., "meso:CL01"
    score_a: float
    score_b: float
    discrepancy: float
    severity: float  # 0.0-1.0
    description: str


class ContradictionScanner:
    """
    Macro Contradiction Scanner: Detect inconsistencies between micro↔meso↔macro
    """
    
    def __init__(self, discrepancy_threshold: float = 0.3):
        self.discrepancy_threshold = discrepancy_threshold
        self.logger = logging.getLogger(self.__class__.__name__)
        self.contradictions: List[ContradictionDetection] = []
    
    def scan_micro_meso(
        self,
        micro_analyses: List[MicroLevelAnalysis],
        meso_analysis: MesoLevelAnalysis
    ) -> List[ContradictionDetection]:
        """Scan for contradictions between micro and meso levels"""
        contradictions = []
        
        for micro in micro_analyses:
            discrepancy = abs(micro.adjusted_score - meso_analysis.adjusted_score)
            
            if discrepancy > self.discrepancy_threshold:
                severity = min(1.0, discrepancy / 2.0)
                
                contradiction = ContradictionDetection(
                    level_a=f"micro:{micro.question_id}",
                    level_b=f"meso:{meso_analysis.cluster_id}",
                    score_a=micro.adjusted_score,
                    score_b=meso_analysis.adjusted_score,
                    discrepancy=discrepancy,
                    severity=severity,
                    description=f"Micro question {micro.question_id} score "
                               f"({micro.adjusted_score:.2f}) differs significantly from "
                               f"meso cluster {meso_analysis.cluster_id} "
                               f"({meso_analysis.adjusted_score:.2f})"
                )
                
                contradictions.append(contradiction)
                self.contradictions.append(contradiction)
        
        return contradictions
    
    def scan_meso_macro(
        self,
        meso_analyses: List[MesoLevelAnalysis],
        macro_score: float
    ) -> List[ContradictionDetection]:
        """Scan for contradictions between meso and macro levels"""
        contradictions = []
        
        for meso in meso_analyses:
            discrepancy = abs(meso.adjusted_score - macro_score)
            
            if discrepancy > self.discrepancy_threshold:
                severity = min(1.0, discrepancy / 2.0)
                
                contradiction = ContradictionDetection(
                    level_a=f"meso:{meso.cluster_id}",
                    level_b="macro:overall",
                    score_a=meso.adjusted_score,
                    score_b=macro_score,
                    discrepancy=discrepancy,
                    severity=severity,
                    description=f"Meso cluster {meso.cluster_id} score "
                               f"({meso.adjusted_score:.2f}) differs significantly from "
                               f"macro overall ({macro_score:.2f})"
                )
                
                contradictions.append(contradiction)
                self.contradictions.append(contradiction)
        
        return contradictions
    
    def calculate_contradiction_penalty(self) -> float:
        """Calculate penalty based on detected contradictions"""
        if not self.contradictions:
            return 0.0
        
        # Average severity weighted by number of contradictions
        avg_severity = np.mean([c.severity for c in self.contradictions])
        count_factor = min(1.0, len(self.contradictions) / 10.0)  # Max at 10 contradictions
        
        penalty = avg_severity * count_factor * 0.5  # Max penalty 0.5
        
        return penalty


# ============================================================================
# MACRO LEVEL: BAYESIAN PORTFOLIO COMPOSER
# ============================================================================

@dataclass
class MacroLevelAnalysis:
    """Complete macro-level portfolio analysis"""
    overall_posterior: float
    coverage_score: float
    coverage_penalty: float
    dispersion_score: float
    dispersion_penalty: float
    contradiction_count: int
    contradiction_penalty: float
    total_penalty: float
    adjusted_score: float
    cluster_scores: Dict[str, float]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class BayesianPortfolioComposer:
    """
    Macro Bayesian Portfolio Composer: 
    Aggregate all evidence with coverage, dispersion, and contradiction penalties
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_coverage(
        self,
        questions_answered: int,
        total_questions: int
    ) -> Tuple[float, float]:
        """
        Calculate coverage score and penalty
        Returns (coverage_score, penalty)
        """
        coverage = questions_answered / max(total_questions, 1)
        
        # Penalty increases sharply below 70% coverage
        if coverage >= 0.9:
            penalty = 0.0
        elif coverage >= 0.7:
            penalty = (0.9 - coverage) * 0.5
        else:
            penalty = 0.1 + (0.7 - coverage) * 1.0
        
        penalty = min(1.0, penalty)
        
        return coverage, penalty
    
    def compose_macro_portfolio(
        self,
        meso_analyses: List[MesoLevelAnalysis],
        total_questions: int,
        contradiction_scanner: ContradictionScanner
    ) -> MacroLevelAnalysis:
        """
        Compose macro-level portfolio from meso analyses
        """
        if not meso_analyses:
            return MacroLevelAnalysis(
                overall_posterior=0.0,
                coverage_score=0.0,
                coverage_penalty=1.0,
                dispersion_score=0.0,
                dispersion_penalty=0.0,
                contradiction_count=0,
                contradiction_penalty=0.0,
                total_penalty=1.0,
                adjusted_score=0.0,
                cluster_scores={},
                recommendations=["No meso-level data available"]
            )
        
        # Calculate raw overall posterior (mean of meso scores)
        meso_scores = [m.adjusted_score for m in meso_analyses]
        raw_overall = np.mean(meso_scores)
        
        # Calculate coverage
        questions_answered = sum(len(m.micro_scores) for m in meso_analyses)
        coverage_score, coverage_penalty = self.calculate_coverage(
            questions_answered, total_questions
        )
        
        # Calculate portfolio-level dispersion
        dispersion_engine = DispersionEngine()
        dispersion_penalty, dispersion_metrics = dispersion_engine.calculate_dispersion_penalty(meso_scores)
        dispersion_score = 1.0 - dispersion_penalty
        
        # Get contradiction penalty
        contradiction_penalty = contradiction_scanner.calculate_contradiction_penalty()
        contradiction_count = len(contradiction_scanner.contradictions)
        
        # Total penalty
        total_penalty = coverage_penalty + dispersion_penalty + contradiction_penalty
        total_penalty = min(1.0, total_penalty)
        
        # Adjusted score
        adjusted_score = raw_overall * (1 - total_penalty)
        adjusted_score = max(0.0, min(1.0, adjusted_score))
        
        # Extract cluster scores
        cluster_scores = {m.cluster_id: m.adjusted_score for m in meso_analyses}
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            coverage_score, dispersion_score, contradiction_count,
            coverage_penalty, dispersion_penalty, contradiction_penalty
        )
        
        self.logger.info(
            f"Macro portfolio: raw={raw_overall:.3f}, "
            f"coverage_pen={coverage_penalty:.3f}, "
            f"dispersion_pen={dispersion_penalty:.3f}, "
            f"contradiction_pen={contradiction_penalty:.3f}, "
            f"final={adjusted_score:.3f}"
        )
        
        return MacroLevelAnalysis(
            overall_posterior=raw_overall,
            coverage_score=coverage_score,
            coverage_penalty=coverage_penalty,
            dispersion_score=dispersion_score,
            dispersion_penalty=dispersion_penalty,
            contradiction_count=contradiction_count,
            contradiction_penalty=contradiction_penalty,
            total_penalty=total_penalty,
            adjusted_score=adjusted_score,
            cluster_scores=cluster_scores,
            recommendations=recommendations,
            metadata={
                'dispersion_metrics': dispersion_metrics,
                'questions_answered': questions_answered,
                'total_questions': total_questions
            }
        )
    
    def _generate_recommendations(
        self,
        coverage: float,
        dispersion: float,
        contradiction_count: int,
        coverage_penalty: float,
        dispersion_penalty: float,
        contradiction_penalty: float
    ) -> List[str]:
        """Generate strategic recommendations based on portfolio analysis"""
        recommendations = []
        
        if coverage_penalty > 0.1:
            recommendations.append(
                f"Improve question coverage (current: {coverage:.1%}). "
                "Address unanswered questions to reduce coverage penalty."
            )
        
        if dispersion_penalty > 0.1:
            recommendations.append(
                f"Reduce score dispersion across clusters (current penalty: {dispersion_penalty:.2f}). "
                "Focus on bringing lower-performing areas up to standard."
            )
        
        if contradiction_penalty > 0.05:
            recommendations.append(
                f"Resolve {contradiction_count} detected contradictions between levels. "
                "Ensure consistency in assessment across micro/meso/macro."
            )
        
        if not recommendations:
            recommendations.append(
                "Portfolio is well-balanced with good coverage, low dispersion, "
                "and minimal contradictions. Continue current approach."
            )
        
        return recommendations
    
    def export_to_csv(
        self,
        macro_analysis: MacroLevelAnalysis,
        output_path: Path
    ):
        """Export macro posterior table to CSV"""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'metric', 'value', 'penalty', 'description'
            ])
            
            writer.writerow([
                'overall_posterior',
                f"{macro_analysis.overall_posterior:.4f}",
                f"{macro_analysis.total_penalty:.4f}",
                'Raw overall score before penalties'
            ])
            
            writer.writerow([
                'coverage',
                f"{macro_analysis.coverage_score:.4f}",
                f"{macro_analysis.coverage_penalty:.4f}",
                'Question coverage ratio'
            ])
            
            writer.writerow([
                'dispersion',
                f"{macro_analysis.dispersion_score:.4f}",
                f"{macro_analysis.dispersion_penalty:.4f}",
                'Portfolio dispersion score'
            ])
            
            writer.writerow([
                'contradictions',
                str(macro_analysis.contradiction_count),
                f"{macro_analysis.contradiction_penalty:.4f}",
                'Number of detected contradictions'
            ])
            
            writer.writerow([
                'adjusted_score',
                f"{macro_analysis.adjusted_score:.4f}",
                '0.0000',
                'Final penalty-adjusted score'
            ])
        
        self.logger.info(f"Exported macro analysis to {output_path}")


# ============================================================================
# ORCHESTRATOR: COMPLETE MULTI-LEVEL PIPELINE
# ============================================================================

class MultiLevelBayesianOrchestrator:
    """
    Complete orchestration of micro→meso→macro Bayesian analysis pipeline
    """
    
    def __init__(
        self,
        validation_rules: List[ValidationRule],
        output_dir: Path = Path("data/bayesian_outputs")
    ):
        self.validation_rules = validation_rules
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.reconciliation_validator = ReconciliationValidator(validation_rules)
        self.bayesian_updater = BayesianUpdater()
        self.dispersion_engine = DispersionEngine()
        self.peer_calibrator = PeerCalibrator()
        self.bayesian_rollup = BayesianRollUp()
        self.contradiction_scanner = ContradictionScanner()
        self.portfolio_composer = BayesianPortfolioComposer()
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def run_complete_analysis(
        self,
        micro_data: List[Dict[str, Any]],
        cluster_mapping: Dict[str, List[str]],  # cluster_id -> question_ids
        peer_contexts: Optional[List[PeerContext]] = None,
        total_questions: int = 300
    ) -> Tuple[List[MicroLevelAnalysis], List[MesoLevelAnalysis], MacroLevelAnalysis]:
        """
        Run complete multi-level Bayesian analysis
        
        Returns: (micro_analyses, meso_analyses, macro_analysis)
        """
        self.logger.info("=" * 80)
        self.logger.info("MULTI-LEVEL BAYESIAN ANALYSIS PIPELINE")
        self.logger.info("=" * 80)
        
        # MICRO LEVEL
        self.logger.info("\n[1/3] MICRO LEVEL: Reconciliation + Bayesian Updating")
        micro_analyses = self._run_micro_level(micro_data)
        
        # Export micro posteriors
        self.bayesian_updater.export_to_csv(
            self.output_dir / "posterior_table_micro.csv"
        )
        
        # MESO LEVEL
        self.logger.info("\n[2/3] MESO LEVEL: Dispersion + Peer Calibration + Roll-Up")
        meso_analyses = self._run_meso_level(
            micro_analyses, cluster_mapping, peer_contexts
        )
        
        # Export meso posteriors
        self.bayesian_rollup.export_to_csv(
            meso_analyses,
            self.output_dir / "posterior_table_meso.csv"
        )
        
        # MACRO LEVEL
        self.logger.info("\n[3/3] MACRO LEVEL: Contradiction Scan + Portfolio Composition")
        macro_analysis = self._run_macro_level(
            micro_analyses, meso_analyses, total_questions
        )
        
        # Export macro posteriors
        self.portfolio_composer.export_to_csv(
            macro_analysis,
            self.output_dir / "posterior_table_macro.csv"
        )
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("ANALYSIS COMPLETE")
        self.logger.info(f"Final adjusted score: {macro_analysis.adjusted_score:.4f}")
        self.logger.info(f"Outputs saved to: {self.output_dir}")
        self.logger.info("=" * 80)
        
        return micro_analyses, meso_analyses, macro_analysis
    
    def _run_micro_level(
        self, 
        micro_data: List[Dict[str, Any]]
    ) -> List[MicroLevelAnalysis]:
        """Run micro-level analysis"""
        micro_analyses = []
        
        for data in micro_data:
            question_id = data.get('question_id', 'UNKNOWN')
            raw_score = data.get('raw_score', 0.0)
            
            # Reconciliation validation
            validation_results = self.reconciliation_validator.validate_data(data)
            validation_penalty = self.reconciliation_validator.calculate_total_penalty(
                validation_results
            )
            
            # Bayesian updating (using probative tests)
            tests = data.get('probative_tests', [])
            if tests:
                initial_prior = raw_score
                final_posterior = self.bayesian_updater.sequential_update(
                    initial_prior, tests
                )
            else:
                final_posterior = raw_score
            
            # Calculate adjusted score
            adjusted_score = final_posterior * (1 - validation_penalty)
            adjusted_score = max(0.0, min(1.0, adjusted_score))
            
            analysis = MicroLevelAnalysis(
                question_id=question_id,
                raw_score=raw_score,
                validation_results=validation_results,
                validation_penalty=validation_penalty,
                bayesian_updates=self.bayesian_updater.updates[-len(tests):] if tests else [],
                final_posterior=final_posterior,
                adjusted_score=adjusted_score
            )
            
            micro_analyses.append(analysis)
        
        self.logger.info(f"  Processed {len(micro_analyses)} micro-level questions")
        return micro_analyses
    
    def _run_meso_level(
        self,
        micro_analyses: List[MicroLevelAnalysis],
        cluster_mapping: Dict[str, List[str]],
        peer_contexts: Optional[List[PeerContext]]
    ) -> List[MesoLevelAnalysis]:
        """Run meso-level analysis"""
        meso_analyses = []
        
        for cluster_id, question_ids in cluster_mapping.items():
            # Get micro analyses for this cluster
            cluster_micros = [
                m for m in micro_analyses 
                if m.question_id in question_ids
            ]
            
            if not cluster_micros:
                continue
            
            # Get micro scores
            micro_scores = [m.adjusted_score for m in cluster_micros]
            
            # Calculate dispersion
            dispersion_penalty, dispersion_metrics = (
                self.dispersion_engine.calculate_dispersion_penalty(micro_scores)
            )
            
            # Peer calibration
            raw_meso_score = np.mean(micro_scores)
            peer_comparison = None
            peer_penalty = 0.0
            
            if peer_contexts:
                peer_comparison = self.peer_calibrator.compare_to_peers(
                    raw_meso_score, peer_contexts, cluster_id
                )
                peer_penalty = peer_comparison.deviation_penalty
            
            # Bayesian roll-up
            adjusted_score = self.bayesian_rollup.aggregate_micro_to_meso(
                cluster_micros,
                dispersion_penalty,
                peer_penalty
            )
            
            total_penalty = dispersion_penalty + peer_penalty
            
            analysis = MesoLevelAnalysis(
                cluster_id=cluster_id,
                micro_scores=micro_scores,
                raw_meso_score=raw_meso_score,
                dispersion_metrics=dispersion_metrics,
                dispersion_penalty=dispersion_penalty,
                peer_comparison=peer_comparison,
                peer_penalty=peer_penalty,
                total_penalty=total_penalty,
                final_posterior=raw_meso_score,
                adjusted_score=adjusted_score,
                metadata={'question_ids': question_ids}  # Add question_ids to metadata
            )
            
            meso_analyses.append(analysis)
        
        self.logger.info(f"  Processed {len(meso_analyses)} meso-level clusters")
        return meso_analyses
    
    def _run_macro_level(
        self,
        micro_analyses: List[MicroLevelAnalysis],
        meso_analyses: List[MesoLevelAnalysis],
        total_questions: int
    ) -> MacroLevelAnalysis:
        """Run macro-level analysis"""
        # Scan for contradictions
        for meso in meso_analyses:
            # Get question_ids for this meso cluster from metadata or empty list
            meso_question_ids = meso.metadata.get('question_ids', [])
            if not isinstance(meso_question_ids, list):
                meso_question_ids = []
            
            cluster_micros = [
                m for m in micro_analyses 
                if m.question_id in meso_question_ids
            ]
            self.contradiction_scanner.scan_micro_meso(cluster_micros, meso)
        
        # Calculate provisional macro score
        if meso_analyses:
            provisional_macro = np.mean([m.adjusted_score for m in meso_analyses])
            self.contradiction_scanner.scan_meso_macro(meso_analyses, provisional_macro)
        
        # Compose final macro portfolio
        macro_analysis = self.portfolio_composer.compose_macro_portfolio(
            meso_analyses,
            total_questions,
            self.contradiction_scanner
        )
        
        self.logger.info(f"  Detected {macro_analysis.contradiction_count} contradictions")
        self.logger.info(f"  Final macro score: {macro_analysis.adjusted_score:.4f}")
        
        return macro_analysis


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Example usage
    logger.info("Bayesian Multi-Level System initialized")
    logger.info("Ready for integration with report_assembly.py")
