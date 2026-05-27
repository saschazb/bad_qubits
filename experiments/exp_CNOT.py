"""
CNOT Fidelity Experiment with Noisy Qubits
===========================================
Evaluates how noise on different qubits affects the fidelity of CNOT operations.
We compare three scenarios:
1. Perfect CNOT (no noise)
2. Noise on control qubit only
3. Noise on target qubit only

This helps identify whether certain qubits in a multi-qubit operation are more
critical than others from a noise perspective.
"""

import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, pauli_error
from qiskit.quantum_info import DensityMatrix, state_fidelity, Statevector
import warnings
warnings.filterwarnings('ignore')
import itertools


def all_subsets(qubits):
    """Return all subsets of the given qubit list."""
    return list(itertools.chain.from_iterable(
        itertools.combinations(qubits, r) for r in range(len(qubits) + 1)
    ))


def subset_key(subset):
    """Convert a tuple subset into a deterministic result dictionary key."""
    if len(subset) == 0:
        return 'noise_on_none'
    return 'noise_on_' + '_'.join(str(q) for q in subset)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_cnot_circuit(control_qubit: int = 0, target_qubit: int = 1) -> QuantumCircuit:
    """
    Create a simple CNOT circuit.
    
    Args:
        control_qubit: Index of control qubit
        target_qubit: Index of target qubit
    
    Returns:
        QuantumCircuit with CNOT gate
    """
    qc = QuantumCircuit(2, name='CNOT')
    qc.cx(control_qubit, target_qubit)
    return qc


def create_noise_model(error_rate: float, noisy_qubits: list) -> NoiseModel:
    """
    Create a noise model with depolarizing errors on specified qubits.
    
    Args:
        error_rate: Error probability for single and two-qubit gates
        noisy_qubits: List of qubit indices to apply noise to
    
    Returns:
        NoiseModel with depolarizing errors
    """
    """
    Create a noise model representing independent bit-flip errors (Pauli-X)
    on the specified qubits. For two-qubit gates we model the error as the
    independent tensor product of single-qubit bit-flip channels on the two
    participating qubits, using the per-qubit probabilities determined by
    whether each qubit is in `noisy_qubits`.
    """
    noise_model = NoiseModel()

    p = float(error_rate)

    # Single-qubit bit-flip error: I with prob 1-p, X with prob p
    single_qubit_error = pauli_error([('I', 1 - p), ('X', p)])

    # Add single-qubit errors to specified qubits for common single-qubit gates
    for qubit in noisy_qubits:
        noise_model.add_quantum_error(single_qubit_error, ['h', 'x', 'y', 'z'], [qubit])

    # Two-qubit error for the CNOT between qubit 0 and 1.
    # Determine per-qubit flip probabilities depending on whether each
    # qubit is marked noisy.
    p0 = p if 0 in noisy_qubits else 0.0
    p1 = p if 1 in noisy_qubits else 0.0

    probs_II = (1 - p0) * (1 - p1)
    probs_XI = p0 * (1 - p1)
    probs_IX = (1 - p0) * p1
    probs_XX = p0 * p1

    two_qubit_error = pauli_error([
        ('II', probs_II),
        ('XI', probs_XI),
        ('IX', probs_IX),
        ('XX', probs_XX),
    ])

    # Attach two-qubit error to the CNOT gate (0 -> 1)
    noise_model.add_quantum_error(two_qubit_error, ['cx'], [0, 1])

    return noise_model


def get_circuit_density_matrix(qc: QuantumCircuit, noise_model: NoiseModel = None):
    """
    Simulate a circuit and return the final density matrix.
    
    Args:
        qc: QuantumCircuit to simulate
        noise_model: Optional noise model to apply
    
    Returns:
        DensityMatrix of the output state
    """
    simulator = AerSimulator(method='density_matrix')
    
    if noise_model is not None:
        job = simulator.run(qc, noise_model=noise_model, shots=1)
    else:
        job = simulator.run(qc, shots=1)
    
    result = job.result()
    return DensityMatrix(result.get_statevector(0))


def calculate_cnot_fidelity(control_state: str = '0', target_state: str = '0',
                           noise_model: NoiseModel = None) -> float:
    """
    Calculate the fidelity of a CNOT operation for a specific input state.
    
    Args:
        control_state: Initial state of control qubit ('0' or '1')
        target_state: Initial state of target qubit ('0' or '1')
        noise_model: Optional noise model
    
    Returns:
        Fidelity (0 to 1)
    """
    # Create ideal circuit with initialization
    qc_ideal = QuantumCircuit(2)
    if control_state == '1':
        qc_ideal.x(0)
    if target_state == '1':
        qc_ideal.x(1)
    qc_ideal.cx(0, 1)
    
    # Create noisy circuit with same initialization
    qc_noisy = QuantumCircuit(2)
    if control_state == '1':
        qc_noisy.x(0)
    if target_state == '1':
        qc_noisy.x(1)
    qc_noisy.cx(0, 1)
    # Request that the Aer simulator returns the final density matrix
    try:
        qc_noisy.save_density_matrix()
    except Exception:
        # If save instruction is unavailable, we'll rely on default result parsing
        pass
    
    # Build ideal reference state directly via Statevector (no simulator needed)
    sv = Statevector.from_instruction(qc_ideal)
    rho_ideal = DensityMatrix(sv)

    # Simulate noisy circuit with density-matrix simulator
    if noise_model is not None:
        simulator_noisy = AerSimulator(method='density_matrix')
        result_noisy = simulator_noisy.run(qc_noisy, noise_model=noise_model).result()
        # Try common locations for density matrix in result
        # Extract density matrix from the ExperimentResultData structure
        try:
            data_dict = result_noisy.results[0].data.to_dict()
        except Exception:
            data_dict = {}

        dm = data_dict.get('density_matrix') or data_dict.get('density')
        if dm is not None:
            rho_noisy = DensityMatrix(dm)
        else:
            # If density matrix not found, raise an informative error
            raise RuntimeError('Density matrix not found in noisy simulation result')
    else:
        rho_noisy = rho_ideal
    
    # Calculate fidelity
    fidelity = state_fidelity(rho_ideal, rho_noisy)
    return float(np.real(fidelity))


