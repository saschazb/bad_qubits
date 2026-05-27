# Qiskit Learning Guide for Bad Qubits Project

This guide explains the key Qiskit concepts used in this project.

## Key Qiskit Concepts

### 1. **QuantumCircuit**
The fundamental building block for quantum programs.
```python
qc = QuantumCircuit(2)  # Create a 2-qubit circuit
qc.cx(0, 1)            # Apply CNOT gate (control=0, target=1)
```

### 2. **NoiseModel**
Describes realistic quantum hardware imperfections. We use depolarizing errors to model how quantum gates fail in real devices.

**Depolarizing Error** (p):
- With probability (1-p): gate executes perfectly
- With probability p: the qubit/qubits collapse to a random state
- Models "bit flip" and "phase flip" errors together

```python
from qiskit_aer.noise import depolarizing_error, NoiseModel

# 5% error rate on single-qubit gates
error_1q = depolarizing_error(0.05, 1)

# 5% error rate on two-qubit gates like CNOT
error_2q = depolarizing_error(0.05, 2)
```

### 3. **AerSimulator**
A classical simulator that can:
- Simulate ideal quantum circuits
- Add noise during simulation
- Return density matrices (not just statevectors) for noisy simulations

```python
from qiskit_aer import AerSimulator

simulator = AerSimulator(method='density_matrix')  # Use density matrix for noise
job = simulator.run(circuit, noise_model=noise_model)
result = job.result()
```

### 4. **State Fidelity**
Measures how close two quantum states are (0 = completely different, 1 = identical).

For comparing ideal vs noisy CNOT:
- **Ideal CNOT**: Creates state |Ψ⟩
- **Noisy CNOT**: Creates state ρ (density matrix with noise)
- **Fidelity**: F(Ψ, ρ) tells us how much the noise affected the output

```python
from qiskit.quantum_info import state_fidelity

fidelity = state_fidelity(ideal_state, noisy_state)  # Returns 0-1
```

---

## Understanding CNOT

CNOT (Controlled-NOT) is a two-qubit gate:

| Control | Target | Control | Target |
|---------|--------|---------|--------|
| 0       | 0      | 0       | 0      |
| 0       | 1      | 0       | 1      |
| 1       | 0      | 1       | 1      |
| 1       | 1      | 1       | 0      |

**Action**: If control=1, flip the target. Otherwise, do nothing.

---

## The Experiment Design

### Research Question
**Which qubit in a CNOT gate is more susceptible to noise—the control or the target?**

This matters for algorithmic optimization: If target qubits are more robust, we might route algorithms to use good qubits as targets more often.

### Methodology

1. **Define input states**: Test all 4 basis states |00⟩, |01⟩, |10⟩, |11⟩
2. **Create ideal CNOT**: Reference behavior with perfect gates
3. **Create noisy CNOT**: Same circuit but simulated with noise model
4. **Calculate fidelity**: Measure how much noise affected the output
5. **Vary noise location**: Test noise on control vs target separately
6. **Compare results**: Identify which qubit position is more vulnerable

### Why This Matters

In real quantum computers:
- Different qubits have different error rates
- Understanding gate-specific noise sensitivity helps optimize circuit mapping
- Can inform decisions like "route high-fidelity algorithms through control qubit positions"

---

## Code Walkthrough: Key Functions

### `create_noise_model(error_rate, noisy_qubits)`
Creates a noise model affecting specific qubits.

**Important detail**: The noise affects gates on those qubits, not just idling. In CNOT, we add error to both single-qubit initialization (x gates) AND the two-qubit cx gate itself.

### `calculate_cnot_fidelity(control_state, target_state, noise_model)`
Simulates CNOT with a specific input state and optional noise.

Steps:
1. Initialize qubits to desired state
2. Apply CNOT
3. Compare ideal vs noisy output via fidelity

### `benchmark_cnot_with_noise_scenarios(error_rates)`
The main experiment loop:
- Tests multiple error rates (1%-20%)
- For each error rate, tests 3 scenarios:
  1. No noise (baseline)
  2. Noise only on control qubit
  3. Noise only on target qubit
- Averages over all 4 input states for robustness

---

## Expected Results

From theory, we'd expect:
- **Higher error rates → Lower fidelity** (linear relationship for depolarizing error)
- Depending on the gate structure, control and target might have different sensitivities
- For CNOT specifically, often **target qubit noise is more impactful** because errors there affect the outcome more directly

---

## Next Steps: Extending the Experiment

### 1. **Study Single Qubits First** (Before CNOT)
```python
# Test single-qubit gates (H, X, Y, Z)
# Establish baseline noise sensitivity
```

### 2. **Add More Noise Models**
```python
# Amplitude damping (energy loss)
# Phase damping (dephasing)
# Bit flip errors
# Combinations
```

### 3. **Study Toffoli Gate** (3-qubit, more complex)
```python
# Control1 -> Control2 -> Target
# Which position is most critical?
```

### 4. **Circuit-Level Analysis**
```python
# Multiple gates in sequence
# Does noise accumulate linearly?
# Are there noise-resilient gate sequences?
```

---

## Useful Qiskit Resources

- **Official Docs**: https://qiskit.org/documentation/
- **Noise Models**: https://qiskit.org/documentation/apidoc/aer_noise.html
- **Density Matrices**: Used for open quantum systems with noise
- **DensityMatrix class**: https://qiskit.org/documentation/apidoc/qiskit.quantum_info.DensityMatrix.html

---

## Common Pitfalls & Tips

1. **Statevectors vs Density Matrices**
   - Statevectors: Pure states (no noise)
   - Density matrices: Mixed states (with noise)
   - Always use `method='density_matrix'` when simulating with noise

2. **Error Rate Interpretation**
   - 0.05 = 5% error rate
   - Depolarizing error with p=0.05: 95% correct + 5% random collapse

3. **Averaging Over Input States**
   - A gate's fidelity depends on input
   - Always average over all input states for fair comparison

4. **Noise on Two-Qubit Gates**
   - CNOT noise can affect control independently or jointly
   - Our model adds noise to both the CNOT itself AND any single-qubit gates on those qubits

---

## Questions to Explore

1. Does the relationship between error rate and fidelity loss change with different noise models?
2. Can we find gate sequences that are naturally error-robust on certain qubit types?
3. How do multi-qubit operations accumulate error in long circuits?
4. Is there an optimal assignment of noisy qubits to algorithm roles?
