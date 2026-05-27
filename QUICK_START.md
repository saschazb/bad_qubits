# Quick Start Guide

## Installation

1. **Create a virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Running the Experiment

```bash
python exp_CNOT.py
```

This will:
- Simulate CNOT gates under different noise conditions
- Test error rates from 1% to 20%
- Compare control vs target qubit noise sensitivity
- Generate a comparison plot: `cnot_fidelity_comparison.png`
- Print detailed results to console

**Expected runtime**: ~2-5 minutes (depending on your machine)

## Understanding the Output

The script prints a table showing:
- **Error Rate**: The depolarizing error probability
- **No Noise**: Baseline perfect CNOT fidelity (should be ~1.0)
- **Control Noisy**: Average fidelity when control qubit has noise
- **Target Noisy**: Average fidelity when target qubit has noise

**Key insight**: 
- If "Control Noisy" fidelity drops more → control position is more critical
- If "Target Noisy" fidelity drops more → target position is more critical

## Example Output

```
Error Rate      No Noise        Control Noisy   Target Noisy   
0.010           0.9900          0.9810          0.9795         
0.030           0.9700          0.9410          0.9390         
...
```

## What to Explore Next

### 1. Modify the Noise Model
Try different error models to see how results change:

```python
# In the script, modify create_noise_model():
from qiskit_aer.noise import amplitude_damping_error, phase_damping_error

# Amplitude damping (energy loss, T1)
error = amplitude_damping_error(gamma=0.01)

# Phase damping (dephasing, T2)
error = phase_damping_error(gamma=0.01)

# Bit flip error
error = pauli_error([('I', 1 - error_rate), ('X', error_rate)])
```

### 2. Test Different Qubit Counts
Extend to 3-qubit systems for Toffoli gates:

```python
def create_toffoli_circuit():
    qc = QuantumCircuit(3)
    qc.ccx(0, 1, 2)  # Toffoli: controls on qubits 0,1; target on 2
    return qc
```

### 3. Vary Input States
Currently averages over all 4 input states. You could separately analyze each:

```python
# For CNOT |11⟩ → |10⟩ (has bit flip on target)
# vs CNOT |10⟩ → |10⟩ (identity on target)
# Do they have different noise sensitivity?
```

### 4. Circuit-Level Experiments
Chain multiple CNOTs to see noise accumulation:

```python
def create_cnot_chain(depth):
    qc = QuantumCircuit(2)
    for _ in range(depth):
        qc.cx(0, 1)
    return qc
```

## Troubleshooting

**Issue**: `ImportError: cannot import name 'AerSimulator'`
- **Solution**: Make sure qiskit-aer is installed: `pip install qiskit-aer`

**Issue**: Script runs very slowly
- **Solution**: This is normal for the first run (Qiskit compiling). Subsequent runs are faster.
- Or reduce the number of error rates being tested in the main script

**Issue**: Memory error
- **Solution**: Reduce the number of error rates or use a simpler noise model

## File Structure

```
bad_qubits/
├── README.md              # Project description
├── QISKIT_GUIDE.md        # Detailed learning guide
├── QUICK_START.md         # This file
├── requirements.txt       # Python dependencies
├── exp_CNOT.py           # Main CNOT fidelity experiment
├── cnot_fidelity_comparison.png  # Output plot
└── (future: exp_Toffoli.py, analysis scripts, etc.)
```

## References

- [Qiskit Documentation](https://qiskit.org/documentation/)
- [Noise Models in Qiskit](https://qiskit.org/documentation/apidoc/aer_noise.html)
- [CNOT Gate Theory](https://en.wikipedia.org/wiki/Controlled_NOT_gate)
- [Depolarizing Channel](https://en.wikipedia.org/wiki/Depolarizing_channel)
