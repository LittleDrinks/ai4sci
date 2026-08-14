# Q013 · Can we predict the next pandemic?

There will be other pandemics, perhaps in the next few decades, writes David Murdoch, Dean and Head of Campus at the University of Otago in Christchurch, New Zealand, in The Conversation. This prediction, he adds, is driven by the fact that epidemics are occurring more frequently, such as those caused by the SARS, Zika, and Ebola viruses, and are spurred by human-caused environmental and societal changes. The question of determining the timing and location of a pandemic is a complicated one. Pandemic prediction is multidisciplinary, requiring collaboration between experts in infectious disease, epidemiology, public health, public health policy, sociology, psychology, human behavior, climate and environmental science, data science, computer science, and crisis communications. Murdoch notes that we can heed lessons from COVID-19. These include boosting support for pandemic preparedness; surge capacity in health systems, laboratories, and supply-chain logistics; and public health communications.

Data scientists, harnessing more robust computer power and capabilities, have taken a lead role in predicting the next pandemic. Zoonosis is a special area of focus, whereby an infectious disease skips from an animal host to a human. Tracking zoonosis is highly challenging. However, researchers like David Redding of the Institute of Zoology in London are crafting powerful prediction models that can mine data harvested from perturbations in the environment and society, including deforestation expansion, animal movement, climate change, and transportation. Through modeling, Redding’s team predicted the location of the last three outbreaks. However, the timing of such outbreaks remains elusive.

The Global Virome Project, a USD 4 billion (RMB 25.7 billion) international effort, is aimed at transforming how we find and monitor infectious diseases. The goal is to improve the robustness and accessibility of such predictions in a manner akin to current weather prediction and surveillance. Zoonotic disease transmission prediction has traditionally been tied to surveillance and preparedness. This project aims to proactively plan and ultimately predict pandemics by building the capacity to identify, genetically catalog, and track upwards of 500,000 viruses that have the potential for spillover to humans. By seeking to better comprehend the complex web that links human health, ecology, and virology with zoonosis, we can begin to predict the next pandemics.

## Direction
Historical Outbreak Risk Backtesting

Translate Redding’s environmental and societal perturbation models into a formal forecasting framework by defining prediction horizons, spatial targets, and statistical baselines, enabling retrospective scoring against known zoonotic spillovers like SARS, Zika, and Ebola.

## Learned
- Deterministic mass-action models assuming homogeneous host mixing systematically overestimate spillover risk at low contact rates and underestimate it at high rates.
- Synthetic calibration demonstrates that baseline transmission functions require stochastic adjustments to capture episodic, heterogeneous wildlife-livestock-human interfaces.
- Retrospective spatial analyses confirm that landscape alteration, climate variables, and healthcare accessibility gradients are primary drivers of zoonotic spillover clustering.

## Evidence
- Characterizes multi-stage SARS-like coronavirus spillover risks across direct and indirect transmission pathways, identifying high-risk clusters proximate to healthcare facilities.
- Projects climate-driven habitat suitability shifts for human monkeypox in Central Africa under IPCC scenarios, highlighting forest clearing and climatic variables as transmission catalysts.
- Establishes foundational mathematical baselines for cross-species transmission probability using mass-action principles, though limited to theoretical derivation without empirical validation.
- Maps spatiotemporal fluctuations and environmental triggers for historical Ebola virus spillover events to identify recurring precursors.

## Limitations
- Cannot deliver rigorous backtesting or calibrated probability scores against real historical outbreak datasets due to reliance on synthetic proxies and absence of empirical field data.
- Homogeneous mixing assumptions fail to model stochastic spillover dynamics, reporting lags, and multi-pathway transmission networks required for operational forecasting.
- Reliance on outdated IPCC Fourth Assessment climate scenarios and static ecological niche modeling restricts the accuracy of future range-shift projections.
- Proximity-based healthcare access metrics conflate geographic adjacency with functional diagnostic capacity, ignoring socioeconomic and infrastructure barriers.

## Open Questions
- How can stochastic branching-process models be integrated with real-time ecological monitoring to establish empirically validated early-warning thresholds?
- What are the precise temporal resolution limits and systematic bias profiles when transitioning from theoretical baselines to retrospective backtesting against curated outbreak records?
- How do dynamic land-use governance, vector adaptation, and anthropogenic mobility interact with current climate ensembles (AR6) to alter projected spillover hotspots?