def benchmark_cnot_with_noise_scenarios(error_rates: list) -> dict:
    """
    Compare CNOT fidelity across different noise scenarios.
    
    Args:
        error_rates: List of error rates to test
    
    Returns:
        Dictionary with fidelity results for each scenario
    """
    # Prepare all subsets of qubits (for 2 qubits: (), (0,), (1,), (0,1))
    qubits = [0, 1]
    subsets = all_subsets(qubits)

    results = {'error_rates': error_rates}
    for s in subsets:
        results[subset_key(s)] = []

    # All possible input states for CNOT
    input_states = [('0', '0'), ('0', '1'), ('1', '0'), ('1', '1')]

    for error_rate in error_rates:
        for s in subsets:
            key = subset_key(s)
            if len(s) == 0:
                # No noise
                fidelities = [
                    calculate_cnot_fidelity(c_state, t_state, noise_model=None)
                    for c_state, t_state in input_states
                ]
            else:
                noise_model = create_noise_model(error_rate, list(s))
                fidelities = [
                    calculate_cnot_fidelity(c_state, t_state, noise_model=noise_model)
                    for c_state, t_state in input_states
                ]
            results[key].append(np.mean(fidelities))

    return results


# ============================================================================
# MAIN EXPERIMENT
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("CNOT Fidelity Experiment with Noisy Qubits")
    print("=" * 70)
    
    # Test error rates from 1e-2 to 1e-4 (log-spaced)
    error_rates = np.logspace(-2, -4, 10)
    
    print(f"\nTesting error rates: {error_rates}")
    print("\nRunning simulations...")
    
    # Run benchmarks
    results = benchmark_cnot_with_noise_scenarios(error_rates)
    
    # Print results for each subset
    subset_keys = [subset_key(s) for s in all_subsets([0, 1])]

    # Header
    print("\n" + "=" * 70)
    print("Results Summary")
    print("=" * 70)
    header = f"{'Error Rate':<15} " + ' '.join(f"{k:<15}" for k in subset_keys)
    print(header)
    print("-" * 70)

    for i, error_rate in enumerate(error_rates):
        row = f"{error_rate:<15.3f} " + ' '.join(f"{results[k][i]:<15.4f}" for k in subset_keys)
        print(row)

    # Plot infidelity (1 - fidelity) on log-log scale for noisy subsets
    plt.figure(figsize=(8, 6))
    noisy_keys = ['noise_on_0', 'noise_on_1', 'noise_on_0_1']
    markers = ['s', '^', 'D']
    colors = ['red', 'blue', 'green']
    labels = ['Noise on qubit 0', 'Noise on qubit 1', 'Noise on qubits 0&1']

    # Convert error_rates to numpy array
    er = np.array(error_rates)

    for k, m, c, lab in zip(noisy_keys, markers, colors, labels):
        fidel = np.array(results[k])
        infidelity = 1.0 - fidel
        # avoid zeros when plotting on log scale
        inf_clipped = np.maximum(infidelity, 1e-16)
        plt.loglog(er, inf_clipped, marker=m, label=lab, linewidth=2, color=c)

    plt.xlabel('Error Rate (p)', fontsize=12)
    plt.ylabel('Infidelity (1 - Fidelity)', fontsize=12)
    plt.title('CNOT Infidelity vs Error Rate (Bit-flip noise, log-log)', fontsize=13)
    plt.legend(fontsize=10)
    plt.grid(True, which='both', linestyle='--', alpha=0.4)
    plt.tight_layout()
    plt.savefig('cnot_infidelity_loglog.png', dpi=150)
    print("\n✓ Plot saved as 'cnot_infidelity_loglog.png'")
    plt.show()
    
    print("\n" + "=" * 70)
    print("Key Findings:")
    print("=" * 70)
    
    # Analyze which subset is most damaging at the highest error rate
    final_no_noise = results['noise_on_none'][-1]
    noisy_keys = [k for k in subset_keys if k != 'noise_on_none']
    impacts = {
        k: abs(final_no_noise - results[k][-1])
        for k in noisy_keys
    }
    
    print(f"→ At highest error rate ({error_rates[-1]:.1%}):")
    for k, err in sorted(impacts.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {k}: Δ fidelity = {err:.4f}")



