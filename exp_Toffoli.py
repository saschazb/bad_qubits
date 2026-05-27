"""
Toffoli (CCNOT) Fidelity Experiment with Noisy Qubits
======================================================
Evaluates how noise on different qubits affects the Toffoli gate.

Toffoli is a 3-qubit gate:
- Control qubits: 0 and 1
- Target qubit: 2
- Action: Flip target if BOTH controls are 1 (AND operation)

We test where a single noisy qubit affects the Toffoli outcome most.
"""

import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, pauli_error
from qiskit.quantum_info import DensityMatrix, state_fidelity, Statevector
import warnings
warnings.filterwarnings('ignore')
import itertools


def all_subsets(qubits):
    """Return all subsets of the given list of qubits."""
    return list(itertools.chain.from_iterable(
        itertools.combinations(qubits, r) for r in range(len(qubits) + 1)
    ))


def subset_key(subset):
    if len(subset) == 0:
        return 'noise_on_none'
    return 'noise_on_' + '_'.join(str(q) for q in subset)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_noise_model(error_rate: float, noisy_qubits: list) -> NoiseModel:
    """
    Create a noise model representing independent bit-flip errors (Pauli-X)
    on the specified qubits for a 3-qubit system. Two-qubit errors are modeled
    as the tensor product of single-qubit bit-flip channels on the involved qubits.
    """
    noise_model = NoiseModel()
    p = float(error_rate)

    # Single-qubit bit-flip error
    single = pauli_error([('I', 1 - p), ('X', p)])
    for q in noisy_qubits:
        noise_model.add_quantum_error(single, ['h', 'x', 'y', 'z'], [q])

    # Prepare two-qubit Pauli errors for all pairs used in Toffoli decompositions
    pairs = [(0,1), (0,2), (1,2)]
    for a,b in pairs:
        pa = p if a in noisy_qubits else 0.0
        pb = p if b in noisy_qubits else 0.0
        probs = {
            'II': (1-pa)*(1-pb),
            'XI': pa*(1-pb),
            'IX': (1-pa)*pb,
            'XX': pa*pb,
        }
        two = pauli_error([(k, v) for k,v in probs.items()])
        noise_model.add_quantum_error(two, ['cx'], [a, b])

    return noise_model


def calculate_toffoli_fidelity(c0_state: str, c1_state: str, target_state: str,
                                noise_model: NoiseModel = None) -> float:
    """
    Calculate the fidelity of a Toffoli operation for a specific input state.
    
    Args:
        c0_state: Initial state of control qubit 0 ('0' or '1')
        c1_state: Initial state of control qubit 1 ('0' or '1')
        target_state: Initial state of target qubit ('0' or '1')
        noise_model: Optional noise model
    
    Returns:
        Fidelity (0 to 1)
    """
    # Create ideal circuit and noisy circuit
    qc_ideal = QuantumCircuit(3)
    if c0_state == '1':
        qc_ideal.x(0)
    if c1_state == '1':
        qc_ideal.x(1)
    if target_state == '1':
        qc_ideal.x(2)
    qc_ideal.ccx(0, 1, 2)

    qc_noisy = QuantumCircuit(3)
    if c0_state == '1':
        qc_noisy.x(0)
    if c1_state == '1':
        qc_noisy.x(1)
    if target_state == '1':
        qc_noisy.x(2)
    qc_noisy.ccx(0, 1, 2)
    try:
        qc_noisy.save_density_matrix()
    except Exception:
        pass

    # Ideal reference via Statevector
    sv = Statevector.from_instruction(qc_ideal)
    rho_ideal = DensityMatrix(sv)

    # Noisy simulation -> extract density matrix
    if noise_model is not None:
        sim_noisy = AerSimulator(method='density_matrix')
        res_noisy = sim_noisy.run(qc_noisy, noise_model=noise_model).result()
        try:
            data = res_noisy.results[0].data.to_dict()
        except Exception:
            data = {}
        dm = data.get('density_matrix') or data.get('density')
        if dm is None:
            raise RuntimeError('Density matrix not found in noisy Toffoli result')
        rho_noisy = DensityMatrix(dm)
    else:
        rho_noisy = rho_ideal
    
    # Calculate fidelity
    fidelity = state_fidelity(rho_ideal, rho_noisy)
    return float(np.real(fidelity))


