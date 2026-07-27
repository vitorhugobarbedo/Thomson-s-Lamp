# Célula única — autocontida. Requer: pip install qiskit qiskit-ibm-runtime pandas
#
# ATENCAO: nunca compartilhe o notebook com o token preenchido. Se expor, REVOGUE.
#
# NOVIDADE em relacao ao script anterior: agora R e R' TAMBEM sao medidos, em base
# de Bell (CX+H+measure), ao final do circuito. Isso permite estimar a FIDELIDADE
# REAL do teletransporte, condicionada ao sucesso da pos-selecao ja registrado --
# nao so a taxa de sobrevivencia do heraldo (o que o script anterior media).
#
# Interpretacao: se a pos-selecao teve sucesso (todos os bits de Bell do "buraco
# negro" = 0) E a medida de Bell entre R,R' tambem deu '00', entao R e R' estavam
# de fato no estado |Phi+> esperado -- ou seja, a informacao foi teletransportada
# corretamente. A fracao disso, entre os shots bem-sucedidos, e' a fidelidade
# condicionada (comparavel aos ~80% de Landsman et al. 2019, embora aqui seja uma
# estimativa em uma unica base de medida, nao tomografia completa).

import os
import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator, random_unitary
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2


# --- 0. Carregar secrets do ambiente (Colab Secrets ou variavel de ambiente) ---
def _get_secret(name):
    try:
        from google.colab import userdata
        val = userdata.get(name)
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(name)


IBM_QUANTUM_TOKEN = _get_secret("IBM_QUANTUM_TOKEN")
IBM_INSTANCE_CRN = _get_secret("IBM_INSTANCE_CRN")
CANDIDATES = ["ibm_marrakesh", "ibm_fez", "ibm_kingston"]


def connect_ibm(token, crn):
    if not token or not crn:
        print("Preencha IBM_QUANTUM_TOKEN e IBM_INSTANCE_CRN (secrets do ambiente) antes de conectar.")
        return None
    QiskitRuntimeService.save_account(
        channel="ibm_quantum_platform", token=token,
        instance=crn, overwrite=True, set_as_default=True
    )
    print("Conta salva e conectada.")
    return QiskitRuntimeService()


# --- 1. Diagnostico de backends ---
def med_gate_error(b, names=("ecr", "cz", "cx")):
    p = b.properties()
    e = [q.value for g in p.gates if g.gate in names and len(g.qubits) == 2
         for q in g.parameters if q.name == "gate_error"]
    return float(np.median(e)) if e else float("inf")


def med_readout_error(b):
    p = b.properties()
    e = [q.value for qb in p.qubits for q in qb if q.name == "readout_error"]
    return float(np.median(e)) if e else float("inf")


def supports_dynamic(b):
    try:
        if "if_else" in b.target.operation_names:
            return True
    except Exception:
        pass
    try:
        feats = getattr(b.configuration(), "supported_features", []) or []
        return any("dynamic" in str(f).lower() for f in feats)
    except Exception:
        return False


def backend_spec(be):
    cfg = be.configuration()
    info = dict(
        name=be.name, num_qubits=be.num_qubits,
        processor_type=getattr(be, "processor_type", getattr(cfg, "processor_type", None)),
        basis_gates=getattr(cfg, "basis_gates", None),
    )
    try:
        info["last_update_date"] = str(be.properties().last_update_date)
    except Exception:
        pass
    print("[backend_spec — cole no manuscrito]")
    for k, v in info.items():
        print(f"   {k}: {v}")
    return info


def choose_best_backend(service, candidates=CANDIDATES):
    rows = []
    for name in candidates:
        try:
            b = service.backend(name)
            st = b.status()
            rows.append(dict(
                backend=name, err2q=med_gate_error(b), readout=med_readout_error(b),
                fila=st.pending_jobs, op=bool(st.operational),
                dyn=supports_dynamic(b), nq=b.num_qubits, obj=b,
            ))
        except Exception:
            rows.append(dict(
                backend=name, err2q=float("inf"), readout=float("inf"),
                fila=10**9, op=False, dyn=False, nq=-1, obj=None,
            ))
    df = pd.DataFrame(rows)
    valid = df[(df.op) & (df.dyn) & np.isfinite(df.err2q)].copy()
    if valid.empty:
        print("AVISO: nenhum candidato com circuitos dinamicos — B1/B2 nao rodam.")
        valid = df[df.op & np.isfinite(df.err2q)].copy()
    qn = max(valid.fila.max(), 1)
    valid["score"] = valid.err2q + 0.5 * valid.readout + 0.05 * (valid.fila / qn)
    valid = valid.sort_values(["score", "err2q", "fila"]).reset_index(drop=True)
    try:
        from IPython.display import display
        display(valid[["backend", "err2q", "readout", "fila", "dyn", "nq", "score"]])
    except Exception:
        print(valid[["backend", "err2q", "readout", "fila", "dyn", "nq", "score"]].to_string())
    best = valid.loc[0, "obj"]
    print(f"\n>>> Selecionado: {best.name}")
    return best


