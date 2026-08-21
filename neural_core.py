"""Small, inspectable neural-network primitives for the V8 research pipeline.

The implementation intentionally uses NumPy instead of a large deep-learning
framework.  The complete forward pass, optimizer, calibration and persistence
format can therefore be audited in this repository and run on free GitHub
Actions runners.  It is a probabilistic research model, not an execution or
trading engine.
"""

from __future__ import annotations

import copy
import math
from statistics import NormalDist
from typing import Any, Iterable

import numpy as np

from research_core import PlattCalibrator, Standardizer, fit_platt, sigmoid


EPSILON = 1e-9
PARAMETER_NAMES = ("w1", "b1", "w2", "b2", "w3", "b3")


def _copy_parameters(parameters: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {name: np.asarray(value, dtype=float).copy() for name, value in parameters.items()}


def initialize_parameters(input_size: int, hidden: tuple[int, int], output_size: int, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    first, second = hidden
    return {
        "w1": rng.normal(0, math.sqrt(2 / (input_size + first)), size=(input_size, first)),
        "b1": np.zeros(first),
        "w2": rng.normal(0, math.sqrt(2 / (first + second)), size=(first, second)),
        "b2": np.zeros(second),
        "w3": rng.normal(0, math.sqrt(2 / (second + output_size)), size=(second, output_size)),
        "b3": np.zeros(output_size),
    }


def forward(parameters: dict[str, np.ndarray], values: np.ndarray) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray]]:
    first = np.tanh(values @ parameters["w1"] + parameters["b1"])
    second = np.tanh(first @ parameters["w2"] + parameters["b2"])
    logits = second @ parameters["w3"] + parameters["b3"]
    return logits, (first, second)


def binary_cross_entropy(logits: np.ndarray, target: np.ndarray) -> float:
    # log(1 + exp(x)) - y*x is stable when written with logaddexp.
    return float(np.mean(np.logaddexp(0, logits) - target * logits))


def gradients(
    parameters: dict[str, np.ndarray],
    values: np.ndarray,
    target: np.ndarray,
    *,
    l2: float = 0.0,
    anchor: dict[str, np.ndarray] | None = None,
    importance: dict[str, np.ndarray] | None = None,
    memory_strength: float = 0.0,
) -> dict[str, np.ndarray]:
    logits, (first, second) = forward(parameters, values)
    output_error = (sigmoid(logits) - target) / max(target.size, 1)
    output = {
        "w3": second.T @ output_error,
        "b3": output_error.sum(axis=0),
    }
    second_error = (output_error @ parameters["w3"].T) * (1 - second ** 2)
    output["w2"] = first.T @ second_error
    output["b2"] = second_error.sum(axis=0)
    first_error = (second_error @ parameters["w2"].T) * (1 - first ** 2)
    output["w1"] = values.T @ first_error
    output["b1"] = first_error.sum(axis=0)
    for name in ("w1", "w2", "w3"):
        output[name] += l2 * parameters[name]
    if anchor is not None and importance is not None and memory_strength > 0:
        for name in PARAMETER_NAMES:
            output[name] += memory_strength * importance[name] * (parameters[name] - anchor[name])
    return output


def estimate_diagonal_fisher(
    parameters: dict[str, np.ndarray],
    values: np.ndarray,
    target: np.ndarray,
    *,
    seed: int,
    maximum_rows: int = 1024,
) -> dict[str, np.ndarray]:
    """Approximate diagonal Fisher information from squared mini-batch gradients."""
    rng = np.random.default_rng(seed + 101)
    if len(values) > maximum_rows:
        selection = rng.choice(len(values), maximum_rows, replace=False)
        values = values[selection]
        target = target[selection]
    fisher = {name: np.zeros_like(parameters[name]) for name in PARAMETER_NAMES}
    batches = 0
    for start in range(0, len(values), 64):
        stop = min(start + 64, len(values))
        current = gradients(parameters, values[start:stop], target[start:stop])
        for name in PARAMETER_NAMES:
            fisher[name] += current[name] ** 2
        batches += 1
    for name in PARAMETER_NAMES:
        fisher[name] = fisher[name] / max(batches, 1)
        mean = float(np.mean(fisher[name]))
        if mean > EPSILON:
            fisher[name] /= mean
        fisher[name] = np.clip(fisher[name], 0, 25)
    return fisher