def benchmark_toffoli_with_noise_scenarios(error_rates: list) -> dict:
    """
    Compare Toffoli fidelity when different qubits are noisy.
    
    Args:
        error_rates: List of error rates to test
    
    Returns:
        Dictionary with fidelity results for each scenario
    """
    # Prepare all subsets of the three qubits
    qubits = [0, 1, 2]
    subsets = list(itertools.chain.from_iterable(
        itertools.combinations(qubits, r) for r in range(len(qubits) + 1)
    ))

    def subset_key(subset):
        if len(subset) == 0:
            return 'noise_on_none'
        return 'noise_on_' + '_'.join(str(q) for q in subset)

    results = {'error_rates': error_rates}
    for s in subsets:
        results[subset_key(s)] = []
    
    # All possible input states for Toffoli
    # Note: Toffoli only flips target when BOTH controls are 1
    input_states = [
        ('0', '0', '0'),  # Both controls off → no flip
        ('0', '0', '1'),
        ('0', '1', '0'),
        ('0', '1', '1'),
        ('1', '0', '0'),
        ('1', '0', '1'),
        ('1', '1', '0'),  # Both controls on → flip
        ('1', '1', '1'),
    ]
    
    for error_rate in error_rates:
        for s in subsets:
            key = subset_key(s)
            if len(s) == 0:
                fidelities = [
                    calculate_toffoli_fidelity(c0, c1, t, noise_model=None)
                    for c0, c1, t in input_states
                ]
            else:
                noise_model = create_noise_model(error_rate, list(s))
                fidelities = [
                    calculate_toffoli_fidelity(c0, c1, t, noise_model=noise_model)
                    for c0, c1, t in input_states
                ]
            results[key].append(np.mean(fidelities))
    
    return results


# ============================================================================
# MAIN EXPERIMENT
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("Toffoli (CCNOT) Fidelity Experiment with Noisy Qubits")
    print("=" * 80)
    
    # Test error rates from 1e-2 to 1e-4 (log-spaced)
    error_rates = np.logspace(-2, -4, 10)
    
    print(f"\nTesting error rates: {error_rates}")
    print("\nRunning simulations...")
    print("(This may take a couple minutes...)")
    
    # Run benchmarks
    results = benchmark_toffoli_with_noise_scenarios(error_rates)
    
    # Print brief results header
    print("\n" + "=" * 80)
    print("Results Summary (averaged fidelities)")
    print("=" * 80)

    # Prepare subset keys (all non-empty subsets plus none)
    qubits = [0,1,2]
    subsets = list(itertools.chain.from_iterable(
        itertools.combinations(qubits, r) for r in range(len(qubits) + 1)
    ))
    def subset_key(s):
        if len(s)==0:
            return 'noise_on_none'
        return 'noise_on_' + '_'.join(str(x) for x in s)

    subset_keys = [subset_key(s) for s in subsets]
    header = f"{'Error Rate':<12} " + ' '.join(f"{k:<14}" for k in subset_keys)
    print(header)
    print('-'*120)
    for i, er in enumerate(error_rates):
        row = f"{er:<12.4g} " + ' '.join(f"{results[k][i]:<14.4f}" for k in subset_keys)
        print(row)

    # Plot infidelity (1 - fidelity) on log-log scale for selected subsets
    plt.figure(figsize=(10,7))
    plot_keys = [
        'noise_on_0', 'noise_on_1', 'noise_on_2',
        'noise_on_0_1', 'noise_on_0_2', 'noise_on_1_2',
        'noise_on_0_1_2'
    ]
    markers = ['s','^','o','v','<','>','D']
    colors = ['red','blue','purple','orange','teal','magenta','green']
    labels = [
        'Noise on c0', 'Noise on c1', 'Noise on target',
        'Noise on c0,c1', 'Noise on c0,target', 'Noise on c1,target',
        'Noise on all qubits'
    ]
    er = np.array(error_rates)
    for k,m,c,lab in zip(plot_keys, markers, colors, labels):
        fidel = np.array(results[k])
        inf = 1.0 - fidel
        inf = np.maximum(inf, 1e-16)
        plt.loglog(er, inf, marker=m, label=lab, linewidth=2, color=c)

    plt.xlabel('Error Rate (p)', fontsize=12)
    plt.ylabel('Infidelity (1 - Fidelity)', fontsize=12)
    plt.title('Toffoli Infidelity vs Error Rate (Bit-flip noise, log-log)', fontsize=13)
    plt.legend(fontsize=11)
    plt.grid(True, which='both', linestyle='--', alpha=0.4)
    plt.tight_layout()
    plt.savefig('toffoli_infidelity_loglog.png', dpi=150)
    print('\n✓ Plot saved as toffoli_infidelity_loglog.png')
    plt.show()
    
    print("\n" + "=" * 80)
    print("Key Findings:")
    print("=" * 80)
    
    final_no_noise = results['noise_on_none'][-1]
    noisy_keys = [k for k in subset_keys if k != 'noise_on_none']
    impact = {
        k: abs(final_no_noise - results[k][-1])
        for k in noisy_keys
    }
    
    print(f"\n→ At highest error rate ({error_rates[-1]:.1%}):")
    for k, err in sorted(impact.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {k}: Δ fidelity = {err:.4f}")