# --- 2. Circuito do protocolo Yoshida-Kitaev (arXiv:1710.03363), COM medida de
#         Bell em (R,R') ao final, para permitir estimar fidelidade condicionada ---
def build_yk_circuit(n_bh, seed=0):
    """
    Qubits (ordem): q1(1), B(n_bh), R(1), E(n_bh), q1p(1), Rp(1)
    Classical bits: primeiro os pares de 'sucesso' (heraldo, buraco negro),
    depois os 2 bits da medida de Bell entre R e R'.
    Retorna: circuito, lista de clbits de sucesso, clbit de R, clbit de R'.
    """
    n = n_bh
    idx_q1 = 0
    idx_B = list(range(1, 1 + n))
    idx_R = 1 + n
    idx_E = list(range(2 + n, 2 + 2 * n))
    idx_q1p = 2 + 2 * n
    idx_Rp = 3 + 2 * n
    n_qubits = 4 + 2 * n

    qc = QuantumCircuit(n_qubits, n_qubits)

    qc.h(idx_q1); qc.cx(idx_q1, idx_R)                    # EPR(q1,R)
    for bi, ei in zip(idx_B, idx_E):                       # EPR_n(B,E)
        qc.h(bi); qc.cx(bi, ei)
    qc.h(idx_q1p); qc.cx(idx_q1p, idx_Rp)                  # EPR(q1',R')

    dim = 2 ** (1 + n)
    U = random_unitary(dim, seed=seed)
    qc.append(U.to_instruction(), [idx_q1] + idx_B)        # scrambling U em (q1,B)

    Ustar = Operator(np.conj(U.data))
    qc.append(Ustar.to_instruction(), [idx_q1p] + idx_E)   # U* em (q1',E)

    bell_pairs = [(idx_q1, idx_q1p)] + list(zip(idx_B, idx_E))
    c = 0
    success_clbits = []
    for a, b in bell_pairs:
        qc.cx(a, b)
        qc.h(a)
        qc.measure(a, c); success_clbits.append(c); c += 1
        qc.measure(b, c); success_clbits.append(c); c += 1

    # NOVO: medida de Bell entre R e R' -- verifica se de fato formaram |Phi+>
    qc.cx(idx_R, idx_Rp)
    qc.h(idx_R)
    c_R = c; qc.measure(idx_R, c_R); c += 1
    c_Rp = c; qc.measure(idx_Rp, c_Rp); c += 1

    return qc, success_clbits, c_R, c_Rp


def analyze_counts(counts, success_clbits, c_R, c_Rp, n_clbits):
    """
    Retorna (prob_sucesso, fidelidade_condicionada).
    fidelidade_condicionada = fracao, ENTRE OS SHOTS BEM-SUCEDIDOS (heraldo=0...0),
    em que a medida de Bell entre R,R' tambem deu '00' (ou seja, R,R' realmente
    formaram o par EPR esperado -- teletransporte correto).
    """
    success_shots = 0
    fidelity_shots = 0
    total_shots = sum(counts.values())
    for bitstring, nc in counts.items():
        bits = bitstring.replace(' ', '')
        bit_of = lambda clbit_idx: bits[n_clbits - 1 - clbit_idx]
        success = all(bit_of(cb) == '0' for cb in success_clbits)
        if success:
            success_shots += nc
            if bit_of(c_R) == '0' and bit_of(c_Rp) == '0':
                fidelity_shots += nc
    prob_success = success_shots / total_shots if total_shots > 0 else float('nan')
    fidelity = fidelity_shots / success_shots if success_shots > 0 else float('nan')
    return prob_success, fidelity, success_shots, total_shots


# --- 3. Conectar, escolher backend, construir, transpilar e submeter ---
service = connect_ibm(IBM_QUANTUM_TOKEN, IBM_INSTANCE_CRN)

if service is not None:
    backend = choose_best_backend(service, CANDIDATES)
    backend_spec(backend)

    n_bh = 1  # comece pequeno (mais robusto a ruido); suba para 2 ou 3 depois
    qc, success_clbits, c_R, c_Rp = build_yk_circuit(n_bh, seed=0)

    tqc = transpile(qc, backend=backend, optimization_level=3)
    n_2q = sum(1 for instr in tqc.data if instr.operation.num_qubits == 2)
    print(f"Profundidade apos transpile: {tqc.depth()}  |  Portas de 2 qubits: {n_2q}")

    sampler = SamplerV2(mode=backend)
    job = sampler.run([tqc], shots=8000)
    print(f"Job ID: {job.job_id()}  -- acompanhe em https://quantum.ibm.com/jobs")

    result = job.result()
    creg_name = tqc.cregs[0].name
    counts = getattr(result[0].data, creg_name).get_counts()

    prob_success, fidelity, n_success, n_total = analyze_counts(
        counts, success_clbits, c_R, c_Rp, qc.num_clbits
    )
    print(f"\nShots totais: {n_total}  |  Shots com sucesso (heraldo): {n_success}")
    print(f"Prob. de sucesso (heraldo): {prob_success:.4f}  (ideal sem ruido = 0.2500)")
    print(f"Fidelidade condicionada ao sucesso (R,R'): {fidelity:.4f}  (ideal sem ruido = 1.0000)")
    print(f"  -> comparavel aos ~80% reportados por Landsman et al. 2019 (Nature 567, 61) em ions presos")
