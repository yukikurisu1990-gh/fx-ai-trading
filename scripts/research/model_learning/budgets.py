"""The two feasibility budgets for learning a mapping from 4.674 seen years.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Both budgets are **signal-blind** — properties of a design, computable before a
byte of price is read — and both are denominated in **years**. That is the whole
point of this module, and it is not obvious, so the derivations are written out.

The capacity budget
-------------------

A design produces `T` dates a year carrying `D_eff` effectively independent bets
each; the model has `p` effective parameters; the strategy's target is an annual
information ratio `IR`.

1. A portfolio aggregating `D_eff` independent bets on each of `T` dates reaches
   `IR = rho * sqrt(D_eff * T)`, where `rho` is the per-observation correlation
   between the true prediction and the realised return. So
   `R2_true = rho^2 = IR^2 / (D_eff * T)`.
2. Fitting `p` parameters on `N_eff = D_eff * T * years` effectively independent
   rows costs an expected out-of-sample `R2` of `p / N_eff` — the standard
   least-squares optimism, `sigma^2 p / N` in risk units.
3. The fitted model beats a constant out of sample only if
   `R2_true > p / N_eff`, i.e.

       IR^2 / (D_eff * T)  >  p / (D_eff * T * years)

   and `D_eff` and `T` **cancel**:

       p  <  IR^2 * years                                          (capacity)

⭐ Neither sampling frequency nor cross-sectional breadth relaxes it. Going from
M15 to M1 multiplies the rows by fifteen and divides the per-row signal by
fifteen; adding currencies multiplies the rows and divides the per-bet signal the
same way, because the portfolio IR that defines the target already aggregates
them. "There are 116,418 bars per pair" is not an answer to "how many parameters
may I fit", and this programme has treated it as one before.

Retaining a fraction of the signal rather than merely breaking even needs

       p  <=  (1 - retention) * IR^2 * years

so keeping half of a target `IR = 1.0` over 4.674 years allows `p <= 2.3`.

Where this can fail, stated rather than hidden
----------------------------------------------

* It is a least-squares result. For a tree ensemble `p` is the **effective**
  degrees of freedom, which is far larger than a naive parameter count and is
  estimated here with a documented approximation that errs high.
* It assumes the model form can represent the signal. Misspecification only
  makes the left-hand side worse.
* `IR` is the **net** annual ratio the design is aiming at. A large gross `R2`
  that cost destroys would permit more parameters and earn nothing, so the net
  normalisation is the economically meaningful one.
* For a representation whose value is downstream — a regime state, a volatility
  forecast — the `IR` that belongs in the budget is the **consumer's**, not the
  representation's. `role_gate` enforces that distinction.

The search budget
-----------------

A candidate's walk-forward annualised IR measured over `Y` out-of-fold years has
a standard error of about `1 / sqrt(Y)`. Choosing the best of `M_eff` effectively
independent candidates that are in truth equally worthless inflates the winner's
estimate by `E[max of M_eff standard normals] / sqrt(Y)`. For that inflation not
to swamp the smallest improvement worth adopting, `MRIE`:

       z_max(M_eff)  <=  MRIE * sqrt(Y)                             (search)

⭐ Years again, not bars. And `M_eff = 1 + (M_nominal - 1) * (1 - rho_config)`,
so neighbouring hyperparameters are cheap and genuinely different architectures
are expensive — which is the opposite of how a grid search spends its budget.

What neither budget covers
--------------------------

The three seen spans have already been screened by roughly 1,200 configurations
across twenty-one recorded hypotheses. That multiplicity is real, is not this
phase's to spend, and cannot be corrected away by a budget that only counts this
phase's fits. It is disclosed, and the only thing that actually protects against
it is an evaluation on data nobody has seen — which is not this phase.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

from scipy import stats as scipy_stats

from scripts.research.model_learning import MAX_PLAUSIBLE_GROSS_IR, TRAIN_YEARS_TOTAL

#: The smallest incremental annual information ratio worth adopting over the
#: baseline the candidate has to beat. Frozen here so that a later stage cannot
#: buy itself a larger search by lowering it.
MINIMUM_RELEVANT_INCREMENTAL_IR: Final[float] = 0.5

#: The fraction of the true signal a fitted model must be expected to retain.
#: Break-even (`0.0`) means the model is expected to tie a constant out of
#: sample, which is not a reason to fit anything.
REQUIRED_SIGNAL_RETENTION: Final[float] = 0.5

#: Average correlation assumed between configurations inside one pre-registered
#: family — neighbouring hyperparameters of one architecture. Genuinely different
#: architectures are counted as separate families, not discounted by this.
WITHIN_FAMILY_CONFIG_CORRELATION: Final[float] = 0.70

#: Recorded so that a reader meets it beside the budgets it does not enter.
PRIOR_SCREENING_CONFIGURATIONS_APPROX: Final[int] = 1200


class BudgetError(ValueError):
    """Raised when a budget is asked for something it cannot answer."""


# ------------------------------------------------------------ capacity budget
def admissible_parameters(
    target_annual_ir: float,
    train_years: float = TRAIN_YEARS_TOTAL,
    *,
    retention: float = REQUIRED_SIGNAL_RETENTION,
) -> float:
    """`p <= (1 - retention) * IR^2 * years`. Breadth and frequency do not enter."""
    if target_annual_ir <= 0.0:
        raise BudgetError("a design with no target information ratio has no capacity")
    if train_years <= 0.0:
        raise BudgetError("no training years, no parameters")
    if not 0.0 <= retention < 1.0:
        raise BudgetError(f"retention {retention} is not in [0, 1)")
    return (1.0 - retention) * target_annual_ir**2 * train_years


def expected_out_of_sample_retention(
    effective_parameters: float,
    target_annual_ir: float,
    train_years: float = TRAIN_YEARS_TOTAL,
) -> float:
    """The fraction of the true signal the fit is expected to keep.

    `1 - p / (IR^2 * years)`, clipped at zero: a model past break-even does not
    have negative signal, it has none, and reporting a negative fraction invites
    it to be read as a quantity that could be traded against.
    """
    if target_annual_ir <= 0.0 or train_years <= 0.0:
        raise BudgetError("retention is undefined without a target and a horizon")
    return max(0.0, 1.0 - effective_parameters / (target_annual_ir**2 * train_years))


#: Effective degrees of freedom by model class, as functions of their own
#: settings. Each errs **high** where it is uncertain, because a budget that
#: under-counts capacity is a budget that licenses overfitting.
def effective_parameters(model_class: str, **settings: float) -> float:
    """Effective degrees of freedom for the model classes this phase may use.

    The approximations, with their sources of error named:

    * `constant` — zero. A baseline fits nothing.
    * `linear` — the number of coefficients, or the ridge trace
      `sum(d_i^2 / (d_i^2 + lam))` when a shrinkage factor is supplied. Exact for
      OLS, and the ridge form is exact given the singular values; the caller
      normally supplies an effective fraction instead, which errs high.
    * `boosted_trees` — `n_trees * leaves * learning_rate`, the usual working
      estimate of boosting's effective degrees of freedom. It is an
      approximation and it is the one most likely to be wrong, so it is used only
      to show that the admissible capacity is exceeded by orders of magnitude,
      never to argue that a particular ensemble just fits.
    * `regime_linear` — `states * (coefficients + 1)`, the per-state coefficients
      plus the state boundary each one costs.
    * `regime_intercept_linear` — `coefficients * shrinkage + states`. Shared
      slopes with a regime-dependent level, which is what the capacity budget can
      afford where a full per-regime mapping is not.
    * `ranking_linear` — the shared coefficient vector. A cross-sectional model
      with shared coefficients does **not** pay per asset, which is the one
      architectural choice the capacity budget rewards.
    """
    name = model_class.strip().lower()
    if name == "constant":
        return 0.0
    if name in {"linear", "ranking_linear"}:
        coefficients = float(settings.get("coefficients", 0.0))
        shrinkage = float(settings.get("effective_fraction", 1.0))
        if not 0.0 < shrinkage <= 1.0:
            raise BudgetError(f"effective_fraction {shrinkage} is not in (0, 1]")
        return coefficients * shrinkage
    if name == "regime_linear":
        states = float(settings.get("states", 1.0))
        coefficients = float(settings.get("coefficients", 0.0))
        return states * (coefficients + 1.0)
    if name == "regime_intercept_linear":
        #: Shared slopes, a regime-dependent intercept (or scale). ⭐ The only
        #: affordable form of regime conditioning on 4.674 years: a separate
        #: mapping per state multiplies the coefficient count by the state count,
        #: while a state-dependent level adds to it.
        states = float(settings.get("states", 1.0))
        coefficients = float(settings.get("coefficients", 0.0))
        shrinkage = float(settings.get("effective_fraction", 1.0))
        if not 0.0 < shrinkage <= 1.0:
            raise BudgetError(f"effective_fraction {shrinkage} is not in (0, 1]")
        return coefficients * shrinkage + states
    if name == "boosted_trees":
        trees = float(settings.get("trees", 0.0))
        leaves = float(settings.get("leaves", 0.0))
        rate = float(settings.get("learning_rate", 1.0))
        return trees * leaves * rate
    raise BudgetError(f"no effective-parameter estimate is defined for {model_class!r}")


# -------------------------------------------------------------- search budget
def expected_max_of_standard_normals(m: float) -> float:
    """Blom's approximation to `E[max of m standard normals]`.

    `Phi^-1((m - 0.375) / (m + 0.25))`. It **overstates** the expectation by
    about 0.02 at small `m` — 0.589 against an exact 0.564 at m = 2, 0.869
    against 0.846 at m = 3 — and the error shrinks as `m` grows. Overstating is
    the safe direction for a budget: it charges a search slightly more inflation
    than it truly costs, so a design that passes would also pass under the exact
    value.

    At `m = 1` the expression is exactly `Phi^-1(0.5) = 0`, with no special case:
    a search over one candidate selects nothing and costs nothing, and the
    formula already says so.
    """
    if m < 1.0:
        raise BudgetError(f"a search over {m} candidates is not a search")
    return float(scipy_stats.norm.ppf((m - 0.375) / (m + 0.25)))


def effective_configurations(
    nominal: int, *, correlation: float = WITHIN_FAMILY_CONFIG_CORRELATION
) -> float:
    """`1 + (M - 1) * (1 - rho)`. Neighbouring settings are nearly one candidate."""
    if nominal < 1:
        raise BudgetError("a family with no configurations is not a family")
    if not 0.0 <= correlation < 1.0:
        raise BudgetError(f"correlation {correlation} is not in [0, 1)")
    return 1.0 + (nominal - 1) * (1.0 - correlation)


def selection_inflation_ir(
    nominal_configurations: int,
    validation_years: float,
    *,
    correlation: float = WITHIN_FAMILY_CONFIG_CORRELATION,
) -> float:
    """Annual IR a winner gains purely by being the best of the set."""
    if validation_years <= 0.0:
        raise BudgetError("selection on no validation years is selection on nothing")
    m_eff = effective_configurations(nominal_configurations, correlation=correlation)
    return expected_max_of_standard_normals(m_eff) / math.sqrt(validation_years)


def admissible_configurations(
    validation_years: float,
    *,
    minimum_relevant_incremental_ir: float = MINIMUM_RELEVANT_INCREMENTAL_IR,
    correlation: float = WITHIN_FAMILY_CONFIG_CORRELATION,
    ceiling: int = 4096,
) -> int:
    """The largest nominal configuration count whose selection inflation is bearable.

    Searched upward rather than inverted in closed form: Blom's approximation has
    no clean inverse, the answer is small, and a loop that stops at the first
    failure cannot accidentally report a count it never checked.
    """
    if validation_years <= 0.0:
        raise BudgetError("no validation years, no admissible search")
    allowed = 0
    for nominal in range(1, ceiling + 1):
        inflation = selection_inflation_ir(nominal, validation_years, correlation=correlation)
        if inflation > minimum_relevant_incremental_ir:
            break
        allowed = nominal
    return allowed


# ------------------------------------------------------------------- reporting
@dataclass(frozen=True, slots=True)
class BudgetVerdict:
    """Both budgets for one design, with the binding one named."""

    capacity_admissible_parameters: float
    capacity_declared_parameters: float
    capacity_ok: bool
    expected_retention: float
    search_admissible_configurations: int
    search_declared_configurations: int
    search_ok: bool
    selection_inflation_ir: float
    binding: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "capacity": {
                "admissible_effective_parameters": round(self.capacity_admissible_parameters, 3),
                "declared_effective_parameters": round(self.capacity_declared_parameters, 3),
                "expected_signal_retention": round(self.expected_retention, 4),
                "ok": self.capacity_ok,
            },
            "search": {
                "admissible_configurations": self.search_admissible_configurations,
                "declared_configurations": self.search_declared_configurations,
                "selection_inflation_annual_ir": round(self.selection_inflation_ir, 4),
                "ok": self.search_ok,
            },
            "binding": self.binding,
            "ok": self.capacity_ok and self.search_ok,
        }


def assess(
    *,
    target_annual_ir: float,
    declared_effective_parameters: float,
    declared_configurations: int,
    train_years: float = TRAIN_YEARS_TOTAL,
    validation_years: float,
    retention: float = REQUIRED_SIGNAL_RETENTION,
    minimum_relevant_incremental_ir: float = MINIMUM_RELEVANT_INCREMENTAL_IR,
    correlation: float = WITHIN_FAMILY_CONFIG_CORRELATION,
) -> BudgetVerdict:
    """Both budgets, and which one binds.

    `binding` names a **failing** budget. A verdict that passes has no binding
    constraint, and an earlier stage of this programme shipped a field that
    sometimes named a condition the design had satisfied.
    """
    if target_annual_ir > MAX_PLAUSIBLE_GROSS_IR:
        raise BudgetError(
            f"a target annual IR of {target_annual_ir} exceeds the frozen plausibility "
            f"ceiling {MAX_PLAUSIBLE_GROSS_IR}; raising the target is how a capacity "
            "budget gets talked into permitting a larger model"
        )
    allowed_p = admissible_parameters(target_annual_ir, train_years, retention=retention)
    capacity_ok = declared_effective_parameters <= allowed_p
    allowed_m = admissible_configurations(
        validation_years,
        minimum_relevant_incremental_ir=minimum_relevant_incremental_ir,
        correlation=correlation,
    )
    search_ok = declared_configurations <= allowed_m
    binding: str | None = None
    if not capacity_ok and not search_ok:
        #: Report the one that is exceeded by the larger factor, so the reader is
        #: pointed at the change that would actually move the design.
        capacity_ratio = declared_effective_parameters / max(allowed_p, 1e-9)
        search_ratio = declared_configurations / max(allowed_m, 1e-9)
        binding = "capacity" if capacity_ratio >= search_ratio else "search"
    elif not capacity_ok:
        binding = "capacity"
    elif not search_ok:
        binding = "search"
    return BudgetVerdict(
        capacity_admissible_parameters=allowed_p,
        capacity_declared_parameters=declared_effective_parameters,
        capacity_ok=capacity_ok,
        expected_retention=expected_out_of_sample_retention(
            declared_effective_parameters, target_annual_ir, train_years
        ),
        search_admissible_configurations=allowed_m,
        search_declared_configurations=declared_configurations,
        search_ok=search_ok,
        selection_inflation_ir=selection_inflation_ir(
            declared_configurations, validation_years, correlation=correlation
        ),
        binding=binding,
    )


def budget_table() -> dict[str, Any]:
    """The capacity budget across the target ratios this programme argues about.

    Signal-free: every entry is `(1 - retention) * IR^2 * years`.
    """
    rows: dict[str, Any] = {"_unit": "effective parameters"}
    for ir in (0.25, 0.5, 0.75, 1.0, 1.25, MAX_PLAUSIBLE_GROSS_IR):
        rows[f"ir_{ir:g}_break_even"] = round(admissible_parameters(ir, retention=0.0), 3)
        rows[f"ir_{ir:g}_retain_half"] = round(admissible_parameters(ir, retention=0.5), 3)
    return {
        "train_years": TRAIN_YEARS_TOTAL,
        "identity": "p <= (1 - retention) * IR_annual^2 * train_years",
        "frequency_and_breadth_cancel": True,
        "parameters": rows,
    }


__all__ = [
    "MINIMUM_RELEVANT_INCREMENTAL_IR",
    "PRIOR_SCREENING_CONFIGURATIONS_APPROX",
    "REQUIRED_SIGNAL_RETENTION",
    "WITHIN_FAMILY_CONFIG_CORRELATION",
    "BudgetError",
    "BudgetVerdict",
    "admissible_configurations",
    "admissible_parameters",
    "assess",
    "budget_table",
    "effective_configurations",
    "effective_parameters",
    "expected_max_of_standard_normals",
    "expected_out_of_sample_retention",
    "selection_inflation_ir",
]