def fit_network(
    training_values: np.ndarray,
    training_target: np.ndarray,
    validation_values: np.ndarray,
    validation_target: np.ndarray,
    *,
    seed: int,
    hidden: tuple[int, int] = (24, 12),
    epochs: int = 140,
    batch_size: int = 512,
    learning_rate: float = 0.004,
    l2: float = 0.002,
    patience: int = 18,
    initial_parameters: dict[str, np.ndarray] | None = None,
    anchor_parameters: dict[str, np.ndarray] | None = None,
    anchor_importance: dict[str, np.ndarray] | None = None,
    memory_strength: float = 0.0,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, float | int]]:
    """Train one deterministic multi-horizon MLP with Adam and early stopping."""
    rng = np.random.default_rng(seed)
    parameters = (
        _copy_parameters(initial_parameters)
        if initial_parameters is not None
        else initialize_parameters(training_values.shape[1], hidden, training_target.shape[1], seed)
    )
    first_moment = {name: np.zeros_like(parameters[name]) for name in PARAMETER_NAMES}
    second_moment = {name: np.zeros_like(parameters[name]) for name in PARAMETER_NAMES}
    best = _copy_parameters(parameters)
    best_loss = float("inf")
    best_epoch = 0
    stale = 0
    step = 0
    for epoch in range(1, epochs + 1):
        indices = rng.permutation(len(training_values))
        for start in range(0, len(indices), batch_size):
            batch = indices[start:start + batch_size]
            current = gradients(
                parameters,
                training_values[batch],
                training_target[batch],
                l2=l2,
                anchor=anchor_parameters,
                importance=anchor_importance,
                memory_strength=memory_strength,
            )
            step += 1
            for name in PARAMETER_NAMES:
                first_moment[name] = .9 * first_moment[name] + .1 * current[name]
                second_moment[name] = .999 * second_moment[name] + .001 * (current[name] ** 2)
                corrected_first = first_moment[name] / (1 - .9 ** step)
                corrected_second = second_moment[name] / (1 - .999 ** step)
                parameters[name] -= learning_rate * corrected_first / (np.sqrt(corrected_second) + 1e-8)
        validation_logits, _ = forward(parameters, validation_values)
        validation_loss = binary_cross_entropy(validation_logits, validation_target)
        if validation_loss < best_loss - 1e-5:
            best = _copy_parameters(parameters)
            best_loss = validation_loss
            best_epoch = epoch
            stale = 0
        else:
            stale += 1
        if stale >= patience:
            break
    fisher = estimate_diagonal_fisher(best, training_values, training_target, seed=seed)
    return best, fisher, {
        "epochsCompleted": epoch,
        "bestEpoch": best_epoch,
        "validationLogLoss": round(best_loss, 8),
    }


def parameters_to_json(parameters: dict[str, np.ndarray], digits: int = 9) -> dict[str, Any]:
    return {name: np.round(parameters[name], digits).tolist() for name in PARAMETER_NAMES}


def parameters_from_json(payload: dict[str, Any]) -> dict[str, np.ndarray]:
    return {name: np.asarray(payload[name], dtype=float) for name in PARAMETER_NAMES}


def standardizer_from_artifact(artifact: dict[str, Any]) -> Standardizer:
    normalization = artifact["normalization"]
    return Standardizer(mean=np.asarray(normalization["mean"], dtype=float), scale=np.asarray(normalization["scale"], dtype=float))


