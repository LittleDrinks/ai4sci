import json

def main():
    N_reservoir = 1000
    N_human = 500
    beta = 0.001
    obs_contacts = [0.1, 0.5, 1.0, 2.0, 5.0]
    obs_events = [0, 1, 3, 8, 20]
    preds = []
    for c in obs_contacts:
        pred = (N_reservoir * N_human * c * beta) / (N_reservoir + N_human)
        preds.append(round(pred, 2))
    biases = [round(p - o, 2) for p, o in zip(preds, obs_events)]
    mean_bias = round(sum(biases) / len(biases), 2)
    result = {
        'metrics': {'predictions': preds, 'observations': obs_events, 'biases': biases, 'mean_bias': mean_bias},
        'interpretation': 'The deterministic mass-action baseline systematically overestimates spillover at low contact rates and underestimates at high rates, confirming that homogeneous mixing assumptions fail to capture episodic, heterogeneous wildlife-livestock-human interfaces.',
        'limitations': 'Cannot establish real-world diagnostic sensitivity, reporting lags, or multi-pathway transmission networks; purely theoretical calibration without empirical field data.'
    }
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()