## Next Moves
- Replace the deterministic mass-action baseline with stochastic branching-process models that incorporate contact heterogeneity and episodic interface dynamics.
- Execute formal retrospective backtesting against verified historical datasets (SARS, Zika, Ebola) using updated IPCC AR6 climate ensembles and dynamic land-cover change models.
- Integrate standardized travel-time metrics and health-system readiness indices to replace ambiguous distance proxies for healthcare accessibility.
- Define and stress-test probabilistic early-warning thresholds based on empirically calibrated outputs before considering prospective operational deployment.

## Artifacts
- Log: `logs/attempt-65418de675cbc2e47cbf4d89.log`
- Log: `logs/attempt-fd63d8e3b9d435b97401a4fa.log`
- Log: `logs/attempt-fbeeb75430b5bda8477a5bb3.log`
- Log: `logs/attempt-a9f8e6bc568edd488a201b2b.log`
- Log: `logs/attempt-0cab23eda9bbe6c084c30aef.log`
- Log: `logs/attempt-c67055f3b6b15afb01b73167.log`
- Log: `logs/attempt-d5a2183f9cbe5317383d664a.log`
- Log: `logs/attempt-9420c126411eb1fe9b054395.log`
- Log: `logs/attempt-9cd62ce4ade426c439e2f18b.log`
- Log: `logs/attempt-c926c9bdc5d007ce139af3d6.log`
- Log: `logs/attempt-8e082a2a1019d3d19b78269d.log`
- Log: `logs/attempt-e588d2ba54d5e4a8a4cda53e.log`
- Code: `research-code/mass_action_calibration.py`

## Work Items
- `source`: completed (3 steps)
- `claim`: completed (3 steps)
- `experiment`: completed (4 steps)
- `report`: completed (3 steps)

## Review Findings
- `minor` `CITE-CONTEXT`: Explicitly include Zika virus literature and clarify the specific backtesting methodology to ensure citation context tightly matches the stated directional scope.
- `major` `SCOPE-INFLATE`: Refrain from claiming 'rigorous backtesting' and 'calibrated probability scores' until empirical validation is performed; restrict scope to the descriptive, theoretical, and historical trigger analyses currently supported.
- `major` `ARGUMENT-CHAIN-BREAK`: Bridge the gap between theoretical/historical modeling and operational forecasting by providing intermediate empirical validation steps or citing studies that successfully demonstrate model calibration against historical data.
- `major` `RESULT-ARTIFACT-MISMATCH`: Produce or reference artifacts containing actual backtest outputs, bias quantification, and temporal resolution limits to satisfy the completion test criteria.
- `minor` `CITE-CONTEXT`: Explicitly include Zika virus literature and clarify the specific backtesting methodology to ensure citation context tightly matches the stated directional scope.
- `major` `SCOPE-INFLATE`: Refrain from claiming 'rigorous backtesting' and 'calibrated probability scores' until empirical validation is performed; restrict scope to the descriptive, theoretical, and historical trigger analyses currently supported.
- `major` `ARGUMENT-CHAIN-BREAK`: Bridge the gap between theoretical/historical modeling and operational forecasting by providing intermediate empirical validation steps or citing studies that successfully demonstrate model calibration against historical data.
- `major` `RESULT-ARTIFACT-MISMATCH`: Produce or reference artifacts containing actual backtest outputs, bias quantification, and temporal resolution limits to satisfy the completion test criteria.
- `minor` `CITE-CONTEXT`: Clarify that obs_contacts and obs_events are illustrative synthetic proxies rather than cited historical records to prevent misinterpretation of data provenance.
- `minor` `SCOPE-INFLATE`: Restrict all downstream inferences to mathematical demonstration; explicitly defer operational forecasting claims until stochastic branching-process models are implemented per the rebuttal repair.
- `info` `ARGUMENT-CHAIN-BREAK`: Accept the theoretical boundary as established; transition to stochastic modeling to bridge the gap to empirical validation.
- `info` `RESULT-ARTIFACT-MISMATCH`: No adjustment required; the artifact successfully validates the synthetic calibration routine and matches planned metrics.
- `minor` `METHOD-DRIFT`: Align the execution command with the plan specification by using 'python3' instead of 'python' to ensure strict procedural fidelity, although the functional outcome remains identical.
- `major` `SCOPE-INFLATE`: Restrict claims to descriptive driver characterization and theoretical baselines until empirical backtesting against curated outbreak datasets is completed.
- `major` `ARGUMENT-CHAIN-BREAK`: Bridge the theoretical demonstration to operational forecasting by implementing stochastic branching-process models and validating them against historical spillover records before claiming predictive capability.
- `major` `RESULT-ARTIFACT-MISMATCH`: Replace synthetic proxy outputs with actual retrospective scoring metrics derived from verified historical outbreak data to satisfy the completion test criteria.