def fit_ensemble(
    training_values: np.ndarray,
    training_target: np.ndarray,
    calibration_values: np.ndarray,
    calibration_target: np.ndarray,
    *,
    features: list[str],
    horizons: list[int],
    seeds: Iterable[int],
    hidden: tuple[int, int] = (24, 12),
    epochs: int = 140,
    l2: float = 0.002,
    warm_artifact: dict[str, Any] | None = None,
    memory_strength: float = 0.0,
) -> dict[str, Any]:
    """Fit a deep ensemble and a temporal Platt/conformal calibration layer."""
    seeds = list(seeds)
    if warm_artifact is not None:
        standardizer = standardizer_from_artifact(warm_artifact)
    else:
        standardizer = Standardizer.fit(training_values)
    train = standardizer.transform(training_values)
    calibration = standardizer.transform(calibration_values)
    members: list[dict[str, Any]] = []
    member_logits: list[np.ndarray] = []
    warm_members = list(warm_artifact.get("members", [])) if warm_artifact else []
    for index, seed in enumerate(seeds):
        warm = warm_members[index % len(warm_members)] if warm_members else None
        initial = parameters_from_json(warm["parameters"]) if warm else None
        importance = parameters_from_json(warm["fisherDiagonal"]) if warm else None
        parameters, fisher, diagnostics = fit_network(
            train,
            training_target,
            calibration,
            calibration_target,
            seed=seed,
            hidden=hidden,
            epochs=epochs,
            l2=l2,
            initial_parameters=initial,
            anchor_parameters=initial,
            anchor_importance=importance,
            memory_strength=memory_strength,
        )
        logits, _ = forward(parameters, calibration)
        member_logits.append(logits)
        members.append({
            "seed": seed,
            "parameters": parameters_to_json(parameters),
            "fisherDiagonal": parameters_to_json(fisher, digits=7),
            "diagnostics": diagnostics,
        })
    mean_logits = np.mean(np.stack(member_logits), axis=0)
    calibration_rows = []
    for output_index, horizon in enumerate(horizons):
        calibrator = fit_platt(mean_logits[:, output_index], calibration_target[:, output_index])
        probability = calibrator.transform(mean_logits[:, output_index])
        residual = np.abs(calibration_target[:, output_index] - probability)
        radius = float(np.quantile(residual, .80, method="higher"))
        calibration_rows.append({
            "horizonSessions": horizon,
            "plattSlope": round(float(calibrator.slope), 10),
            "plattIntercept": round(float(calibrator.intercept), 10),
            "conformalRadius80": round(radius, 8),
            "calibrationRows": int(len(calibration_target)),
        })
    return {
        "schemaVersion": 1,
        "kind": "multi-task-mlp-deep-ensemble",
        "features": features,
        "horizons": horizons,
        "architecture": {
            "input": len(features),
            "hidden": list(hidden),
            "output": len(horizons),
            "activation": "tanh",
            "loss": "binary-cross-entropy",
            "optimizer": "Adam",
            "ensembleMembers": len(members),
        },
        "normalization": {
            "mean": np.round(standardizer.mean, 10).tolist(),
            "scale": np.round(standardizer.scale, 10).tolist(),
            "missingValuePolicy": "training mean",
        },
        "members": members,
        "calibration": calibration_rows,
        "memory": {
            "method": "EWC-style diagonal Fisher anchoring" if warm_artifact else "cold start",
            "strength": memory_strength,
            "parentVersion": warm_artifact.get("version") if warm_artifact else None,
        },
    }


