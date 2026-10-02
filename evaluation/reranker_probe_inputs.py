"""Research adapters use the exact serving input transformation."""
from campusai.retrieval.reranker_inputs import FORMATS, scoring_text, render_table


def probe_loader(model_dir, identity, input_format):
    from campusai.retrieval.model_runtime import retrieval_runtime
    if identity.input_format != input_format:
        raise ValueError("research input must match the serving model identity")
    def load():
        register_pinned_architecture(model_dir)
        model = retrieval_runtime().get_offline_reranker(
            model_dir, device=identity.device, max_length=identity.max_length,
            snapshot_sha256=identity.model_sha256, dtype=identity.dtype)
        restore_gte_inference_buffers(model)
        return model
    return load


def restore_gte_inference_buffers(cross_encoder):
    # The pinned 2024 implementation predates Transformers 5 meta loading.
    # Its nonpersistent buffers are absent from checkpoint weights and can
    # remain uninitialized. Re-run their original constructor formulas only;
    # no learned tensor or forward equation changes.
    model = cross_encoder.model
    if model.config.model_type != "new" or getattr(model,"_phase7_probe_buffers_ready",False):
        return
    import torch
    from types import MethodType
    device, dtype = next(model.parameters()).device, next(model.parameters()).dtype
    embeddings = model.new.embeddings
    embeddings.register_buffer("position_ids",torch.arange(model.config.max_position_embeddings,device=device),persistent=False)
    embeddings._init_rope(model.config)
    embeddings.rotary_emb.to(device=device,dtype=dtype)
    if not hasattr(model.new,"get_extended_attention_mask"):
        def extended_attention_mask(encoder, mask, _input_shape, device=None, dtype=None):
            if getattr(encoder.config,"is_decoder",False):
                raise ValueError("research adapter supports encoder-only attention")
            dtype = dtype or next(encoder.parameters()).dtype
            if mask.ndim == 2:
                expanded = mask[:,None,None,:]
            elif mask.ndim == 3:
                expanded = mask[:,None,:,:]
            else:
                raise ValueError("invalid GTE attention mask shape")
            return (1.0-expanded.to(dtype=dtype))*torch.finfo(dtype).min
        model.new.get_extended_attention_mask = MethodType(extended_attention_mask,model.new)
    if not torch.isfinite(embeddings.rotary_emb.cos_cached).all() or not torch.isfinite(embeddings.rotary_emb.sin_cached).all():
        raise ValueError("invalid restored GTE rotary buffers")
    model._phase7_probe_buffers_ready = True


def register_pinned_architecture(model_dir):
    """Research adapter for locally inspected, snapshot-bound GTE source.

    No remote module resolution is enabled. The custom implementation must be
    inside the same snapshot whose bytes the provider verifies before loading.
    """
    import hashlib
    import importlib
    import json
    from pathlib import Path
    import sys
    from types import ModuleType
    root = Path(model_dir).resolve()
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    if config.get("model_type") != "new":
        return
    code = [root / name for name in ("configuration.py","modeling.py")]
    if not all(path.is_file() for path in code):
        raise ValueError("GTE research requires local pinned implementation in the verified snapshot")
    digest = hashlib.sha256(b"".join(path.read_bytes() for path in code)).hexdigest()
    package = "phase7_probe_gte_" + digest
    if package not in sys.modules:
        module = ModuleType(package)
        module.__path__ = [str(root)]
        sys.modules[package] = module
    configuration = importlib.import_module(package + ".configuration")
    modeling = importlib.import_module(package + ".modeling")
    from transformers import AutoConfig, AutoModelForSequenceClassification
    AutoConfig.register("new",configuration.NewConfig,exist_ok=True)
    AutoModelForSequenceClassification.register(configuration.NewConfig,modeling.NewForSequenceClassification,exist_ok=True)
