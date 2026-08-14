# Q049 · Why don’t the orbits of planets decay and cause them to crash into each other?

Gravity keeps planets in stable orbits around the sun. Yet orbits do decay very gradually. Eventually, the planets will swirl into the sun.

## Direction
Baseline Conservative Dynamics Verification

Isolate pure Newtonian gravity in a Sun-Earth two-body system to establish a zero-dissipation baseline and quantify numerical versus physical orbital drift.

## Learned
- High-precision numerical integration of a conservative two-body system yields bounded, oscillatory energy deviations over short timescales.
- Explicit Runge-Kutta methods lack the geometric structure required to preserve the symplectic 2-form or modified Hamiltonian over long durations.
- Theoretical claims regarding symplectic integrator stability require empirical validation using appropriate geometric solvers rather than standard ODE methods.

## Evidence
- Empirical execution demonstrates a maximum energy deviation of 1.40e-08 over a 100-unit integration window using RK45.
- Literature defines symplectic integrators as canonical transformations that conserve the symplectic 2-form, distinguishing them from non-symplectic schemes.
- No simulation logs, plots, or long-term metrics were provided to substantiate the claimed 10^6-year semi-major axis conservation.

## Limitations
- Cannot establish long-term orbital stability or quantify physical versus numerical drift over million-year scales.
- Fails to validate modified Hamiltonian preservation or backward-error bounds due to solver-class mismatch and truncated integration horizon.
- Relies on aggregated scalar metrics rather than full time-series residuals, obscuring oscillatory behavior and potential resonance crossings.

## Open Questions
- How do true symplectic algorithms quantitatively outperform non-symplectic methods in conserving orbital elements across extended integration windows?
- Which non-conservative perturbation mechanism exerts the dominant influence on secular orbital decay within the target system?
- What integration strategies maintain numerical stability when transitioning from conservative Hamiltonian dynamics to dissipative perturbations?

## Next Moves
- Replace the explicit RK45 solver with a verified symplectic integrator (e.g., Stormer-Verlet or implicit midpoint) and re-execute the baseline simulation.
- Extend the integration horizon and output full energy/time-series residuals to empirically confirm bounded deviation and assess convergence rates.
- Perform a dominant timescale analysis to identify and prioritize the first non-conservative perturbation for model extension.
- Develop or adapt non-canonical geometric integrators to safely introduce dissipative forces without triggering artificial energy blow-up.

## Artifacts
- Log: `logs/attempt-22da415b81a4f067ba9b9285.log`
- Log: `logs/attempt-9d222b239f8b691278f50743.log`
- Log: `logs/attempt-e8a716875fdef7b6f05876b4.log`
- Log: `logs/attempt-82bcb327764d9f837c222b18.log`
- Log: `logs/attempt-85315dc99fe31aee87118a1c.log`
- Log: `logs/attempt-e8f2c7bf786c44950f27b3e2.log`
- Log: `logs/attempt-ee61fbd90b25ebeaf8689342.log`
- Log: `logs/attempt-0c305bf6961d83af355d1222.log`
- Log: `logs/attempt-ae5bc1f04c2e2bef82682fde.log`
- Log: `logs/attempt-d99ce0c287d783177e128d44.log`
- Log: `logs/attempt-d193dcd4f172e7cc2414d9ba.log`
- Log: `logs/attempt-87531a1227cd5246d27478ea.log`
- Code: `research-code/experiment.py`

## Work Items
- `source`: completed (3 steps)
- `claim`: completed (3 steps)
- `experiment`: completed (4 steps)
- `report`: completed (3 steps)

## Review Findings
- `info` `RESULT-ARTIFACT-MISMATCH`: Replace the generic theoretical definition with direct outputs, logs, or plots from the specific high-precision simulation. Provide quantitative metrics or time-series data demonstrating semi-major axis conservation over the 10^6-year interval to substantiate the completion test.
- `info` `RESULT-ARTIFACT-MISMATCH`: Replace the generic theoretical definition with direct outputs, logs, or plots from the specific high-precision simulation. Provide quantitative metrics or time-series data demonstrating semi-major axis conservation over the 10^6-year interval to substantiate the completion test.
- `major` `SCOPE-INFLATE`: Replace the explicit Runge-Kutta (RK45) solver with a true symplectic integrator (e.g., Stormer-Verlet or implicit midpoint) to empirically validate the modified Hamiltonian preservation claim. Restrict the inference scope to short-time integration bounds for the current RK45 setup, as it lacks the geometric structure required for long-term energy conservation.
- `minor` `SELECTIVE-REPORTING`: Report the full energy time-series or aggregate statistics (min, max, mean) to empirically validate the 'oscillatory' claim in the expected observation, rather than relying solely on a single scalar maximum deviation.
- `info` `RESULT-ARTIFACT-MISMATCH`: Replace the generic theoretical definition with direct outputs, logs, or plots from the specific high-precision simulation. Provide quantitative metrics or time-series data demonstrating semi-major axis conservation over the 10^6-year interval to substantiate the completion test.
- `major` `SCOPE-INFLATE`: Replace the explicit Runge-Kutta (RK45) solver with a true symplectic integrator (e.g., Stormer-Verlet or implicit midpoint) to empirically validate the modified Hamiltonian preservation claim. Restrict the inference scope to short-time integration bounds for the current RK45 setup, as it lacks the geometric structure required for long-term energy conservation.