def predict_ensemble(artifact: dict[str, Any], values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    standardizer = standardizer_from_artifact(artifact)
    transformed = standardizer.transform(np.asarray(values, dtype=float))
    logits = []
    for member in artifact["members"]:
        member_logits, _ = forward(parameters_from_json(member["parameters"]), transformed)
        logits.append(member_logits)
    stacked_logits = np.stack(logits)
    mean_logits = np.mean(stacked_logits, axis=0)
    probabilities = np.zeros_like(mean_logits)
    member_probabilities = np.zeros_like(stacked_logits)
    for index, row in enumerate(artifact["calibration"]):
        calibrator = PlattCalibrator(slope=float(row["plattSlope"]), intercept=float(row["plattIntercept"]))
        probabilities[:, index] = calibrator.transform(mean_logits[:, index])
        for member_index in range(len(stacked_logits)):
            member_probabilities[member_index, :, index] = calibrator.transform(stacked_logits[member_index, :, index])
    disagreement = np.std(member_probabilities, axis=0)
    return probabilities, disagreement, mean_logits


def expected_calibration_error(probability: np.ndarray, target: np.ndarray, bins: int = 10) -> float:
    probability = np.asarray(probability, dtype=float).reshape(-1)
    target = np.asarray(target, dtype=float).reshape(-1)
    total = max(len(probability), 1)
    error = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        mask = (probability >= low) & (probability <= high if index == bins - 1 else probability < high)
        if mask.any():
            error += float(mask.sum()) / total * abs(float(probability[mask].mean()) - float(target[mask].mean()))
    return error


def classification_metrics(probability: np.ndarray, target: np.ndarray, horizons: list[int]) -> dict[str, Any]:
    probability = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    target = np.asarray(target, dtype=float)
    overall_brier = float(np.mean((probability - target) ** 2))
    overall_logloss = float(np.mean(-(target * np.log(probability) + (1 - target) * np.log(1 - probability))))
    per_horizon = {}
    for index, horizon in enumerate(horizons):
        current = probability[:, index]
        labels = target[:, index]
        per_horizon[str(horizon)] = {
            "brierScore": round(float(np.mean((current - labels) ** 2)), 8),
            "logLoss": round(float(np.mean(-(labels * np.log(current) + (1 - labels) * np.log(1 - current)))), 8),
            "accuracy": round(float(np.mean((current >= .5) == labels)), 8),
            "ece": round(expected_calibration_error(current, labels), 8),
        }
    return {
        "rows": int(len(target)),
        "probabilities": int(target.size),
        "brierScore": round(overall_brier, 8),
        "logLoss": round(overall_logloss, 8),
        "accuracy": round(float(np.mean((probability >= .5) == target)), 8),
        "ece": round(expected_calibration_error(probability, target), 8),
        "perHorizon": per_horizon,
    }


def temporal_block_win_rate(
    candidate: np.ndarray,
    reference: np.ndarray,
    target: np.ndarray,
    dates: np.ndarray,
    *,
    blocks: int = 4,
) -> tuple[float, list[dict[str, Any]]]:
    unique_dates = np.asarray(sorted(np.unique(dates)))
    partitions = [part for part in np.array_split(unique_dates, blocks) if len(part)]
    output = []
    wins = 0
    for index, part in enumerate(partitions):
        mask = np.isin(dates, part)
        candidate_brier = float(np.mean((candidate[mask] - target[mask]) ** 2))
        reference_brier = float(np.mean((reference[mask] - target[mask]) ** 2))
        won = candidate_brier < reference_brier
        wins += int(won)
        output.append({
            "block": index + 1,
            "start": str(np.datetime_as_string(part[0], unit="D")),
            "end": str(np.datetime_as_string(part[-1], unit="D")),
            "candidateBrier": round(candidate_brier, 8),
            "referenceBrier": round(reference_brier, 8),
            "won": won,
        })
    return wins / max(len(output), 1), output


def promotion_gate(reference: dict[str, Any], candidate: dict[str, Any], *, trial_count: int) -> tuple[bool, dict[str, bool], float]:
    rows = max(int(candidate.get("rows", 0)), 1)
    # Small but explicit multiple-testing penalty. More attempted challengers
    # require a larger improvement before replacing the frozen champion.
    required_improvement = max(.001, .018 * math.sqrt(math.log(max(trial_count, 2)) / rows))
    reference_horizons = reference.get("perHorizon", {})
    candidate_horizons = candidate.get("perHorizon", {})
    horizon_wins = sum(
        float(candidate_horizons[key]["brierScore"]) < float(reference_horizons[key]["brierScore"])
        for key in candidate_horizons
        if key in reference_horizons
    )
    checks = {
        "minimumShadowSample": rows >= 600,
        "trialAdjustedBrierImprovement": float(reference["brierScore"]) - float(candidate["brierScore"]) >= required_improvement,
        "logLossImprovement": float(candidate["logLoss"]) < float(reference["logLoss"]),
        "calibrationNotWorse": float(candidate["ece"]) <= float(reference["ece"]) + .01,
        "twoOfThreeHorizonsImprove": horizon_wins >= 2,
        "temporalStability": float(candidate.get("temporalBlockWinRate", 0)) >= .5,
    }
    return all(checks.values()), checks, required_improvement


def ablation_sensitivity(artifact: dict[str, Any], values: np.ndarray, maximum_rows: int = 2000) -> list[dict[str, Any]]:
    sample = np.asarray(values, dtype=float)
    if len(sample) > maximum_rows:
        selection = np.linspace(0, len(sample) - 1, maximum_rows, dtype=int)
        sample = sample[selection]
    baseline, _, _ = predict_ensemble(artifact, sample)
    standardizer = standardizer_from_artifact(artifact)
    output = []
    for index, feature in enumerate(artifact["features"]):
        ablated = sample.copy()
        ablated[:, index] = standardizer.mean[index]
        probability, _, _ = predict_ensemble(artifact, ablated)
        output.append({
            "feature": feature,
            "meanAbsoluteProbabilityChange": round(float(np.mean(np.abs(probability - baseline))), 8),
            "method": "Reemplazar la variable por la media de entrenamiento; sensibilidad, no causalidad",
        })
    return sorted(output, key=lambda row: float(row["meanAbsoluteProbabilityChange"]), reverse=True)


def deflated_sharpe_probability(returns: np.ndarray, *, trials: int) -> float | None:
    """Diagnostic DSR probability for sufficiently independent return blocks.

    This is deliberately not used as a promotion gate when the number of
    non-overlapping observations is too small.
    """
    values = np.asarray(returns, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 20 or float(values.std(ddof=1)) < EPSILON:
        return None
    standardized = (values - values.mean()) / values.std(ddof=1)
    sharpe = float(values.mean() / values.std(ddof=1))
    skew = float(np.mean(standardized ** 3))
    kurtosis = float(np.mean(standardized ** 4))
    variance = max((1 - skew * sharpe + ((kurtosis - 1) / 4) * sharpe ** 2) / (len(values) - 1), EPSILON)
    trial_variance = max(1 / max(len(values) - 1, 1), EPSILON)
    normal = NormalDist()
    count = max(int(trials), 2)
    euler_gamma = .5772156649
    expected_max = math.sqrt(trial_variance) * (
        (1 - euler_gamma) * normal.inv_cdf(1 - 1 / count)
        + euler_gamma * normal.inv_cdf(1 - 1 / (count * math.e))
    )
    return float(normal.cdf((sharpe - expected_max) / math.sqrt(variance)))


def clone_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(artifact)
